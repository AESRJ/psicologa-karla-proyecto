"""
Punto de entrada del servidor FastAPI.
Gestiona el webhook de WhatsApp Business Cloud API.
"""
import logging
import json
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database.db import init_db, get_db, Conversation, ConversationStatus
from app.models.conversation import IncomingMessage
from app.handlers.message_handler import handle_incoming_message
from app.handlers.karla_handler import handle_karla_decision, handle_karla_manual_schedule_command

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("✅ Base de datos inicializada")
    logger.info("🤖 Ast-titox listo para atender")
    yield
    logger.info("Servidor detenido")


app = FastAPI(
    title="Agente-Mama — Consultorio de Psicología",
    description="Agente IA para gestión de WhatsApp y citas de Karla",
    version="1.0.0",
    lifespan=lifespan,
)


# ──────────────────────────────────────────────────────────────────────────────
# WEBHOOK DE WHATSAPP
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/webhook")
async def verify_webhook(request: Request):
    """
    Verificación del webhook por Meta.
    Meta envía un GET con hub.verify_token para confirmar que el servidor es válido.
    """
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("✅ Webhook verificado por Meta")
        return PlainTextResponse(content=challenge)

    raise HTTPException(status_code=403, detail="Token de verificación inválido")


@app.post("/webhook")
async def receive_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Recibe todos los eventos de WhatsApp Business Cloud API.
    Procesa mensajes de texto y respuestas de botones interactivos.
    """
    try:
        body = await request.json()
        logger.debug(f"Webhook recibido: {json.dumps(body, indent=2)}")
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    # Navegar la estructura del payload de Meta
    entry = body.get("entry", [{}])[0]
    changes = entry.get("changes", [{}])[0]
    value = changes.get("value", {})

    # Ignorar notificaciones de estado (delivered, read, etc.)
    if "statuses" in value:
        return {"status": "ok"}

    messages = value.get("messages", [])
    contacts = value.get("contacts", [])

    for message in messages:
        phone_number = message.get("from", "")
        message_id = message.get("id", "")
        timestamp = datetime.fromtimestamp(int(message.get("timestamp", 0)))
        msg_type = message.get("type", "")

        # Obtener nombre del contacto
        customer_name = None
        if contacts:
            customer_name = contacts[0].get("profile", {}).get("name")

        # ── Mensaje de texto normal ──────────────────────────────────────────
        if msg_type == "text":
            text = message.get("text", {}).get("body", "")

            if not text:
                continue

            # ¿Es Karla enviando un comando manual?
            if phone_number == settings.karla_phone_number:
                if text.upper().startswith("AGENDAR "):
                    await handle_karla_manual_schedule_command(text, db)
                    continue
                # Otros mensajes de Karla se ignoran (ella habla directamente con clientes)
                continue

            # Mensaje de cliente
            incoming = IncomingMessage(
                phone_number=phone_number,
                name=customer_name,
                message_id=message_id,
                text=text,
                timestamp=timestamp,
            )
            await handle_incoming_message(incoming, db)

        # ── Respuesta a botón interactivo (decisión de Karla) ────────────────
        elif msg_type == "interactive":
            if phone_number != settings.karla_phone_number:
                continue  # Solo Karla usa botones

            interactive = message.get("interactive", {})
            button_reply = interactive.get("button_reply", {})
            button_id = button_reply.get("id", "")

            if button_id in ("decision_yo", "decision_agente"):
                # El contexto del botón tiene el número del cliente
                # Lo guardamos en el ID del botón o lo derivamos del contexto
                # NOTA: Meta no incluye el customer_phone directamente en el button reply.
                # La solución práctica: el ID del botón incluye el número del cliente.
                # En build_karla_notification usamos botones con ID estático, por lo que
                # necesitamos rastrear a quién pertenece la última notificación enviada.
                await _handle_karla_button(button_id, db)

        # ── Otros tipos (imagen, audio, etc.) ────────────────────────────────
        else:
            logger.info(f"Tipo de mensaje no manejado: {msg_type} de {phone_number}")

    return {"status": "ok"}


async def _handle_karla_button(button_id: str, db: AsyncSession) -> None:
    """
    Maneja el botón que presionó Karla.
    Busca la conversación más reciente en estado WAITING_KARLA.
    """
    result = await db.execute(
        select(Conversation)
        .where(Conversation.status == ConversationStatus.WAITING_KARLA)
        .order_by(Conversation.updated_at.desc())
    )
    conv = result.scalar_one_or_none()

    if not conv:
        from app.services.whatsapp import send_text_message
        await send_text_message(
            settings.karla_phone_number,
            "⚠️ No hay conversaciones esperando tu decisión en este momento."
        )
        return

    await handle_karla_decision(button_id, conv.phone_number, db)


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINTS DE ADMINISTRACIÓN
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {"status": "ok", "agent": "Ast-titox", "version": "1.0.0"}


@app.get("/conversations")
async def list_conversations(db: AsyncSession = Depends(get_db)):
    """Lista todas las conversaciones activas (para depuración)."""
    result = await db.execute(
        select(Conversation).order_by(Conversation.updated_at.desc())
    )
    convs = result.scalars().all()
    return [
        {
            "id": c.id,
            "phone": c.phone_number,
            "name": c.customer_name,
            "status": c.status,
            "handler": c.handler,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in convs
    ]
