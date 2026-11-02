from contextlib import asynccontextmanager
from fastapi import Depends, Header, HTTPException   # merge with your existing fastapi import
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Inventory
from .services import inventory_status
# plus the same "get_db" import line that analytics.py uses
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from fastapi import FastAPI, Header, HTTPException
from . import models  # noqa: F401  (registers tables)
from .config import CORS_ORIGINS
from .database import Base, SessionLocal, engine
from .routers import analytics, auth, donors, inventory, notifications, requests
import os
import logging

if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    from azure.monitor.opentelemetry import configure_azure_monitor
    configure_azure_monitor()

logger = logging.getLogger("inventory")
logger.setLevel(logging.INFO)
logger.info("request created: id=%s", request_id)


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

@app.post("/internal/low-stock-check")
def internal_low_stock_check(
    x_api_key: str = Header(None),
    db: Session = Depends(get_db),
):
    if x_api_key != os.getenv("FUNC_API_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    rows = db.scalars(select(Inventory)).all()
    low = [i for i in rows if inventory_status(i.available_units, i.min_threshold) != "OK"]
    for i in low:
        logger.warning(
            "low stock detected for item %s (qty=%s)", i.blood_group, i.available_units
        )
    return {"low_stock_count": len(low)}
@app.get("/health", tags=["health"])
def health():
    """Used by load balancers / monitoring later. Also checks the database."""
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok"}
