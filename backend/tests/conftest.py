import os

# must be set before the app is imported
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import User


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def client(db_session):
    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    # no `with` block -> startup/lifespan (which touches the real DB) is skipped
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(db, name, email, role, password="Passw0rd!"):
    u = User(name=name, email=email, role=role, password_hash=hash_password(password))
    db.add(u)
    db.commit()
    return u


def login(client, email, password="Passw0rd!"):
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def register_donor(client, email, group="O+", city="Udupi", **extra):
    body = {
        "name": "Test Donor",
        "email": email,
        "password": "Passw0rd!",
        "role": "donor",
        "blood_group": group,
        "city": city,
        **extra,
    }
    r = client.post("/auth/register", json=body)
    assert r.status_code == 201, r.text
    return r.json()
