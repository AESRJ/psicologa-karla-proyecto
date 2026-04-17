"""
Base de datos SQLite asíncrona para mantener el estado de conversaciones.
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, DateTime, Text, Enum, Boolean, Integer
from datetime import datetime
import enum


DATABASE_URL = "sqlite+aiosqlite:///./agente_mama.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class ConversationStatus(str, enum.Enum):
    NEW = "new"                         # Primer mensaje recibido, saludo enviado
    WAITING_KARLA = "waiting_karla"     # Notificada Karla, esperando decisión
    KARLA_HANDLING = "karla_handling"   # Karla atiende directamente
    AGENT_HANDLING = "agent_handling"   # Ast-titox atiende
    APPOINTMENT_PENDING = "appointment_pending"  # Se acordó cita, pendiente de agendar
    APPOINTMENT_SCHEDULED = "appointment_scheduled"  # Cita agendada en Calendar
    CLOSED = "closed"                   # Conversación cerrada


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String(20), nullable=False, index=True)
    customer_name = Column(String(100), nullable=True)
    status = Column(Enum(ConversationStatus), default=ConversationStatus.NEW)
    handler = Column(String(20), nullable=True)  # "karla" o "ast-titox"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, nullable=False, index=True)
    phone_number = Column(String(20), nullable=False)
    role = Column(String(10), nullable=False)  # "user" o "assistant"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class AppointmentData(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, nullable=False, unique=True)
    phone_number = Column(String(20), nullable=False)
    customer_name = Column(String(100), nullable=True)
    appointment_date = Column(DateTime, nullable=True)
    appointment_type = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    calendar_event_id = Column(String(200), nullable=True)
    scheduled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
