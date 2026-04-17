"""
database.py
SQLAlchemy engine, session factory y Base declarativa.

Entornos:
  - Local (desarrollo): SQLite — sin configuración adicional
  - Producción (Railway): PostgreSQL — se lee de DATABASE_URL automáticamente

Railway inyecta DATABASE_URL con el prefijo postgresql://, pero
SQLAlchemy 2.x requiere postgresql+psycopg2://. La conversión se hace aquí.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ── URL de conexión ────────────────────────────────────────────
_DB_PATH     = Path(__file__).parent / "karla_psicologia.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_DB_PATH}")

# Railway usa postgresql://, SQLAlchemy 2.x necesita postgresql+psycopg2://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# ── Engine ─────────────────────────────────────────────────────
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — cede una sesión de DB y garantiza su cierre."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
