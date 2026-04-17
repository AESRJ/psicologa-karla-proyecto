from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class IncomingMessage(BaseModel):
    phone_number: str
    name: Optional[str] = None
    message_id: str
    text: str
    timestamp: datetime


class KarlaDecision(BaseModel):
    phone_number: str       # número del cliente
    decision: str           # "yo" o "agente"


class AppointmentInfo(BaseModel):
    phone_number: str
    customer_name: Optional[str] = None
    appointment_date: datetime
    appointment_type: Optional[str] = "Terapia psicológica"
    notes: Optional[str] = None
