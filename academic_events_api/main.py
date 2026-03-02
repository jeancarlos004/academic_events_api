import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import Base, engine
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.routers import auth, users, events, registrations, reports

logging.basicConfig(level=logging.INFO)

# Crear tablas si no existen (solo desarrollo)
Base.metadata.create_all(bind=engine)

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
    SQLAlchemyError,
    ErrorHandlerMiddleware.integrity_error_handler
)

app.add_exception_handler(
    Exception,
    ErrorHandlerMiddleware.generic_exception_handler
)

# ────────────────────────────────
# ROUTERS
# ────────────────────────────────
PREFIX = "/api/v1"
app.include_router(auth.router, prefix=PREFIX)
app.include_router(users.router, prefix=PREFIX)
app.include_router(events.router, prefix=PREFIX)
app.include_router(registrations.router, prefix=PREFIX)
app.include_router(reports.router, prefix=PREFIX)


@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "app": "API de Eventos Académicos",
        "version": "1.0.0",
        "docs": "/docs"
    }