from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.services.registration_service import RegistrationService
from app.schemas.registration import RegistrationWithEvent, AttendanceUpdate, RegistrationOut

router = APIRouter(prefix="/registrations", tags=["Inscripciones"])


@router.get("/me", response_model=list[RegistrationWithEvent])
def get_my_registrations(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Lista todas las inscripciones del usuario autenticado."""
    return RegistrationService.get_my_registrations(db, current_user.id)


@router.patch("/{id}/attendance", response_model=RegistrationOut)
def mark_attendance(
    id: int,
    body: AttendanceUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin)
):
    """Marca o desmarca asistencia de una inscripción. Solo administradores."""
    return RegistrationService.mark_attendance(db, id, body.asistencia)
