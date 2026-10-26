"""Business rules: blood compatibility, donor eligibility, matching,
request priority, inventory status and notifications.

These are simple, predefined rules for an academic prototype and are
decision support only - not medical advice."""

from datetime import date, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import DONATION_INTERVAL_DAYS
from .models import BloodRequest, Donor, Inventory, Notification, User

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

# recipient blood group -> donor groups that are compatible (red cells)
COMPATIBLE_DONORS: Dict[str, List[str]] = {
    "O-": ["O-"],
    "O+": ["O-", "O+"],
    "A-": ["O-", "A-"],
    "A+": ["O-", "O+", "A-", "A+"],
    "B-": ["O-", "B-"],
    "B+": ["O-", "O+", "B-", "B+"],
    "AB-": ["O-", "A-", "B-", "AB-"],
    "AB+": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
}

# donor blood group -> recipient groups they can donate to
COMPATIBLE_RECIPIENTS: Dict[str, List[str]] = {
    donor: [r for r, donors in COMPATIBLE_DONORS.items() if donor in donors]
    for donor in BLOOD_GROUPS
}

URGENCY_WEIGHT = {"low": 1, "medium": 2, "high": 3, "critical": 4}


# ---------- eligibility ----------
def eligibility_info(donor: Donor, today: Optional[date] = None) -> dict:
    today = today or date.today()
    if donor.last_donation_date is None:
        return {"eligible": True, "next_eligible_date": None, "days_until_eligible": 0}
    next_date = donor.last_donation_date + timedelta(days=DONATION_INTERVAL_DAYS)
    days = max((next_date - today).days, 0)
    return {
        "eligible": today >= next_date,
        "next_eligible_date": next_date,
        "days_until_eligible": days,
    }


def is_eligible(donor: Donor, today: Optional[date] = None) -> bool:
    return eligibility_info(donor, today)["eligible"]


# ---------- matching ----------
def find_matches(db: Session, req: BloodRequest) -> List[Donor]:
    """Donors with a compatible blood group, in the request city, marked
    available and past the donation interval. Exact group matches come
    first, then donors who have rested longest."""
    groups = COMPATIBLE_DONORS[req.blood_group]
    donors = db.scalars(
        select(Donor).where(
            Donor.blood_group.in_(groups),
            Donor.available.is_(True),
            func.lower(Donor.city) == req.city.strip().lower(),
        )
    ).all()
    eligible = [d for d in donors if is_eligible(d)]
    eligible.sort(
        key=lambda d: (d.blood_group != req.blood_group, d.last_donation_date or date.min)
    )
    return eligible


# ---------- priority ----------
def compute_priority(
    urgency: str,
    units: int,
    required_date: date,
    stock_is_short: bool,
    today: Optional[date] = None,
) -> int:
    """0-100 score from urgency, quantity, time remaining and stock."""
    today = today or date.today()
    days_left = max((required_date - today).days, 0)
    score = URGENCY_WEIGHT[urgency] * 15  # up to 60
    score += min(units, 10) * 2  # up to 20
    score += max(0, 10 - days_left)  # up to 10
    if stock_is_short:
        score += 10
    return min(score, 100)


def priority_label(score: int) -> str:
    if score >= 70:
        return "High"
    if score >= 45:
        return "Medium"
    return "Low"


# ---------- inventory ----------
def inventory_status(available: int, threshold: int) -> str:
    if available <= 0:
        return "Out of Stock"
    if available < threshold:
        return "Low Stock"
    return "OK"


def total_available(db: Session, blood_group: str) -> int:
    return int(
        db.scalar(
            select(func.coalesce(func.sum(Inventory.available_units), 0)).where(
                Inventory.blood_group == blood_group
            )
        )
        or 0
    )


def ensure_inventory_rows(db: Session, org_id: int) -> None:
    existing = set(
        db.scalars(select(Inventory.blood_group).where(Inventory.org_id == org_id)).all()
    )
    for group in BLOOD_GROUPS:
        if group not in existing:
            db.add(Inventory(org_id=org_id, blood_group=group))
    db.commit()


# ---------- notifications ----------
def notify(
    db: Session,
    user_id: int,
    type_: str,
    message: str,
    request_id: Optional[int] = None,
    dedupe: bool = False,
) -> Optional[Notification]:
    if dedupe:
        exists = db.scalar(
            select(Notification.id).where(
                Notification.user_id == user_id,
                Notification.message == message,
                Notification.is_read.is_(False),
            )
        )
        if exists:
            return None
    n = Notification(user_id=user_id, type=type_, message=message, request_id=request_id)
    db.add(n)
    return n


def admin_ids(db: Session) -> List[int]:
    return list(db.scalars(select(User.id).where(User.role == "admin")).all())
