from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.event import Event
from app.models.registration import Registration
from app.exceptions.app_exceptions import NotFoundException


class ReportService:

    @staticmethod
    def _build_report(db: Session, event: Event) -> dict:
        inscritos = db.query(func.count(Registration.id)).filter(
            Registration.evento_id == event.id
        ).scalar() or 0

        asistentes = db.query(func.count(Registration.id)).filter(
            Registration.evento_id == event.id,
            Registration.asistencia == True
        ).scalar() or 0

        porcentaje = round((asistentes / inscritos * 100), 2) if inscritos > 0 else 0.0

        return {
            "evento_id": event.id,
            "titulo": event.titulo,
            "tipo": event.tipo,
            "fecha": str(event.fecha),
            "cupos": event.cupos,
            "inscritos": inscritos,
            "asistentes": asistentes,
            "cupos_disponibles": event.cupos - inscritos,
            "porcentaje_asistencia": porcentaje,
        }

    @staticmethod
    def all_events(db: Session) -> list[dict]:
        events = db.query(Event).all()
        return [ReportService._build_report(db, e) for e in events]

    @staticmethod
    def single_event(db: Session, event_id: int) -> dict:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise NotFoundException("Evento")
        return ReportService._build_report(db, event)
