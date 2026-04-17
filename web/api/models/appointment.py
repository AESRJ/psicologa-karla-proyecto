"""
appointment.py
Pydantic schemas — request/response models for the appointments API.
These are separate from the SQLAlchemy ORM models in db_models.py.
"""

from __future__ import annotations

from datetime import date, time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TherapyType(str, Enum):
    individual    = "individual"
    pareja        = "pareja"
    familia       = "familia"
    adolescentes  = "adolescentes"
    online        = "online"


class AppointmentStatus(str, Enum):
    pending   = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"


# ── Prices — single source of truth ──────────────────────────

PRICES: dict[TherapyType, int] = {
    TherapyType.individual:   600,
    TherapyType.pareja:       800,
    TherapyType.familia:      1000,
    TherapyType.adolescentes: 600,
    TherapyType.online:       600,
}


# ── Request schemas ───────────────────────────────────────────

class AppointmentCreate(BaseModel):
    patient_name:  str       = Field(..., min_length=2, max_length=120)
    patient_phone: str       = Field(..., min_length=7, max_length=20)
    patient_email: Optional[str] = Field(None, max_length=200)
    therapy_type:  TherapyType
    date:          date
    slot:          str       = Field(..., pattern=r"^\d{2}:\d{2}$",
                                     description="Hora de inicio HH:MM (24 h)")
    price:         int       = Field(..., gt=0)
    notes:         Optional[str] = Field(None, max_length=500)


class StatusUpdate(BaseModel):
    status: AppointmentStatus


# ── Response schemas ──────────────────────────────────────────

class AppointmentOut(BaseModel):
    id:              int
    patient_name:    str
    patient_phone:   str
    patient_email:   Optional[str]
    therapy_type:    TherapyType
    date:            date
    slot:            str
    status:          AppointmentStatus
    price:           int
    notes:           Optional[str]

    model_config = {"from_attributes": True}


# ── Availability schemas ──────────────────────────────────────

class DayStatus(str, Enum):
    available   = "available"
    limited     = "limited"
    unavailable = "unavailable"


class AvailableSlot(BaseModel):
    time:      str   # "HH:MM"
    available: bool


class SlotsResponse(BaseModel):
    date:  date
    slots: list[AvailableSlot]
