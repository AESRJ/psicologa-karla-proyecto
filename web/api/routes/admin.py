"""
admin.py
Endpoints de administración para la app móvil de Karla.

Autenticación: Bearer token — el valor debe coincidir con ADMIN_PIN en Railway.

Rutas:
  POST  /admin/login              — verificar PIN, devuelve token
  GET   /admin/appointments       — citas del día o rango
  PATCH /admin/appointments/{id}/status — confirmar / cancelar
  GET   /admin/blocked-days       — listar días bloqueados
  POST  /admin/blocked-days       — bloquear un día
  DELETE /admin/blocked-days/{date} — desbloquear un día
"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.appointment import (
    AppointmentOut,
    AppointmentStatus,
    BlockedDayCreate,
    BlockedDayOut,
    StatusUpdate,
    TherapyType,
    PRICES,
    AppointmentCreate,
)
from api.models.db_models import Appointment, BlockedDay, DeviceToken

router = APIRouter(prefix="/admin", tags=["admin"])

# ── Auth ───────────────────────────────────────────────────────────────────

def _verify_token(authorization: str = Header(...)):
    """Valida el header Authorization: Bearer {ADMIN_PIN}"""
    pin = os.getenv("ADMIN_PIN", "")
    if not pin:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_PIN no configurado en el servidor.",
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != pin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="PIN incorrecto.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


# ── Login ──────────────────────────────────────────────────────────────────

@router.post("/login")
async def login(authorization: str = Header(...)):
    """Verifica el PIN. Devuelve confirmación si es correcto."""
    _verify_token(authorization)
    return {"ok": True, "message": "Autenticación exitosa."}


# ── Appointments ───────────────────────────────────────────────────────────

@router.get("/appointments", response_model=list[AppointmentOut])
async def admin_list_appointments(
    date_:   Optional[date]              = Query(None, alias="date"),
    status_: Optional[AppointmentStatus] = Query(None, alias="status"),
    limit:   int                         = Query(200, ge=1, le=500),
    db:      Session                     = Depends(get_db),
    _:       str                         = Depends(_verify_token),
) -> list[AppointmentOut]:
    """Lista citas, opcionalmente filtradas por fecha y/o estado."""
    q = db.query(Appointment)
    if date_:    q = q.filter(Appointment.appointment_date == date_)
    if status_:  q = q.filter(Appointment.status == status_)
    rows = q.order_by(
        Appointment.appointment_date,
        Appointment.appointment_time,
    ).limit(limit).all()
    return [_to_out(r) for r in rows]


@router.post("/appointments", response_model=AppointmentOut,
             status_code=status.HTTP_201_CREATED)
async def admin_create_appointment(
    payload: AppointmentCreate,
    db:      Session = Depends(get_db),
    _:       str     = Depends(_verify_token),
) -> AppointmentOut:
    """Agenda una cita manualmente (sin validar precio)."""
    from api.routes.appointments import _booked_slots_for_date
    booked = _booked_slots_for_date(payload.date, db)
    if payload.slot in booked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El horario {payload.slot} ya está ocupado.",
        )
    if db.query(BlockedDay).filter(BlockedDay.date == payload.date).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ese día está bloqueado.",
        )
    from datetime import time as dtime
    h, m = map(int, payload.slot.split(":"))
    record = Appointment(
        patient_name     = payload.patient_name,
        patient_phone    = payload.patient_phone,
        patient_email    = payload.patient_email,
        therapy_type     = payload.therapy_type,
        appointment_date = payload.date,
        appointment_time = dtime(h, m),
        status           = AppointmentStatus.confirmed,
        price            = PRICES[payload.therapy_type],
        notes            = payload.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_out(record)


@router.patch("/appointments/{appointment_id}/status",
              response_model=AppointmentOut)
async def admin_update_status(
    appointment_id: int,
    body:           StatusUpdate,
    db:             Session = Depends(get_db),
    _:              str     = Depends(_verify_token),
) -> AppointmentOut:
    row = db.get(Appointment, appointment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Cita no encontrada.")
    row.status = body.status
    db.commit()
    db.refresh(row)
    return _to_out(row)


# ── Recent appointments (for polling notifications) ───────────────────────

@router.get("/appointments/recent", response_model=list[AppointmentOut])
async def admin_recent_appointments(
    since: datetime = Query(...),
    db:    Session  = Depends(get_db),
    _:     str      = Depends(_verify_token),
) -> list[AppointmentOut]:
    """Citas creadas después de una fecha/hora dada (para notificaciones)."""
    rows = (
        db.query(Appointment)
        .filter(Appointment.created_at > since)
        .order_by(Appointment.created_at.desc())
        .limit(50)
        .all()
    )
    return [_to_out(r) for r in rows]


# ── Blocked days ───────────────────────────────────────────────────────────

@router.get("/blocked-days", response_model=list[BlockedDayOut])
async def list_blocked_days(
    db: Session = Depends(get_db),
    _:  str     = Depends(_verify_token),
) -> list[BlockedDayOut]:
    rows = db.query(BlockedDay).order_by(BlockedDay.date).all()
    return rows


@router.post("/blocked-days", response_model=BlockedDayOut,
             status_code=status.HTTP_201_CREATED)
async def block_day(
    payload: BlockedDayCreate,
    db:      Session = Depends(get_db),
    _:       str     = Depends(_verify_token),
) -> BlockedDayOut:
    existing = db.query(BlockedDay).filter(BlockedDay.date == payload.date).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ese día ya está bloqueado.",
        )
    row = BlockedDay(date=payload.date, reason=payload.reason)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/blocked-days/{date_str}",
               status_code=status.HTTP_204_NO_CONTENT)
async def unblock_day(
    date_str: str,
    db:       Session = Depends(get_db),
    _:        str     = Depends(_verify_token),
):
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida (YYYY-MM-DD).")
    row = db.query(BlockedDay).filter(BlockedDay.date == d).first()
    if not row:
        raise HTTPException(status_code=404, detail="Ese día no está bloqueado.")
    db.delete(row)
    db.commit()


# ── Device tokens (FCM) ───────────────────────────────────────────────

@router.post("/register-device", status_code=status.HTTP_201_CREATED)
async def register_device(
    payload: dict,
    db:      Session = Depends(get_db),
    _:       str     = Depends(_verify_token),
):
    """Registra un token FCM para recibir push notifications."""
    token = payload.get("token", "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token requerido.")
    existing = db.query(DeviceToken).filter(DeviceToken.token == token).first()
    if existing:
        return {"ok": True, "message": "Token ya registrado."}
    db.add(DeviceToken(token=token))
    db.commit()
    return {"ok": True, "message": "Token registrado."}


# ── Debug push (temporal) ──────────────────────────────────────────────────

@router.get("/push-status")
async def push_status(
    db: Session = Depends(get_db),
    _:  str     = Depends(_verify_token),
):
    """Diagnóstico de notificaciones push."""
    import os
    tokens = db.query(DeviceToken).all()
    has_firebase = bool(os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", ""))
    return {
        "firebase_configured": has_firebase,
        "registered_devices": len(tokens),
        "tokens": [t.token[:20] + "..." for t in tokens],
    }


# ── Helper ─────────────────────────────────────────────────────────────────

def _to_out(row: Appointment) -> AppointmentOut:
    return AppointmentOut(
        id            = row.id,
        patient_name  = row.patient_name,
        patient_phone = row.patient_phone,
        patient_email = row.patient_email,
        therapy_type  = TherapyType(row.therapy_type),
        date          = row.appointment_date,
        slot          = row.appointment_time.strftime("%H:%M"),
        status        = AppointmentStatus(row.status),
        price         = row.price,
        notes         = row.notes,
    )
