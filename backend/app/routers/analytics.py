from collections import Counter
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import require_roles
from ..database import get_db
from ..ml import forecast_demand, previous_months
from ..models import BloodRequest, Donation, Donor, Inventory, User
from ..schemas import ForecastItem
from ..services import BLOOD_GROUPS, inventory_status

router = APIRouter(prefix="/analytics", tags=["analytics"])

allowed = require_roles("admin", "hospital")


@router.get("/summary")
def summary(user: User = Depends(allowed), db: Session = Depends(get_db)):
    total_donors = db.scalar(select(func.count(Donor.id))) or 0
    available_donors = (
        db.scalar(select(func.count(Donor.id)).where(Donor.available.is_(True))) or 0
    )
    total_donations = db.scalar(select(func.count(Donation.id))) or 0
    units_donated = db.scalar(select(func.coalesce(func.sum(Donation.units), 0))) or 0

    dist = dict(
        db.execute(select(Donor.blood_group, func.count(Donor.id)).group_by(Donor.blood_group)).all()
    )
    stock = dict(
        db.execute(
            select(Inventory.blood_group, func.coalesce(func.sum(Inventory.available_units), 0))
            .group_by(Inventory.blood_group)
        ).all()
    )
    threshold = dict(
        db.execute(
            select(Inventory.blood_group, func.coalesce(func.sum(Inventory.min_threshold), 0))
            .group_by(Inventory.blood_group)
        ).all()
    )
    status_counts = dict(
        db.execute(
            select(BloodRequest.status, func.count(BloodRequest.id)).group_by(BloodRequest.status)
        ).all()
    )

    low_stock = [
        {
            "org": i.org.name,
            "blood_group": i.blood_group,
            "available": i.available_units,
            "minimum": i.min_threshold,
            "status": inventory_status(i.available_units, i.min_threshold),
        }
        for i in db.scalars(select(Inventory)).all()
        if inventory_status(i.available_units, i.min_threshold) != "OK"
    ]

    return {
        "total_donors": total_donors,
        "available_donors": available_donors,
        "total_donations": total_donations,
        "total_units_donated": int(units_donated),
        "donor_distribution": [
            {"blood_group": g, "count": int(dist.get(g, 0))} for g in BLOOD_GROUPS
        ],
        "inventory_by_group": [
            {
                "blood_group": g,
                "available": int(stock.get(g, 0)),
                "minimum": int(threshold.get(g, 0)),
            }
            for g in BLOOD_GROUPS
        ],
        "request_status": {
            s: int(status_counts.get(s, 0))
            for s in ["pending", "matched", "fulfilled", "cancelled"]
        },
        "active_requests": int(status_counts.get("pending", 0) + status_counts.get("matched", 0)),
        "low_stock": low_stock,
    }


@router.get("/trends")
def trends(user: User = Depends(allowed), db: Session = Depends(get_db)):
    """Monthly donations and blood demand for the last 12 months."""
    from datetime import date

    today = date.today()
    labels = previous_months(11, today) + [f"{today.year:04d}-{today.month:02d}"]

    donations = Counter()
    for d in db.scalars(select(Donation.donated_on)).all():
        donations[d.strftime("%Y-%m")] += 1

    req_count, req_units = Counter(), Counter()
    for created, units in db.execute(select(BloodRequest.created_at, BloodRequest.units)).all():
        key = created.strftime("%Y-%m")
        req_count[key] += 1
        req_units[key] += units

    return [
        {
            "month": m,
            "donations": donations.get(m, 0),
            "requests": req_count.get(m, 0),
            "units_requested": req_units.get(m, 0),
        }
        for m in labels
    ]


@router.get("/forecast", response_model=List[ForecastItem])
def forecast(user: User = Depends(allowed), db: Session = Depends(get_db)):
    """Demand forecast per blood group (decision support, not medical advice)."""
    rows = [
        (group, created.strftime("%Y-%m"), units)
        for group, created, units in db.execute(
            select(BloodRequest.blood_group, BloodRequest.created_at, BloodRequest.units)
        ).all()
    ]
    stock = dict(
        db.execute(
            select(Inventory.blood_group, func.coalesce(func.sum(Inventory.available_units), 0))
            .group_by(Inventory.blood_group)
        ).all()
    )
    return forecast_demand(rows, {g: int(v) for g, v in stock.items()})
