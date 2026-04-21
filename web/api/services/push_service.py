"""
push_service.py
Envía push notifications vía Firebase Cloud Messaging (firebase-admin SDK).
"""

from __future__ import annotations

import json
import os
import logging

logger = logging.getLogger(__name__)

_initialized = False


def _init_firebase():
    global _initialized
    if _initialized:
        return True

    raw = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")
    if not raw:
        logger.warning("FIREBASE_SERVICE_ACCOUNT_JSON not set — push disabled")
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials

        info = json.loads(raw)
        cred = credentials.Certificate(info)
        firebase_admin.initialize_app(cred)
        _initialized = True
        return True
    except Exception as e:
        logger.error("Firebase init failed: %s", e)
        return False


def send_push(token: str, title: str, body: str) -> bool:
    if not _init_firebase():
        return False

    from firebase_admin import messaging

    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                sound="default",
                channel_id="new_appointments",
            ),
        ),
        token=token,
    )

    try:
        messaging.send(message)
        return True
    except Exception as e:
        logger.error("FCM send failed: %s", e)
        return False


def notify_new_appointment(db_session, appointment) -> None:
    from api.models.db_models import DeviceToken

    tokens = db_session.query(DeviceToken).all()
    if not tokens:
        logger.info("No device tokens registered — skipping push")
        return

    therapy_labels = {
        "individual": "Terapia Individual",
        "pareja": "Terapia en Pareja",
        "familia": "Terapia Familiar",
        "adolescentes": "Terapia para Adolescentes",
        "online": "Terapia en Línea",
    }
    label = therapy_labels.get(appointment.therapy_type, appointment.therapy_type)
    title = "Nueva Cita"
    body = (
        f"{appointment.patient_name} — "
        f"{appointment.appointment_date} {appointment.appointment_time.strftime('%H:%M')} — "
        f"{label}"
    )

    for t in tokens:
        send_push(t.token, title, body)
