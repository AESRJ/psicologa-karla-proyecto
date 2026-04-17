"""
Manejador de las decisiones e interacciones de Karla con el sistema.
Karla puede: decidir quién atiende, cerrar conversaciones, ver resúmenes.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.database.db import Conversation, ConversationStatus
from app.services import whatsapp
from app.config import settings

logger = logging.getLogger(__name__)


async def handle_karla_decision(
    button_id: str,
    customer_phone: str,
    db: AsyncSession,
) -> None:
    """
    Procesa la decisión de Karla cuando presiona un botón interactivo.
    button_id: "decision_yo" o "decision_agente"
    customer_phone: número del cliente sobre quien se toma la decisión
    """
    result = await db.execute(
        select(Conversation)
        .where(Conversation.phone_number == customer_phone)
        .where(Conversation.status == ConversationStatus.WAITING_KARLA)
        .order_by(Conversation.created_at.desc())
    )
    conv = result.scalar_one_or_none()

    if not conv:
        logger.warning(f"No se encontró conversación esperando decisión para {customer_phone}")
        await whatsapp.send_text_message(
            settings.karla_phone_number,
            f"⚠️ No encontré una conversación activa para el número +{customer_phone}."
        )
        return

    if button_id == "decision_yo":
        conv.status = ConversationStatus.KARLA_HANDLING
        conv.handler = "karla"
        await db.commit()

        await whatsapp.send_text_message(
            settings.karla_phone_number,
            f"✅ Entendido. Atenderás tú directamente a +{customer_phone}.\n"
            f"Cuando termines y se acuerde una cita, escribe:\n"
            f"*AGENDAR {customer_phone}* y te ayudo a registrarla en Calendar. 📅"
        )
        logger.info(f"Karla atiende a {customer_phone}")

    elif button_id == "decision_agente":
        conv.status = ConversationStatus.AGENT_HANDLING
        conv.handler = "ast-titox"
        await db.commit()

        # Notificar al cliente que está siendo atendido
        handoff_msg = (
            "Con gusto te atiendo 😊 Soy Titox, el asistente virtual del consultorio.\n\n"
            "¿Me cuentas qué información necesitas o en qué te puedo ayudar?"
        )
        await whatsapp.send_text_message(customer_phone, handoff_msg)

        await whatsapp.send_text_message(
            settings.karla_phone_number,
            f"🤖 Ast-titox tomará el control de la conversación con +{customer_phone}.\n"
            f"Te notificaré cuando se acuerde o agende una cita."
        )
        logger.info(f"Ast-titox atiende a {customer_phone}")


async def handle_karla_manual_schedule_command(
    raw_message: str,
    db: AsyncSession,
) -> None:
    """
    Procesa el comando AGENDAR que Karla puede enviar cuando ella atendió directamente.
    Formato: AGENDAR <numero_cliente> <fecha> <hora> [tipo_terapia]
    Ejemplo: AGENDAR 5215512345678 2024-12-20 10:00 individual
    """
    parts = raw_message.strip().split()
    if len(parts) < 4:
        await whatsapp.send_text_message(
            settings.karla_phone_number,
            "⚠️ Formato incorrecto. Usa:\n"
            "*AGENDAR <número> <fecha YYYY-MM-DD> <hora HH:MM> [tipo]*\n\n"
            "Ejemplo:\n`AGENDAR 5215512345678 2024-12-20 10:00 individual`"
        )
        return

    from app.services.calendar import create_appointment
    from datetime import datetime

    customer_phone = parts[1]
    date_str = parts[2]
    time_str = parts[3]
    appointment_type = " ".join(parts[4:]) if len(parts) > 4 else "Terapia psicológica"

    try:
        appt_date = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        await whatsapp.send_text_message(
            settings.karla_phone_number,
            "⚠️ Fecha u hora inválida. Formato esperado: YYYY-MM-DD HH:MM"
        )
        return

    # Buscar nombre del cliente
    result = await db.execute(
        select(Conversation)
        .where(Conversation.phone_number == customer_phone)
        .order_by(Conversation.created_at.desc())
    )
    conv = result.scalar_one_or_none()
    customer_name = conv.customer_name if conv else customer_phone

    event_id, event_link = await create_appointment(
        customer_name=customer_name or customer_phone,
        appointment_date=appt_date,
        appointment_type=appointment_type,
        phone_number=customer_phone,
    )

    if event_id:
        if conv:
            conv.status = ConversationStatus.APPOINTMENT_SCHEDULED
            await db.commit()

        await whatsapp.send_text_message(
            settings.karla_phone_number,
            f"✅ Cita agendada en Google Calendar:\n\n"
            f"👤 {customer_name}\n"
            f"📅 {appt_date.strftime('%d/%m/%Y %H:%M')}\n"
            f"🎯 {appointment_type}\n"
            f"🔗 {event_link}"
        )

        # Confirmar también al cliente
        if conv:
            await whatsapp.send_text_message(
                customer_phone,
                f"✅ Tu cita ha sido confirmada:\n\n"
                f"📅 {appt_date.strftime('%A %d de %B, %Y')} a las {appt_date.strftime('%I:%M %p')}\n"
                f"Nos vemos pronto 🌿"
            )
    else:
        await whatsapp.send_text_message(
            settings.karla_phone_number,
            "❌ Hubo un error al crear el evento en Google Calendar. Intenta de nuevo."
        )
