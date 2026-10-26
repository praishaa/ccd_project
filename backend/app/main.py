from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from . import models  # noqa: F401  (registers tables)
from .config import CORS_ORIGINS
from .database import Base, SessionLocal, engine
from .routers import analytics, auth, donors, inventory, notifications, requests


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Smart Blood Donation Management System",
    description="Prototype API - uses synthetic data, decision support only.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (
    auth.router,
    donors.router,
    requests.router,
    inventory.router,
    notifications.router,
    analytics.router,
):
    app.include_router(r)


@app.get("/health", tags=["health"])
def health():
    """Used by load balancers / monitoring later. Also checks the database."""
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok"}
