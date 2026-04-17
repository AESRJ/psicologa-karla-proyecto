"""
db_models.py
Modelos ORM de SQLAlchemy — definen el esquema de la base de datos.

Notas de compatibilidad PostgreSQL:
  - Los Enum usan native_enum=False para almacenarse como VARCHAR.
    Esto permite agregar nuevos valores sin migraciones ALTER TYPE.
  - La validación de valores permitidos se hace en los schemas Pydantic.
"""

from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Enum, Integer, String, Text, Time

from api.database import Base

# Opciones válidas — deben coincidir con TherapyType en appointment.py
_THERAPY_TYPES = ("individual", "pareja", "familia", "adolescentes", "online")
_STATUSES      = ("pending", "confirmed", "cancelled")


class Appointment(Base):
    __tablename__ = "appointments"

    id               = Column(Integer, primary_key=True, index=True)
    patient_name     = Column(String(120), nullable=False)
    patient_phone    = Column(String(20),  nullable=False)
    patient_email    = Column(String(200), nullable=True)
    therapy_type     = Column(
        Enum(*_THERAPY_TYPES, native_enum=False),
        nullable=False,
    )
    appointment_date = Column(Date,    nullable=False, index=True)
    appointment_time = Column(Time,    nullable=False)
    status           = Column(
        Enum(*_STATUSES, native_enum=False),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    price            = Column(Integer, nullable=False)
    notes            = Column(Text,    nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return (
            f"<Appointment id={self.id} "
            f"{self.appointment_date} {self.appointment_time} "
            f"{self.therapy_type} — {self.patient_name}>"
        )


class BlockedDay(Base):
    """Días que la psicóloga marca como no disponibles."""
    __tablename__ = "blocked_days"

    id         = Column(Integer, primary_key=True, index=True)
    date       = Column(Date,        nullable=False, unique=True, index=True)
    reason     = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<BlockedDay {self.date} — {self.reason}>"
