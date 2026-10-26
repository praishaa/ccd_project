from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)  # donor | hospital | admin
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    donor: Mapped[Optional["Donor"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Donor(Base):
    __tablename__ = "donors"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    blood_group: Mapped[str] = mapped_column(String(3), index=True)
    city: Mapped[str] = mapped_column(String(80), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    last_donation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    available: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="donor")
    donations: Mapped[List["Donation"]] = relationship(
        back_populates="donor", cascade="all, delete-orphan", order_by="Donation.donated_on.desc()"
    )


class Donation(Base):
    __tablename__ = "donations"

    id: Mapped[int] = mapped_column(primary_key=True)
    donor_id: Mapped[int] = mapped_column(ForeignKey("donors.id"), index=True)
    donated_on: Mapped[date] = mapped_column(Date, index=True)
    units: Mapped[int] = mapped_column(Integer, default=1)

    donor: Mapped["Donor"] = relationship(back_populates="donations")


class BloodRequest(Base):
    __tablename__ = "blood_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    blood_group: Mapped[str] = mapped_column(String(3), index=True)
    units: Mapped[int] = mapped_column(Integer)
    urgency: Mapped[str] = mapped_column(String(10))  # low | medium | high | critical
    required_date: Mapped[date] = mapped_column(Date)
    city: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True)
    priority_score: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    requester: Mapped["User"] = relationship()


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (UniqueConstraint("org_id", "blood_group", name="uq_inventory_org_group"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    blood_group: Mapped[str] = mapped_column(String(3))
    available_units: Mapped[int] = mapped_column(Integer, default=0)
    incoming_units: Mapped[int] = mapped_column(Integer, default=0)
    issued_units: Mapped[int] = mapped_column(Integer, default=0)
    expired_units: Mapped[int] = mapped_column(Integer, default=0)
    min_threshold: Mapped[int] = mapped_column(Integer, default=10)

    org: Mapped["User"] = relationship()


class Notification(Base):
    """Local stand-in for Azure Notification Hubs. Every alert is stored here
    so the UI can show it; later the same event can also be pushed to Azure."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(30))  # request | low_stock | reminder | status
    message: Mapped[str] = mapped_column(Text)
    request_id: Mapped[Optional[int]] = mapped_column(ForeignKey("blood_requests.id"), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
