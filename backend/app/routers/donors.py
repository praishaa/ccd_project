from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import require_roles
from ..config import DONATION_INTERVAL_DAYS
from ..database import get_db
from ..models import Donation, Donor, User
from ..schemas import BloodGroup, DonationCreate, DonationOut, DonorOut, DonorUpdate
from ..services import eligibility_info

router = APIRouter(prefix="/donors", tags=["donors"])


def _donor_out(d: Donor) -> DonorOut:
    return DonorOut(
        id=d.id,
        user_id=d.user_id,
        name=d.user.name,
        email=d.user.email,
        blood_group=d.blood_group,
        city=d.city,
        phone=d.phone,
        last_donation_date=d.last_donation_date,
        available=d.available,
        **eligibility_info(d),
    )


def _my_donor(db: Session, user: User) -> Donor:
    donor = db.scalar(select(Donor).where(Donor.user_id == user.id))
    if donor is None:
        raise HTTPException(404, "Donor profile not found")
    return donor


@router.get("/me", response_model=DonorOut)
def get_my_profile(
    user: User = Depends(require_roles("donor")), db: Session = Depends(get_db)
):
    return _donor_out(_my_donor(db, user))


@router.put("/me", response_model=DonorOut)
def update_my_profile(
    data: DonorUpdate,
    user: User = Depends(require_roles("donor")),
    db: Session = Depends(get_db),
):
    donor = _my_donor(db, user)
    if data.city is not None:
        donor.city = data.city.strip()
    if data.phone is not None:
        donor.phone = data.phone
    if data.available is not None:
        donor.available = data.available
    db.commit()
    db.refresh(donor)
    return _donor_out(donor)


@router.get("/me/donations", response_model=List[DonationOut])
def my_donations(
    user: User = Depends(require_roles("donor")), db: Session = Depends(get_db)
):
    return _my_donor(db, user).donations


@router.post("/me/donations", response_model=DonorOut, status_code=201)
def record_donation(
    data: DonationCreate,
    user: User = Depends(require_roles("donor")),
    db: Session = Depends(get_db),
):
    """Record a new donation and update the last donation date."""
    donor = _my_donor(db, user)
    donated_on = data.donated_on or date.today()
    if donated_on > date.today():
        raise HTTPException(400, "Donation date cannot be in the future")
    if donor.last_donation_date and donated_on < donor.last_donation_date + timedelta(
        days=DONATION_INTERVAL_DAYS
    ):
        next_ok = donor.last_donation_date + timedelta(days=DONATION_INTERVAL_DAYS)
        raise HTTPException(
            400,
            f"Minimum gap between donations is {DONATION_INTERVAL_DAYS} days. "
            f"Next eligible date: {next_ok.isoformat()}",
        )
    db.add(Donation(donor_id=donor.id, donated_on=donated_on, units=data.units))
    donor.last_donation_date = donated_on
    db.commit()
    db.refresh(donor)
    return _donor_out(donor)


@router.get("", response_model=List[DonorOut])
def list_donors(
    blood_group: Optional[BloodGroup] = None,
    city: Optional[str] = None,
    only_eligible: bool = False,
    limit: int = Query(200, ge=1, le=500),
    user: User = Depends(require_roles("admin", "hospital")),
    db: Session = Depends(get_db),
):
    stmt = select(Donor).order_by(Donor.id)
    if blood_group:
        stmt = stmt.where(Donor.blood_group == blood_group)
    if city:
        stmt = stmt.where(func.lower(Donor.city) == city.strip().lower())
    donors = db.scalars(stmt).all()
    result = [_donor_out(d) for d in donors]
    if only_eligible:
        result = [d for d in result if d.eligible and d.available]
    return result[:limit]
