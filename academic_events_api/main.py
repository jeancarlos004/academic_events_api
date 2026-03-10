import logging
import time
from sqlalchemy import inspect, text
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import Base, engine
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.routers import auth, users, events, registrations, reports, chat

# Importar modelos para que SQLAlchemy registre las tablas antes de create_all
from app.models.chat_message import ChatMessage  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear tablas si no existen (solo desarrollo)
Base.metadata.create_all(bind=engine)

try:
    insp = inspect(engine)
    cols = {c.get("name") for c in insp.get_columns("chat_messages")}
    if "conversation_id" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE chat_messages ADD COLUMN conversation_id VARCHAR(36)"))
except Exception:
    logger.exception("No se pudo aplicar migración ligera para chat_messages.conversation_id")

app = FastAPI(
    title="API de Gestión de Eventos Académicos",
    description=(
        "REST API para gestionar eventos institucionales, inscripciones, "
        "control de asistencia y reportes. Autenticación JWT con refresh tokens."
    ),
    version="1.0.0",
    contact={"name": "Soporte Institucional"},
    license_info={"name": "MIT"},
)

# ────────────────────────────────
# CORS
# ────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambiar en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ────────────────────────────────
# MANEJADORES DE ERRORES GLOBALES
# ────────────────────────────────
app.add_exception_handler(
    RequestValidationError,
    ErrorHandlerMiddleware.validation_exception_handler
)

app.add_exception_handler(
    HTTPException,
    ErrorHandlerMiddleware.http_exception_handler
)

app.add_exception_handler(
    SQLAlchemyError,
    ErrorHandlerMiddleware.integrity_error_handler
)

app.add_exception_handler(
    Exception,
    ErrorHandlerMiddleware.generic_exception_handler
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        dt_ms = int((time.perf_counter() - t0) * 1000)
        logger.info("%s %s -> %s (%sms)", request.method, request.url.path, getattr(locals().get("response"), "status_code", "-"), dt_ms)
    return response

# ────────────────────────────────
# ROUTERS
# ────────────────────────────────
PREFIX = "/api/v1"
app.include_router(auth.router, prefix=PREFIX)
app.include_router(users.router, prefix=PREFIX)
app.include_router(events.router, prefix=PREFIX)
app.include_router(registrations.router, prefix=PREFIX)
app.include_router(reports.router, prefix=PREFIX)
app.include_router(chat.router, prefix=PREFIX)


@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "app": "API de Eventos Académicos",
        "version": "1.0.0",
        "docs": "/docs"
    }