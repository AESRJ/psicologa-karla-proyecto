"""
appointments.py
REST endpoints for the appointment scheduling system.

Routes:
  GET  /appointments/calendar          — colour state per day in a month
  GET  /appointments/slots             — available slots for a date
  POST /appointments                   — create appointment
  GET  /appointments                   — list all (for Android app)
  GET  /appointments/{id}              — single appointment
  PATCH /appointments/{id}/status      — confirm / cancel
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.appointment import (
    AppointmentCreate,
    AppointmentOut,
    AppointmentStatus,
    AvailableSlot,
    DayStatus,
    PRICES,
    SlotsResponse,
    StatusUpdate,
    TherapyType,
)
from api.models.db_models import Appointment, BlockedDay
from api.services.email_service import send_confirmation

router = APIRouter(prefix="/appointments", tags=["appointments"])

# ── Business hours ─────────────────────────────────────────────────────────
# Mon–Fri  16:00–21:00 (5 slots)
# Sat–Sun  09:00–21:00 (12 slots)

def _slots_for_date(d: date) -> list[str]:
    """Return HH:MM strings for all business-hour slots on a given date."""
    dow = d.weekday()           # 0=Mon … 6=Sun
    is_weekend = dow >= 5
    start, end = (9, 21) if is_weekend else (16, 21)
    return [f"{h:02d}:00" for h in range(start, end)]


def _total_slots(d: date) -> int:
    return len(_slots_for_date(d))


def _booked_slots_for_date(d: date, db: Session) -> set[str]:
    rows = (
        db.query(Appointment.appointment_time)
        .filter(
            Appointment.appointment_date == d,
            Appointment.status != AppointmentStatus.cancelled,
        )
        .all()
    )
    return {r.appointment_time.strftime("%H:%M") for r in rows}


def _day_status(d: date, db: Session) -> DayStatus:
    """Compute green / yellow / red for a calendar day."""
    # Blocked by psychologist?
    if db.query(BlockedDay).filter(BlockedDay.date == d).first():
        return DayStatus.unavailable

    total  = _total_slots(d)
    booked = len(_booked_slots_for_date(d, db))
    free   = total - booked

    if free <= 0:
        return DayStatus.unavailable          # rojo   — sin horarios disponibles
    if booked < 2:
        return DayStatus.available            # verde  — 0 o 1 cita reservada
    return DayStatus.limited                  # amarillo — 2 o más citas reservadas


# ── Debug endpoint (temporal) ─────────────────────────────────────────────

@router.get("/debug")
async def debug_db(db: Session = Depends(get_db)):
    """Muestra el estado real de la BD — solo para diagnóstico."""
    total = db.query(Appointment).count()
    sample = db.query(Appointment).order_by(Appointment.id.desc()).limit(10).all()
    return {
        "total_appointments": total,
        "last_10": [
            {
                "id":     a.id,
                "date":   str(a.appointment_date),
                "time":   str(a.appointment_time),
                "status": a.status,
                "name":   a.patient_name,
            }
            for a in sample
        ],
    }


# ── Calendar endpoint ──────────────────────────────────────────────────────

@router.get("/calendar", response_model=dict[str, DayStatus])
async def get_calendar(
    year:     int      = Query(..., ge=2024, le=2100),
    month:    int      = Query(..., ge=1,    le=12),
    db:       Session  = Depends(get_db),
    response: Response = None,
) -> dict[str, DayStatus]:
    """
    Return the availability state for every day in the requested month.
    Past days are omitted. Keys are 'YYYY-MM-DD' strings.
    """
    if response:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

    today      = datetime.utcnow().date()
    days_count = (date(year, month % 12 + 1, 1) - date(year, month, 1)).days \
                 if month < 12 else 31  # December has 31 days

    # Use a robust approach to find month length
    import calendar as cal_mod
    days_count = cal_mod.monthrange(year, month)[1]

    result: dict[str, DayStatus] = {}
    for d in range(1, days_count + 1):
        day = date(year, month, d)
        if day < today:
            continue
        result[day.isoformat()] = _day_status(day, db)

    return result


# ── Slots endpoint ─────────────────────────────────────────────────────────

@router.get("/slots", response_model=SlotsResponse)
async def get_slots(
    date_: date = Query(..., alias="date"),
    db:    Session = Depends(get_db),
) -> SlotsResponse:
    """Return all business-hour slots for a date with their availability."""
    booked = _booked_slots_for_date(date_, db)
    slots  = [
        AvailableSlot(time=t, available=t not in booked)
        for t in _slots_for_date(date_)
    ]
    return SlotsResponse(date=date_, slots=slots)


# ── Create appointment ─────────────────────────────────────────────────────

@router.post("/", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    payload: AppointmentCreate,
    db:      Session = Depends(get_db),
) -> AppointmentOut:
    """Book a new appointment."""
    # Verify slot is still free
    booked = _booked_slots_for_date(payload.date, db)
    if payload.slot in booked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El horario {payload.slot} ya está ocupado para {payload.date}.",
        )

    # Verify day is not blocked
    if db.query(BlockedDay).filter(BlockedDay.date == payload.date).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La psicóloga no tiene disponibilidad ese día.",
        )

    # Validate price matches therapy type
    expected_price = PRICES[payload.therapy_type]
    if payload.price != expected_price:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"El precio para {payload.therapy_type} debe ser ${expected_price}.",
        )

    h, m   = map(int, payload.slot.split(':'))
    record = Appointment(
        patient_name     = payload.patient_name,
        patient_phone    = payload.patient_phone,
        patient_email    = payload.patient_email,
        therapy_type     = payload.therapy_type,
        appointment_date = payload.date,
        appointment_time = time(h, m),
        status           = AppointmentStatus.pending,
        price            = payload.price,
        notes            = payload.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Enviar correo de confirmación (no bloquea si falla)
    send_confirmation(record)

    return _to_out(record)


# ── List appointments (for Android app) ───────────────────────────────────

@router.get("/", response_model=list[AppointmentOut])
async def list_appointments(
    date_:   Optional[date]              = Query(None,        alias="date"),
    status_: Optional[AppointmentStatus] = Query(None,        alias="status"),
    limit:   int                         = Query(100, ge=1, le=500),
    db:      Session = Depends(get_db),
) -> list[AppointmentOut]:
    """List appointments, optionally filtered by date and/or status."""
    q = db.query(Appointment)
    if date_:    q = q.filter(Appointment.appointment_date == date_)
    if status_:  q = q.filter(Appointment.status == status_)
    rows = q.order_by(Appointment.appointment_date, Appointment.appointment_time)\
            .limit(limit).all()
    return [_to_out(r) for r in rows]


# ── Get single appointment ─────────────────────────────────────────────────

@router.get("/{appointment_id}", response_model=AppointmentOut)
async def get_appointment(
    appointment_id: int,
    db:             Session = Depends(get_db),
) -> AppointmentOut:
    row = db.get(Appointment, appointment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Cita no encontrada.")
    return _to_out(row)


# ── Update status ──────────────────────────────────────────────────────────

@router.patch("/{appointment_id}/status", response_model=AppointmentOut)
async def update_status(
    appointment_id: int,
    body:           StatusUpdate,
    db:             Session = Depends(get_db),
) -> AppointmentOut:
    row = db.get(Appointment, appointment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Cita no encontrada.")
    row.status = body.status
    db.commit()
    db.refresh(row)
    return _to_out(row)


# ── Helpers ────────────────────────────────────────────────────────────────

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
