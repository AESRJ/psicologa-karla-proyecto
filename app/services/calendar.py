"""
Integración con Google Calendar para agendar citas automáticamente.
Requiere credenciales OAuth2 de Google Cloud Console.
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Optional
import pytz

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings

logger = logging.getLogger(__name__)

# Permisos requeridos para Google Calendar
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    """
    Obtiene el servicio de Google Calendar con autenticación OAuth2.
    La primera vez abrirá el navegador para autorizar. Luego usa el token guardado.
    """
    creds = None

    if os.path.exists(settings.google_token_file):
        creds = Credentials.from_authorized_user_file(settings.google_token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(settings.google_credentials_file):
                raise FileNotFoundError(
                    f"No se encontró el archivo de credenciales: {settings.google_credentials_file}\n"
                    "Descárgalo desde Google Cloud Console → APIs & Services → Credentials"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                settings.google_credentials_file, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(settings.google_token_file, "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


async def create_appointment(
    customer_name: str,
    appointment_date: datetime,
    appointment_type: str = "Terapia psicológica",
    modality: str = "presencial",
    phone_number: str = "",
    notes: str = "",
    duration_minutes: int = 60,
) -> Optional[str]:
    """
    Crea un evento en Google Calendar para la cita.

    Returns:
        El ID del evento creado, o None si falló.
    """
    try:
        service = get_calendar_service()

        # Asegurar que la fecha tiene timezone
        tz = settings.tz
        if appointment_date.tzinfo is None:
            appointment_date = tz.localize(appointment_date)

        end_date = appointment_date + timedelta(minutes=duration_minutes)

        # Descripción del evento
        description_lines = [
            f"📱 WhatsApp: +{phone_number}" if phone_number else "",
            f"🎯 Tipo de terapia: {appointment_type}",
            f"💻 Modalidad: {modality}",
            f"📝 Notas: {notes}" if notes else "",
            "",
            "Cita agendada automáticamente por Ast-titox (Agente IA)",
        ]
        description = "\n".join(line for line in description_lines if line is not None)

        event = {
            "summary": f"Terapia — {customer_name}",
            "description": description,
            "start": {
                "dateTime": appointment_date.isoformat(),
                "timeZone": settings.timezone,
            },
            "end": {
                "dateTime": end_date.isoformat(),
                "timeZone": settings.timezone,
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 60},
                    {"method": "popup", "minutes": 15},
                ],
            },
            "colorId": "2",  # Verde (salud/bienestar)
        }

        created_event = service.events().insert(
            calendarId=settings.google_calendar_id,
            body=event,
        ).execute()

        event_id = created_event.get("id")
        event_link = created_event.get("htmlLink")
        logger.info(f"Cita creada en Calendar: {event_id} — {customer_name}")
        return event_id, event_link

    except HttpError as e:
        logger.error(f"Error de Google Calendar API: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Error creando cita: {e}")
        return None, None


async def check_availability(date: datetime, duration_minutes: int = 60) -> bool:
    """
    Verifica si hay disponibilidad en el calendario para la fecha/hora dada.
    Returns True si el slot está libre.
    """
    try:
        service = get_calendar_service()
        tz = settings.tz

        if date.tzinfo is None:
            date = tz.localize(date)

        time_min = date.isoformat()
        time_max = (date + timedelta(minutes=duration_minutes)).isoformat()

        events_result = service.events().list(
            calendarId=settings.google_calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
        ).execute()

        events = events_result.get("items", [])
        return len(events) == 0

    except Exception as e:
        logger.error(f"Error verificando disponibilidad: {e}")
        return True  # Asumir disponible si hay error
