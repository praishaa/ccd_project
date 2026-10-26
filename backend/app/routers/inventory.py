from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_roles
from ..database import get_db
from ..models import Inventory, User
from ..schemas import BloodGroup, InventoryOut, InventoryUpdate, MessageOut, UnitsIn
from ..services import admin_ids, ensure_inventory_rows, inventory_status, notify

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _out(i: Inventory) -> InventoryOut:
    return InventoryOut(
        id=i.id,
        org_id=i.org_id,
        org_name=i.org.name,
        blood_group=i.blood_group,
        available_units=i.available_units,
        incoming_units=i.incoming_units,
        issued_units=i.issued_units,
        expired_units=i.expired_units,
        min_threshold=i.min_threshold,
        status=inventory_status(i.available_units, i.min_threshold),
    )


def _resolve_org(user: User, org_id: Optional[int], db: Session) -> int:
    """Hospitals/blood banks always work on their own stock.
    Admins must say which organisation they mean."""
    if user.role == "hospital":
        return user.id
    if org_id is None:
        raise HTTPException(400, "Admins must pass ?org_id=<organisation user id>")
    org = db.get(User, org_id)
    if org is None or org.role != "hospital":
        raise HTTPException(404, "Organisation not found")
    return org_id


def _row(db: Session, org_id: int, blood_group: str) -> Inventory:
    ensure_inventory_rows(db, org_id)
    return db.scalar(
        select(Inventory).where(
            Inventory.org_id == org_id, Inventory.blood_group == blood_group
        )
    )


@router.get("", response_model=List[InventoryOut])
def list_inventory(
    org_id: Optional[int] = None,
    user: User = Depends(require_roles("hospital", "admin")),
    db: Session = Depends(get_db),
):
    stmt = select(Inventory).order_by(Inventory.org_id, Inventory.blood_group)
    if user.role == "hospital":
        ensure_inventory_rows(db, user.id)
        stmt = stmt.where(Inventory.org_id == user.id)
    elif org_id is not None:
        stmt = stmt.where(Inventory.org_id == org_id)
    return [_out(i) for i in db.scalars(stmt).all()]


@router.get("/alerts", response_model=List[InventoryOut])
def low_stock(
    user: User = Depends(require_roles("hospital", "admin")),
    db: Session = Depends(get_db),
):
    stmt = select(Inventory)
    if user.role == "hospital":
        stmt = stmt.where(Inventory.org_id == user.id)
    rows = db.scalars(stmt).all()
    return [
        _out(i)
        for i in rows
        if inventory_status(i.available_units, i.min_threshold) != "OK"
    ]


@router.post("/check-alerts", response_model=MessageOut)
def check_alerts(
    user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    """Scan all stock and create low-stock notifications.
    Later an Azure Function (timer trigger) will call this endpoint."""
    created = 0
    admins = admin_ids(db)
    for i in db.scalars(select(Inventory)).all():
        st = inventory_status(i.available_units, i.min_threshold)
        if st == "OK":
            continue
        msg = (
            f"{st}: {i.org.name} has {i.available_units} unit(s) of {i.blood_group} "
            f"(minimum {i.min_threshold})."
        )
        for uid in {i.org_id, *admins}:
            if notify(db, uid, "low_stock", msg, dedupe=True):
                created += 1
    db.commit()
    return MessageOut(detail="Low-stock check complete", count=created)


@router.put("/{blood_group}", response_model=InventoryOut)
def update_settings(
    blood_group: BloodGroup,
    data: InventoryUpdate,
    org_id: Optional[int] = Query(None),
    user: User = Depends(require_roles("hospital", "admin")),
    db: Session = Depends(get_db),
):
    row = _row(db, _resolve_org(user, org_id, db), blood_group)
    if data.min_threshold is not None:
        row.min_threshold = data.min_threshold
    if data.incoming_units is not None:
        row.incoming_units = data.incoming_units
    db.commit()
    db.refresh(row)
    return _out(row)


@router.post("/{blood_group}/receive", response_model=InventoryOut)
def receive_units(
    blood_group: BloodGroup,
    data: UnitsIn,
    org_id: Optional[int] = Query(None),
    user: User = Depends(require_roles("hospital", "admin")),
    db: Session = Depends(get_db),
):
    row = _row(db, _resolve_org(user, org_id, db), blood_group)
    row.available_units += data.units
    row.incoming_units = max(0, row.incoming_units - data.units)
    db.commit()
    db.refresh(row)
    return _out(row)


@router.post("/{blood_group}/issue", response_model=InventoryOut)
def issue_units(
    blood_group: BloodGroup,
    data: UnitsIn,
    org_id: Optional[int] = Query(None),
    user: User = Depends(require_roles("hospital", "admin")),
    db: Session = Depends(get_db),
):
    row = _row(db, _resolve_org(user, org_id, db), blood_group)
    if data.units > row.available_units:
        raise HTTPException(
            400, f"Only {row.available_units} unit(s) of {blood_group} available"
        )
    row.available_units -= data.units
    row.issued_units += data.units
    db.commit()
    db.refresh(row)
    return _out(row)


@router.post("/{blood_group}/expire", response_model=InventoryOut)
def expire_units(
    blood_group: BloodGroup,
    data: UnitsIn,
    org_id: Optional[int] = Query(None),
    user: User = Depends(require_roles("hospital", "admin")),
    db: Session = Depends(get_db),
):
    row = _row(db, _resolve_org(user, org_id, db), blood_group)
    if data.units > row.available_units:
        raise HTTPException(
            400, f"Only {row.available_units} unit(s) of {blood_group} available"
        )
    row.available_units -= data.units
    row.expired_units += data.units
    db.commit()
    db.refresh(row)
    return _out(row)
