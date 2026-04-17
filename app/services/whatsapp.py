"""
Servicio de integración con la API de WhatsApp Business Cloud (Meta).
Documentación: https://developers.facebook.com/docs/whatsapp/cloud-api
"""
import httpx
import logging
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)

WHATSAPP_API_URL = "https://graph.facebook.com/v21.0"


async def send_text_message(to: str, text: str) -> dict:
    """Envía un mensaje de texto a un número de WhatsApp."""
    url = f"{WHATSAPP_API_URL}/{settings.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        logger.info(f"Mensaje enviado a {to}: {text[:60]}...")
        return response.json()


async def send_interactive_buttons(to: str, body: str, buttons: list[dict]) -> dict:
    """
    Envía un mensaje con botones interactivos.
    buttons = [{"id": "btn_id", "title": "Texto del botón"}, ...]
    """
    url = f"{WHATSAPP_API_URL}/{settings.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                    for b in buttons
                ]
            },
        },
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


def get_greeting() -> str:
    """Devuelve el saludo apropiado según la hora del día en la zona horaria configurada."""
    now = datetime.now(settings.tz)
    hour = now.hour
    if 5 <= hour < 12:
        return "buenos días"
    elif 12 <= hour < 19:
        return "buenas tardes"
    else:
        return "buenas noches"


def build_auto_greeting(customer_name: str | None = None) -> str:
    """
    Construye el mensaje de bienvenida automático.
    El mensaje exacto será configurado por Karla — este es el placeholder inicial.
    """
    greeting = get_greeting()
    name_part = f", {customer_name}" if customer_name else ""

    # ─── MENSAJE DE BIENVENIDA (editar con el texto que proporcione Karla) ────
    message = (
        f"¡Hola{name_part}! {greeting.capitalize()} 😊\n\n"
        "Bienvenido/a al consultorio de psicología. Soy el asistente virtual y "
        "con gusto te ayudaré.\n\n"
        "¿En qué puedo orientarte hoy? ¿Buscas información sobre las terapias, "
        "costos, disponibilidad o te gustaría agendar una cita? 🌿"
    )
    # ─────────────────────────────────────────────────────────────────────────
    return message


def build_karla_notification(customer_phone: str, customer_name: str | None, customer_message: str) -> str:
    """Construye la notificación que se envía a Karla cuando llega un nuevo cliente."""
    name_display = customer_name or customer_phone
    return (
        f"🔔 *Nuevo cliente en WhatsApp*\n\n"
        f"📱 Número: +{customer_phone}\n"
        f"👤 Nombre: {name_display}\n\n"
        f"💬 Su mensaje:\n_{customer_message}_\n\n"
        f"¿Cómo deseas atenderlo?"
    )


KARLA_DECISION_BUTTONS = [
    {"id": "decision_yo", "title": "Lo atiendo yo"},
    {"id": "decision_agente", "title": "Que lo atienda Titox"},
]
