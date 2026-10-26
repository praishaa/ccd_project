from datetime import date, timedelta

from app.ml import forecast_demand, previous_months
from app.models import Donor
from app.services import (
    COMPATIBLE_DONORS,
    COMPATIBLE_RECIPIENTS,
    compute_priority,
    inventory_status,
    priority_label,
)

from .conftest import login, make_user, register_donor


# ---------- pure rules ----------
def test_blood_compatibility_rules():
    assert COMPATIBLE_DONORS["O-"] == ["O-"]
    assert set(COMPATIBLE_DONORS["AB+"]) == {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}
    assert "AB+" in COMPATIBLE_RECIPIENTS["O-"]  # O- donates to everyone
    assert COMPATIBLE_RECIPIENTS["AB+"] == ["AB+"]  # AB+ donates only to AB+


def test_priority_and_inventory_status():
    today = date.today()
    hi = compute_priority("critical", 10, today, True, today)
    lo = compute_priority("low", 1, today + timedelta(days=30), False, today)
    assert hi == 100 and lo < 45
    assert priority_label(hi) == "High" and priority_label(lo) == "Low"
    assert inventory_status(0, 10) == "Out of Stock"
    assert inventory_status(4, 10) == "Low Stock"
    assert inventory_status(10, 10) == "OK"


# ---------- auth ----------
def test_register_login_me_and_duplicates(client):
    register_donor(client, "a@test.com")
    assert client.post("/auth/register", json={
        "name": "Dup", "email": "A@test.com", "password": "Passw0rd!",
        "role": "donor", "blood_group": "A+", "city": "Udupi"}).status_code == 409
    h = login(client, "a@test.com")
    me = client.get("/auth/me", headers=h).json()
    assert me["email"] == "a@test.com" and me["role"] == "donor"
    bad = client.post("/auth/login", json={"email": "a@test.com", "password": "wrong"})
    assert bad.status_code == 401
    assert client.get("/auth/me").status_code == 401


def test_donor_needs_blood_group_and_city(client):
    r = client.post("/auth/register", json={
        "name": "No Group", "email": "n@test.com", "password": "Passw0rd!", "role": "donor"})
    assert r.status_code == 422


def test_admin_role_cannot_self_register(client):
    r = client.post("/auth/register", json={
        "name": "Evil", "email": "e@test.com", "password": "Passw0rd!", "role": "admin"})
    assert r.status_code == 422


# ---------- donors ----------
def test_donation_interval_rule(client):
    register_donor(client, "d@test.com")
    h = login(client, "d@test.com")
    r = client.post("/donors/me/donations", json={}, headers=h)
    assert r.status_code == 201
    body = r.json()
    assert body["eligible"] is False and body["days_until_eligible"] == 90
    again = client.post("/donors/me/donations", json={}, headers=h)
    assert again.status_code == 400
    assert len(client.get("/donors/me/donations", headers=h).json()) == 1


def test_donor_update_availability(client):
    register_donor(client, "u@test.com")
    h = login(client, "u@test.com")
    r = client.put("/donors/me", json={"available": False}, headers=h)
    assert r.json()["available"] is False


# ---------- requests & matching ----------
def test_request_matching_and_notifications(client, db_session):
    make_user(db_session, "City Hospital", "h@test.com", "hospital")
    register_donor(client, "match@test.com", group="O+", city="Udupi")            # compatible
    register_donor(client, "exact@test.com", group="A+", city="udupi")            # exact, case-insens.
    register_donor(client, "wrongcity@test.com", group="A+", city="Mangalore")    # other city
    register_donor(client, "incompat@test.com", group="B+", city="Udupi")         # incompatible
    register_donor(client, "recent@test.com", group="A+", city="Udupi",
                   last_donation_date=str(date.today() - timedelta(days=10)))     # not eligible
    register_donor(client, "off@test.com", group="A+", city="Udupi")              # unavailable
    ho = login(client, "off@test.com")
    client.put("/donors/me", json={"available": False}, headers=ho)

    h = login(client, "h@test.com")
    r = client.post("/requests", headers=h, json={
        "blood_group": "A+", "units": 2, "urgency": "high",
        "required_date": str(date.today() + timedelta(days=2)), "city": "Udupi"})
    assert r.status_code == 201, r.text
    req = r.json()
    assert req["donors_notified"] == 2 and req["status"] == "matched"

    matches = client.get(f"/requests/{req['id']}/matches", headers=h).json()
    assert [m["exact_match"] for m in matches] == [True, False]  # exact group first

    d = login(client, "match@test.com")
    notes = client.get("/notifications", headers=d).json()
    assert len(notes) == 1 and "A+" in notes[0]["message"]
    nearby = client.get("/requests/nearby", headers=d).json()
    assert [n["id"] for n in nearby] == [req["id"]]
    assert client.post(f"/notifications/{notes[0]['id']}/read", headers=d).json()["is_read"]

    # B+ donor can't donate to A+ -> sees nothing
    assert client.get("/requests/nearby", headers=login(client, "incompat@test.com")).json() == []


def test_request_without_donors_stays_pending(client, db_session):
    make_user(db_session, "H", "h@test.com", "hospital")
    h = login(client, "h@test.com")
    r = client.post("/requests", headers=h, json={
        "blood_group": "AB-", "units": 1, "urgency": "low",
        "required_date": str(date.today() + timedelta(days=5)), "city": "Nowhere"})
    assert r.json()["status"] == "pending" and r.json()["donors_notified"] == 0


def test_rbac_rules(client, db_session):
    make_user(db_session, "H1", "h1@test.com", "hospital")
    make_user(db_session, "H2", "h2@test.com", "hospital")
    make_user(db_session, "Admin", "admin@test.com", "admin")
    register_donor(client, "d@test.com")
    body = {"blood_group": "O+", "units": 1, "urgency": "low",
            "required_date": str(date.today() + timedelta(days=3)), "city": "Udupi"}

    assert client.post("/requests", json=body, headers=login(client, "d@test.com")).status_code == 403
    assert client.get("/analytics/summary", headers=login(client, "d@test.com")).status_code == 403
    assert client.get("/donors", headers=login(client, "d@test.com")).status_code == 403

    h1, h2, adm = (login(client, e) for e in ("h1@test.com", "h2@test.com", "admin@test.com"))
    rid = client.post("/requests", json=body, headers=h1).json()["id"]
    assert client.get(f"/requests/{rid}", headers=h2).status_code == 403  # someone else's
    assert client.get(f"/requests/{rid}", headers=adm).status_code == 200
    assert len(client.get("/requests", headers=h2).json()) == 0
    assert len(client.get("/requests", headers=adm).json()) == 1

    assert client.patch(f"/requests/{rid}/status", json={"status": "fulfilled"}, headers=h1).status_code == 200
    assert client.patch(f"/requests/{rid}/status", json={"status": "cancelled"}, headers=h1).status_code == 400


def test_past_required_date_rejected(client, db_session):
    make_user(db_session, "H", "h@test.com", "hospital")
    r = client.post("/requests", headers=login(client, "h@test.com"), json={
        "blood_group": "O+", "units": 1, "urgency": "low",
        "required_date": str(date.today() - timedelta(days=1)), "city": "Udupi"})
    assert r.status_code == 400


# ---------- inventory ----------
def test_inventory_flow_and_low_stock_alerts(client, db_session):
    make_user(db_session, "Red Cross", "bank@test.com", "hospital")
    make_user(db_session, "Admin", "admin@test.com", "admin")
    h = login(client, "bank@test.com")
    adm = login(client, "admin@test.com")

    rows = client.get("/inventory", headers=h).json()
    assert len(rows) == 8 and all(r["status"] == "Out of Stock" for r in rows)

    r = client.post("/inventory/O+/receive", json={"units": 4}, headers=h).json()
    assert r["available_units"] == 4 and r["status"] == "Low Stock"
    assert client.post("/inventory/O+/issue", json={"units": 10}, headers=h).status_code == 400
    r = client.post("/inventory/O+/issue", json={"units": 1}, headers=h).json()
    assert r["available_units"] == 3 and r["issued_units"] == 1
    r = client.post("/inventory/O+/expire", json={"units": 1}, headers=h).json()
    assert r["expired_units"] == 1
    client.post("/inventory/O+/receive", json={"units": 20}, headers=h)
    assert client.get("/inventory", headers=h).json()[0]  # still works

    alerts = client.get("/inventory/alerts", headers=h).json()
    assert "O+" not in [a["blood_group"] for a in alerts]  # O+ now healthy
    assert len(alerts) == 7

    # admin runs the check -> notifications for bank + admin, no duplicates on 2nd run
    first = client.post("/inventory/check-alerts", headers=adm).json()["count"]
    second = client.post("/inventory/check-alerts", headers=adm).json()["count"]
    assert first == 14 and second == 0
    assert client.post("/inventory/check-alerts", headers=h).status_code == 403

    # admin must name an organisation
    assert client.post("/inventory/A+/receive", json={"units": 1}, headers=adm).status_code == 400
    org_id = client.get("/auth/me", headers=h).json()["id"]
    assert client.post(f"/inventory/A+/receive?org_id={org_id}", json={"units": 1}, headers=adm).status_code == 200


# ---------- analytics & ML ----------
def test_forecast_detects_rising_demand():
    months = previous_months(6)
    rows = [("O+", m, u) for m, u in zip(months, [4, 6, 8, 10, 12, 14])]
    rows += [("A+", m, 5) for m in months]
    out = {r["blood_group"]: r for r in forecast_demand(rows, {"O+": 5, "A+": 50})}
    assert out["O+"]["trend"] == "rising" and out["O+"]["shortage_risk"] is True
    assert "outreach" in out["O+"]["recommendation"].lower()
    assert out["A+"]["trend"] == "stable" and out["A+"]["shortage_risk"] is False
    assert out["AB-"]["trend"] == "insufficient data"


def test_analytics_endpoints(client, db_session):
    make_user(db_session, "Admin", "admin@test.com", "admin")
    register_donor(client, "d@test.com", group="O+")
    adm = login(client, "admin@test.com")
    s = client.get("/analytics/summary", headers=adm).json()
    assert s["total_donors"] == 1 and len(s["donor_distribution"]) == 8
    t = client.get("/analytics/trends", headers=adm).json()
    assert len(t) == 12
    f = client.get("/analytics/forecast", headers=adm).json()
    assert len(f) == 8


def test_health(client):
    # /health uses the module-level SessionLocal (in-memory sqlite) - just needs to respond
    assert client.get("/health").status_code == 200
