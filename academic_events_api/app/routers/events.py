from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.services.event_service import EventService
from app.services.registration_service import RegistrationService
from app.schemas.event import EventCreate, EventUpdate, EventOut, PaginatedEvents
from app.schemas.registration import RegistrationOut, RegistrationWithEvent, RegistrationAdminOut

router = APIRouter(prefix="/events", tags=["Eventos"])


@router.get("", response_model=PaginatedEvents)
def list_events(
    tipo: Optional[str] = Query(None, description="Filtrar por tipo"),
    fecha: Optional[date] = Query(None, description="Filtrar por fecha YYYY-MM-DD"),
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db)
):
    """Lista eventos con filtros opcionales y paginación."""
    return EventService.get_all(db, tipo=tipo, fecha=fecha, estado=estado, page=page, page_size=page_size)


@router.get("/{id}", response_model=EventOut)
def get_event(id: int, db: Session = Depends(get_db)):
    """Obtiene un evento por ID."""
    return EventService.get_by_id(db, id)


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(
    body: EventCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin)
):
    """Crea un nuevo evento. Solo administradores."""
    return EventService.create(db, body)


@router.put("/{id}", response_model=EventOut)
def update_event(
    id: int,
    body: EventUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin)
):
    """Actualiza un evento. Solo administradores."""
    return EventService.update(db, id, body)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin)
):
    """Elimina un evento y sus inscripciones. Solo administradores."""
    EventService.delete(db, id)


# ── Inscripciones anidadas en /events ────────────────────────────────────────

@router.post("/{id}/register", status_code=status.HTTP_201_CREATED)
def register_to_event(
    id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Inscribe al usuario autenticado en un evento."""
    RegistrationService.register(db, id, current_user)
    return {"message": "Inscripción realizada correctamente"}


@router.delete("/{id}/register", status_code=status.HTTP_200_OK)
def cancel_registration(
    id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Cancela la inscripción del usuario autenticado en un evento."""
    RegistrationService.cancel(db, id, current_user)
    return {"message": "Inscripción cancelada correctamente"}


@router.get("/{id}/registrations", response_model=list[RegistrationAdminOut])
def get_event_registrations(
    id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin)
):
    """Lista todos los inscritos en un evento. Solo administradores."""
    return RegistrationService.get_event_registrations(db, id)
