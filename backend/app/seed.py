"""Fill the database with SYNTHETIC demo data.

    python -m app.seed            # only if the database is empty
    python -m app.seed --reset    # drop all tables and re-create demo data
"""

import random
import sys
from datetime import date, datetime, timedelta

from sqlalchemy import select

from . import models  # noqa: F401
from .auth import hash_password
from .database import Base, SessionLocal, engine
from .models import BloodRequest, Donation, Donor, Inventory, User
from .services import BLOOD_GROUPS, compute_priority

CITIES = ["Udupi", "Manipal", "Mangalore", "Bengaluru"]
FIRST = ["Aarav", "Isha", "Aditi", "Rohan", "Priya", "Karthik", "Sneha", "Vikram", "Ananya",
         "Rahul", "Meera", "Arjun", "Divya", "Nikhil", "Pooja", "Suresh", "Kavya", "Manoj",
         "Neha", "Varun", "Lakshmi", "Harsh", "Ritu", "Sanjay", "Deepa"]
LAST = ["Shetty", "Rao", "Nayak", "Prabhu", "Kamath", "Bhat", "Hegde", "Pai", "Naik", "Shenoy",
        "Kini", "Acharya", "Poojary", "Salian", "Tiwari", "Narsaria", "Sharma", "Gowda"]
GROUP_WEIGHTS = [("O+", 35), ("B+", 30), ("A+", 22), ("AB+", 7),
                 ("O-", 2), ("B-", 2), ("A-", 1), ("AB-", 1)]
# base monthly demand (units) per blood group
BASE_DEMAND = {"O+": 8, "A+": 6, "B+": 5, "O-": 3, "A-": 2, "B-": 2, "AB+": 2, "AB-": 1}

ADMIN = ("Admin", "admin@bloodsys.com", "Admin@123")
ORGS = [
    ("City General Hospital", "city.hospital@bloodsys.com"),
    ("Red Cross Blood Bank", "redcross@bloodsys.com"),
]
ORG_PASSWORD = "Hospital@123"
DONOR_PASSWORD = "Donor@123"


def month_start(today: date, months_back: int) -> date:
    y, m = today.year, today.month - months_back
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


def run(reset: bool = False) -> None:
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    random.seed(42)
    today = date.today()

    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.role == "admin")):
            print("Database already has data. Use --reset to wipe and re-seed.")
            return

        org_hash = hash_password(ORG_PASSWORD)
        donor_hash = hash_password(DONOR_PASSWORD)

        db.add(User(name=ADMIN[0], email=ADMIN[1], password_hash=hash_password(ADMIN[2]), role="admin"))
        orgs = []
        for name, email in ORGS:
            u = User(name=name, email=email, password_hash=org_hash, role="hospital")
            db.add(u)
            orgs.append(u)
        db.flush()

        # ---- donors (60) ----
        groups, weights = zip(*GROUP_WEIGHTS)
        donors = []
        for i in range(1, 61):
            u = User(
                name=f"{random.choice(FIRST)} {random.choice(LAST)}",
                email=f"donor{i}@bloodsys.com",
                password_hash=donor_hash,
                role="donor",
            )
            db.add(u)
            db.flush()
            n_donations = random.randint(0, 4)
            last = today - timedelta(days=random.randint(5, 300)) if n_donations else None
            d = Donor(
                user_id=u.id,
                blood_group=random.choices(groups, weights)[0],
                city=CITIES[(i - 1) % len(CITIES)],
                phone=f"98{random.randint(10000000, 99999999)}",
                last_donation_date=last,
                available=random.random() < 0.85,
            )
            db.add(d)
            db.flush()
            for k in range(n_donations):
                db.add(
                    Donation(
                        donor_id=d.id,
                        donated_on=last - timedelta(days=100 * k + random.randint(0, 20)),
                        units=1,
                    )
                )
            donors.append(d)

        # ---- inventory ----
        for org in orgs:
            for g in BLOOD_GROUPS:
                avail = random.randint(6, 25)
                if org.name == "Red Cross Blood Bank" and g == "O+":
                    avail = 4  # demo low-stock alert
                if org.name == "City General Hospital" and g == "AB-":
                    avail = 1
                db.add(
                    Inventory(
                        org_id=org.id,
                        blood_group=g,
                        available_units=avail,
                        incoming_units=random.randint(0, 5),
                        issued_units=random.randint(20, 80),
                        expired_units=random.randint(0, 6),
                        min_threshold=10,
                    )
                )

        # ---- historical requests: 8 months, O+ demand rising ----
        for back in range(8, 0, -1):
            start = month_start(today, back)
            growth = 1 + 0.12 * (8 - back)
            for g in BLOOD_GROUPS:
                factor = growth if g == "O+" else 1.0
                target = max(0, round(BASE_DEMAND[g] * factor + random.randint(-1, 1)))
                total = 0
                while total < target:
                    units = min(random.randint(1, 4), target - total)
                    total += units
                    created = datetime(start.year, start.month, 1) + timedelta(
                        days=random.randint(0, 26), hours=random.randint(0, 20)
                    )
                    req_date = created.date() + timedelta(days=random.randint(1, 7))
                    urgency = random.choice(["low", "medium", "medium", "high", "critical"])
                    db.add(
                        BloodRequest(
                            requester_id=random.choice(orgs).id,
                            blood_group=g,
                            units=units,
                            urgency=urgency,
                            required_date=req_date,
                            city=random.choice(CITIES),
                            status="fulfilled" if random.random() < 0.88 else "cancelled",
                            priority_score=compute_priority(
                                urgency, units, req_date, False, today=created.date()
                            ),
                            created_at=created,
                        )
                    )

        # ---- a few open requests this month ----
        for g, units, urgency, city in [
            ("O+", 3, "critical", "Udupi"),
            ("A+", 2, "high", "Manipal"),
            ("B-", 1, "medium", "Mangalore"),
        ]:
            req_date = today + timedelta(days=2)
            db.add(
                BloodRequest(
                    requester_id=orgs[0].id,
                    blood_group=g,
                    units=units,
                    urgency=urgency,
                    required_date=req_date,
                    city=city,
                    status="pending",
                    priority_score=compute_priority(urgency, units, req_date, False),
                )
            )

        db.commit()

    print("Demo data created.\n")
    print("Logins (email / password):")
    print(f"  Admin     : {ADMIN[1]} / {ADMIN[2]}")
    for name, email in ORGS:
        print(f"  Hospital  : {email} / {ORG_PASSWORD}   ({name})")
    print(f"  Donors    : donor1@bloodsys.com ... donor60@bloodsys.com / {DONOR_PASSWORD}")


if __name__ == "__main__":
    run(reset="--reset" in sys.argv)
