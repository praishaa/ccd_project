from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

BloodGroup = Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
Urgency = Literal["low", "medium", "high", "critical"]
RequestStatus = Literal["pending", "matched", "fulfilled", "cancelled"]


# ---------- auth ----------
class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: Literal["donor", "hospital"]
    # donor-only fields
    blood_group: Optional[BloodGroup] = None
    city: Optional[str] = Field(default=None, max_length=80)
    phone: Optional[str] = Field(default=None, max_length=20)
    last_donation_date: Optional[date] = None


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- donors ----------
class DonorOut(BaseModel):
    id: int
    user_id: int
    name: str
    email: str
    blood_group: str
    city: str
    phone: Optional[str]
    last_donation_date: Optional[date]
    available: bool
    eligible: bool
    next_eligible_date: Optional[date]
    days_until_eligible: int


class DonorUpdate(BaseModel):
    city: Optional[str] = Field(default=None, min_length=1, max_length=80)
    phone: Optional[str] = Field(default=None, max_length=20)
    available: Optional[bool] = None


class DonationCreate(BaseModel):
    donated_on: Optional[date] = None
    units: int = Field(default=1, ge=1, le=2)


class DonationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    donated_on: date
    units: int


# ---------- requests ----------
class RequestCreate(BaseModel):
    blood_group: BloodGroup
    units: int = Field(ge=1, le=50)
    urgency: Urgency
    required_date: date
    city: str = Field(min_length=1, max_length=80)


class RequestStatusUpdate(BaseModel):
    status: RequestStatus


class RequestOut(BaseModel):
    id: int
    requester_id: int
    hospital: str
    blood_group: str
    units: int
    urgency: str
    required_date: date
    city: str
    status: str
    priority_score: int
    priority_label: str
    created_at: datetime
    donors_notified: Optional[int] = None


class DonorMatchOut(BaseModel):
    donor_id: int
    name: str
    blood_group: str
    city: str
    phone: Optional[str]
    last_donation_date: Optional[date]
    exact_match: bool


# ---------- inventory ----------
class InventoryOut(BaseModel):
    id: int
    org_id: int
    org_name: str
    blood_group: str
    available_units: int
    incoming_units: int
    issued_units: int
    expired_units: int
    min_threshold: int
    status: str


class InventoryUpdate(BaseModel):
    min_threshold: Optional[int] = Field(default=None, ge=0, le=1000)
    incoming_units: Optional[int] = Field(default=None, ge=0, le=100000)


class UnitsIn(BaseModel):
    units: int = Field(gt=0, le=1000)


# ---------- notifications ----------
class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    message: str
    request_id: Optional[int]
    is_read: bool
    created_at: datetime


class MessageOut(BaseModel):
    detail: str
    count: Optional[int] = None


# ---------- analytics ----------
class ForecastItem(BaseModel):
    blood_group: str
    history: List[int]
    predicted_units: float
    baseline_units: float
    change_pct: Optional[float]
    trend: str
    current_stock: int
    shortage_risk: bool
    recommendation: str
