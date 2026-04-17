"""
main.py
FastAPI application — Karla Zermeño Psicóloga.

Run locally:
    cd web/
    uvicorn api.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.database import Base, engine
from api.models import db_models  # noqa: F401 — ensures models are registered
from api.routes import appointments, contact


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup if they don't exist
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Karla Zermeño — Psicóloga API",
    version="0.2.0",
    description="Backend para agendamiento de citas y contacto.",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────
# Adjust allowed origins before deploying to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────
app.include_router(appointments.router, prefix="/api")
app.include_router(contact.router,      prefix="/api")

# ── Serve static frontend ─────────────────────────────────────
# El frontend se sirve desde http://localhost:8000/
app.mount("/", StaticFiles(directory=".", html=True), name="static")
