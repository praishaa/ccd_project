from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_roles
from ..database import get_db
from ..models import BloodRequest, Donor, User
from ..schemas import (
    DonorMatchOut,
    RequestCreate,
    RequestOut,
    RequestStatus,
    RequestStatusUpdate,
)
from ..services import (
    COMPATIBLE_RECIPIENTS,
    admin_ids,
    compute_priority,
    find_matches,
    notify,
    priority_label,
    total_available,
)

router = APIRouter(prefix="/requests", tags=["blood requests"])


def _out(r: BloodRequest, donors_notified: Optional[int] = None) -> RequestOut:
    return RequestOut(
        id=r.id,
        requester_id=r.requester_id,
        hospital=r.requester.name,
        blood_group=r.blood_group,
        units=r.units,
        urgency=r.urgency,
        required_date=r.required_date,
        city=r.city,
        status=r.status,
        priority_score=r.priority_score,
        priority_label=priority_label(r.priority_score),
        created_at=r.created_at,
        donors_notified=donors_notified,
    )


def _get_request(db: Session, request_id: int, user: User) -> BloodRequest:
    req = db.get(BloodRequest, request_id)
    if req is None:
        raise HTTPException(404, "Request not found")
    if user.role != "admin" and req.requester_id != user.id:
        raise HTTPException(403, "You can only access your own requests")
    return req


@router.post("", response_model=RequestOut, status_code=201)
def create_request(
    data: RequestCreate,
    user: User = Depends(require_roles("hospital", "admin")),
    db: Session = Depends(get_db),
):
    if data.required_date < date.today():
        raise HTTPException(400, "Required date cannot be in the past")

    stock_short = total_available(db, data.blood_group) < data.units
    req = BloodRequest(
        requester_id=user.id,
        blood_group=data.blood_group,
        units=data.units,
        urgency=data.urgency,
        required_date=data.required_date,
        city=data.city.strip(),
        status="pending",
        priority_score=compute_priority(
            data.urgency, data.units, data.required_date, stock_short
        ),
    )
    db.add(req)
    db.flush()

    matches = find_matches(db, req)
    msg = (
        f"{data.urgency.upper()} request: {data.units} unit(s) of {data.blood_group} "
        f"needed in {req.city} by {data.required_date.isoformat()} ({user.name})."
    )
    for donor in matches:
        notify(db, donor.user_id, "request", msg, request_id=req.id)
    if data.urgency == "critical":
        for admin_id in admin_ids(db):
            notify(db, admin_id, "request", f"[Admin] {msg}", request_id=req.id)
    if matches:
        req.status = "matched"

    db.commit()
    db.refresh(req)
    return _out(req, donors_notified=len(matches))


@router.get("/nearby", response_model=List[RequestOut])
def nearby_requests(
    user: User = Depends(require_roles("donor")), db: Session = Depends(get_db)
):
    """Open requests in the donor's city that their blood group can serve."""
    donor = db.scalar(select(Donor).where(Donor.user_id == user.id))
    if donor is None:
        raise HTTPException(404, "Donor profile not found")
    reqs = db.scalars(
        select(BloodRequest)
        .where(
            BloodRequest.status.in_(["pending", "matched"]),
            BloodRequest.required_date >= date.today(),
            BloodRequest.blood_group.in_(COMPATIBLE_RECIPIENTS[donor.blood_group]),
            func.lower(BloodRequest.city) == donor.city.strip().lower(),
        )
        .order_by(BloodRequest.priority_score.desc())
    ).all()
    return [_out(r) for r in reqs]


@router.get("", response_model=List[RequestOut])
def list_requests(
    status: Optional[RequestStatus] = None,
    user: User = Depends(require_roles("hospital", "admin")),
    db: Session = Depends(get_db),
):
    stmt = select(BloodRequest).order_by(BloodRequest.created_at.desc())
    if user.role == "hospital":
        stmt = stmt.where(BloodRequest.requester_id == user.id)
    if status:
        stmt = stmt.where(BloodRequest.status == status)
    return [_out(r) for r in db.scalars(stmt.limit(300)).all()]


@router.get("/{request_id}", response_model=RequestOut)
def get_request(
    request_id: int,
    user: User = Depends(require_roles("hospital", "admin")),
    db: Session = Depends(get_db),
):
    return _out(_get_request(db, request_id, user))


@router.get("/{request_id}/matches", response_model=List[DonorMatchOut])
def request_matches(
    request_id: int,
    user: User = Depends(require_roles("hospital", "admin")),
    db: Session = Depends(get_db),
):
    req = _get_request(db, request_id, user)
    return [
        DonorMatchOut(
            donor_id=d.id,
            name=d.user.name,
            blood_group=d.blood_group,
            city=d.city,
            phone=d.phone,
            last_donation_date=d.last_donation_date,
            exact_match=d.blood_group == req.blood_group,
        )
        for d in find_matches(db, req)
    ]


@router.patch("/{request_id}/status", response_model=RequestOut)
def update_status(
    request_id: int,
    data: RequestStatusUpdate,
    user: User = Depends(require_roles("hospital", "admin")),
    db: Session = Depends(get_db),
):
    req = _get_request(db, request_id, user)
    if req.status in ("fulfilled", "cancelled"):
        raise HTTPException(400, f"Request is already {req.status}")
    req.status = data.status
    db.commit()
    db.refresh(req)
    return _out(req)
