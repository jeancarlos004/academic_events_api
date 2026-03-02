from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.services.report_service import ReportService
from app.schemas.report import EventReport

router = APIRouter(prefix="/reports", tags=["Reportes"])


@router.get("/events", response_model=list[EventReport])
def report_all_events(
    db: Session = Depends(get_db),
    _=Depends(require_admin)
):
    """Reporte general de todos los eventos con métricas de asistencia."""
    return ReportService.all_events(db)


@router.get("/events/{id}", response_model=EventReport)
def report_event(
    id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin)
):
    """Reporte detallado de un evento específico."""
    return ReportService.single_event(db, id)
