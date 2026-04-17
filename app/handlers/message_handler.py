"""
Manejador principal del flujo de mensajes de WhatsApp.
Orquesta: saludo automático → notificación a Karla → decisión → agente o Karla → cita.
"""
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.database.db import Conversation, Message, AppointmentData, ConversationStatus
from app.models.conversation import IncomingMessage
from app.services import whatsapp, ai_agent, calendar
from app.config import settings

logger = logging.getLogger(__name__)


async def handle_incoming_message(msg: IncomingMessage, db: AsyncSession) -> None:
    """
    Punto de entrada principal para cada mensaje entrante del cliente.
    """
    phone = msg.phone_number

    # 1. Buscar conversación activa para este número
    result = await db.execute(
        select(Conversation)
        .where(Conversation.phone_number == phone)
        .where(Conversation.status.not_in([ConversationStatus.CLOSED, ConversationStatus.APPOINTMENT_SCHEDULED]))
        .order_by(Conversation.created_at.desc())
    )
    conv = result.scalar_one_or_none()

    if conv is None:
        # ── PRIMERA VEZ: nuevo cliente ──────────────────────────────────────
        await _handle_new_customer(msg, db)
    elif conv.status == ConversationStatus.WAITING_KARLA:
        # ── Karla aún no ha decidido quién atiende ─────────────────────────
        await _save_message(db, conv.id, phone, "user", msg.text)
        logger.info(f"Mensaje de {phone} mientras Karla decide: '{msg.text}'")
        # Re-notificar a Karla con el nuevo mensaje
        notification = f"⏰ El cliente volvió a escribir mientras esperabas decidir:\n\n_{msg.text}_"
        await whatsapp.send_text_message(settings.karla_phone_number, notification)

    elif conv.status == ConversationStatus.KARLA_HANDLING:
        # ── Karla está atendiendo directamente (solo registrar) ─────────────
        await _save_message(db, conv.id, phone, "user", msg.text)
        logger.info(f"Mensaje en conv manejada por Karla: {phone}")

    elif conv.status == ConversationStatus.AGENT_HANDLING:
        # ── Ast-titox atiende ────────────────────────────────────────────────
        await _handle_agent_response(msg, conv, db)

    elif conv.status == ConversationStatus.APPOINTMENT_PENDING:
        # ── Se acordó cita, procesar agendado ──────────────────────────────
        await _handle_appointment_pending(msg, conv, db)


async def _handle_new_customer(msg: IncomingMessage, db: AsyncSession) -> None:
    """Saluda al cliente nuevo y notifica a Karla."""
    phone = msg.phone_number

    # Crear conversación en BD
    conv = Conversation(
        phone_number=phone,
        customer_name=msg.name,
        status=ConversationStatus.NEW,
    )
    db.add(conv)
    await db.flush()  # Para obtener el ID

    # Guardar mensaje del cliente
    await _save_message(db, conv.id, phone, "user", msg.text)

    # Enviar saludo automático al cliente
    greeting = whatsapp.build_auto_greeting(msg.name)
    await whatsapp.send_text_message(phone, greeting)
    await _save_message(db, conv.id, phone, "assistant", greeting)

    # Actualizar estado
    conv.status = ConversationStatus.WAITING_KARLA
    await db.commit()

    # Notificar a Karla con botones de decisión
    notification = whatsapp.build_karla_notification(phone, msg.name, msg.text)
    await whatsapp.send_interactive_buttons(
        to=settings.karla_phone_number,
        body=notification,
        buttons=whatsapp.KARLA_DECISION_BUTTONS,
    )
    logger.info(f"Nuevo cliente {phone}, Karla notificada.")


async def _handle_agent_response(msg: IncomingMessage, conv: Conversation, db: AsyncSession) -> None:
    """Ast-titox procesa el mensaje y responde al cliente."""
    phone = msg.phone_number

    # Guardar mensaje del cliente
    await _save_message(db, conv.id, phone, "user", msg.text)

    # Cargar historial para el modelo
    history = await _load_history(db, conv.id)

    # Generar respuesta con Ast-titox
    response_text, cita_lista = await ai_agent.ast_titox.respond(history, msg.text)

    # Enviar respuesta al cliente
    await whatsapp.send_text_message(phone, response_text)
    await _save_message(db, conv.id, phone, "assistant", response_text)

    # Si se completó la recopilación de datos de cita
    if cita_lista:
        conv.status = ConversationStatus.APPOINTMENT_PENDING
        await db.commit()
        logger.info(f"Datos de cita completos para {phone}, procediendo a agendar.")
        await _schedule_appointment_from_history(conv, db)
    else:
        conv.updated_at = datetime.utcnow()
        await db.commit()


async def _handle_appointment_pending(msg: IncomingMessage, conv: Conversation, db: AsyncSession) -> None:
    """Maneja mensajes cuando ya se acordó la cita pero no se ha agendado."""
    await _save_message(db, conv.id, conv.phone_number, "user", msg.text)
    # Continuar con el agente para confirmar la cita
    history = await _load_history(db, conv.id)
    response_text, _ = await ai_agent.ast_titox.respond(history, msg.text)
    await whatsapp.send_text_message(conv.phone_number, response_text)
    await _save_message(db, conv.id, conv.phone_number, "assistant", response_text)
    await db.commit()


async def _schedule_appointment_from_history(conv: Conversation, db: AsyncSession) -> None:
    """Extrae datos de la cita del historial y la agenda en Google Calendar."""
    history = await _load_history(db, conv.id)
    appointment_data = await ai_agent.ast_titox.extract_appointment_data(history)

    if not appointment_data or not appointment_data.get("appointment_date"):
        logger.warning(f"No se pudieron extraer datos de cita para {conv.phone_number}")
        return

    try:
        appt_date = datetime.strptime(appointment_data["appointment_date"], "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        logger.error(f"Fecha de cita inválida: {appointment_data.get('appointment_date')}")
        return

    event_id, event_link = await calendar.create_appointment(
        customer_name=appointment_data.get("customer_name") or conv.customer_name or conv.phone_number,
        appointment_date=appt_date,
        appointment_type=appointment_data.get("appointment_type", "Terapia psicológica"),
        modality=appointment_data.get("modality", "presencial"),
        phone_number=conv.phone_number,
        notes=appointment_data.get("notes", ""),
    )

    if event_id:
        # Guardar en BD
        appt = AppointmentData(
            conversation_id=conv.id,
            phone_number=conv.phone_number,
            customer_name=appointment_data.get("customer_name"),
            appointment_date=appt_date,
            appointment_type=appointment_data.get("appointment_type"),
            notes=appointment_data.get("notes"),
            calendar_event_id=event_id,
            scheduled=True,
        )
        db.add(appt)
        conv.status = ConversationStatus.APPOINTMENT_SCHEDULED
        await db.commit()

        # Confirmar al cliente
        confirmation = (
            f"✅ ¡Listo! Tu cita ha quedado agendada:\n\n"
            f"📅 Fecha: {appt_date.strftime('%A %d de %B, %Y')}\n"
            f"⏰ Hora: {appt_date.strftime('%I:%M %p')}\n"
            f"🎯 Servicio: {appointment_data.get('appointment_type', 'Terapia')}\n\n"
            f"Recibirás un recordatorio. Si necesitas cambiar o cancelar, "
            f"escríbenos con al menos 24 horas de anticipación. 🙏"
        )
        await whatsapp.send_text_message(conv.phone_number, confirmation)

        # Notificar a Karla sobre la cita agendada
        karla_notif = (
            f"📆 *Cita agendada automáticamente*\n\n"
            f"👤 Cliente: {appointment_data.get('customer_name') or conv.phone_number}\n"
            f"📅 Fecha: {appt_date.strftime('%d/%m/%Y %H:%M')}\n"
            f"🎯 Tipo: {appointment_data.get('appointment_type')}\n"
            f"💻 Modalidad: {appointment_data.get('modality')}\n"
            f"🔗 Ver en Calendar: {event_link}"
        )
        await whatsapp.send_text_message(settings.karla_phone_number, karla_notif)
        logger.info(f"Cita agendada exitosamente para {conv.phone_number}: {event_id}")


async def _save_message(db: AsyncSession, conv_id: int, phone: str, role: str, content: str) -> None:
    """Guarda un mensaje en la base de datos."""
    msg = Message(conversation_id=conv_id, phone_number=phone, role=role, content=content)
    db.add(msg)
    await db.flush()


async def _load_history(db: AsyncSession, conv_id: int) -> list[dict]:
    """Carga el historial de mensajes en formato para Ollama."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.timestamp.asc())
    )
    messages = result.scalars().all()

    history = []
    for msg in messages:
        role = "user" if msg.role == "user" else "assistant"
        history.append({"role": role, "content": msg.content})
    return history
