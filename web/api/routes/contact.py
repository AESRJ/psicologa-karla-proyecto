"""
contact.py
Contact form endpoint — receives messages from the website.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, status

router = APIRouter(prefix="/contact", tags=["contact"])


class ContactMessage(BaseModel):
    name:    str      = Field(..., min_length=2, max_length=120)
    email:   EmailStr
    phone:   str      = Field(..., min_length=7, max_length=20)
    message: str      = Field(..., min_length=10, max_length=1000)


class ContactAck(BaseModel):
    ok:      bool = True
    message: str  = "Mensaje recibido. Te responderemos a la brevedad."


@router.post("/", response_model=ContactAck, status_code=status.HTTP_200_OK)
async def send_contact_message(payload: ContactMessage) -> ContactAck:
    """
    Receive a contact form submission.
    TODO: forward the message via email or WhatsApp notification.
    """
    # Placeholder — wire up email/WhatsApp notification here
    print(f"[contact] New message from {payload.name} <{payload.email}>")
    return ContactAck()
