from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.registration import Registration
from app.models.event import Event
from app.models.user import User
from app.exceptions.app_exceptions import NotFoundException, ConflictException, BadRequestException


class RegistrationService:

    @staticmethod
    def register(db: Session, event_id: int, user: User) -> Registration:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise NotFoundException("Evento")

        if event.estado != "activo":
            raise BadRequestException("El evento no está disponible para inscripciones")

        # Doble inscripción
        existing = db.query(Registration).filter(
            Registration.evento_id == event_id,
            Registration.usuario_id == user.id
        ).first()
        if existing:
            raise ConflictException("Ya estás inscrito en este evento")

        # Cupos
        inscritos = db.query(func.count(Registration.id)).filter(
            Registration.evento_id == event_id
        ).scalar()
        if inscritos >= event.cupos:
            raise ConflictException("No hay cupos disponibles para este evento")

        reg = Registration(usuario_id=user.id, evento_id=event_id)
        db.add(reg)
        db.commit()
        db.refresh(reg)
        return reg

    @staticmethod
    def cancel(db: Session, event_id: int, user: User) -> None:
        reg = db.query(Registration).filter(
            Registration.evento_id == event_id,
            Registration.usuario_id == user.id
        ).first()
        if not reg:
            raise NotFoundException("Inscripción")
        db.delete(reg)
        db.commit()

    @staticmethod
    def get_my_registrations(db: Session, user_id: int) -> list[Registration]:
        return db.query(Registration).filter(Registration.usuario_id == user_id).all()

    @staticmethod
    def get_event_registrations(db: Session, event_id: int) -> list[Registration]:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise NotFoundException("Evento")
        return db.query(Registration).filter(Registration.evento_id == event_id).all()

    @staticmethod
    def mark_attendance(db: Session, registration_id: int, asistencia: bool) -> Registration:
        reg = db.query(Registration).filter(Registration.id == registration_id).first()
        if not reg:
            raise NotFoundException("Inscripción")
        reg.asistencia = asistencia
        db.commit()
        db.refresh(reg)
        return reg
