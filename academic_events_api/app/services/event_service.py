from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import date

from app.models.event import Event
from app.models.registration import Registration
from app.schemas.event import EventCreate, EventUpdate
from app.exceptions.app_exceptions import NotFoundException, BadRequestException


class EventService:

    @staticmethod
    def _get_event_orm_by_id(db: Session, event_id: int) -> Event:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise NotFoundException("Evento")
        return event

    @staticmethod
    def _event_to_out_dict(db: Session, event: Event) -> dict:
        inscritos = db.query(func.count(Registration.id)).filter(Registration.evento_id == event.id).scalar() or 0
        return {
            "id": event.id,
            "titulo": event.titulo,
            "descripcion": event.descripcion,
            "fecha": event.fecha,
            "hora": event.hora,
            "lugar": event.lugar,
            "cupos": event.cupos,
            "inscritos": inscritos,
            "cupos_disponibles": max(0, event.cupos - inscritos),
            "tipo": event.tipo,
            "estado": event.estado,
        }

    @staticmethod
    def get_all(
        db: Session,
        tipo: Optional[str] = None,
        fecha: Optional[date] = None,
        estado: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        base_query = db.query(Event)
        if tipo:
            base_query = base_query.filter(Event.tipo == tipo)
        if fecha:
            base_query = base_query.filter(Event.fecha == fecha)
        if estado:
            base_query = base_query.filter(Event.estado == estado)

        total = base_query.with_entities(func.count(Event.id)).scalar() or 0

        inscritos_count = func.count(Registration.id)
        query = (
            db.query(Event, inscritos_count.label("inscritos"))
            .outerjoin(Registration, Registration.evento_id == Event.id)
        )
        if tipo:
            query = query.filter(Event.tipo == tipo)
        if fecha:
            query = query.filter(Event.fecha == fecha)
        if estado:
            query = query.filter(Event.estado == estado)

        results = (
            query.group_by(Event.id)
            .order_by(Event.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        mapped = []
        for event, inscritos in results:
            inscritos = int(inscritos or 0)
            mapped.append({
                "id": event.id,
                "titulo": event.titulo,
                "descripcion": event.descripcion,
                "fecha": event.fecha,
                "hora": event.hora,
                "lugar": event.lugar,
                "cupos": event.cupos,
                "inscritos": inscritos,
                "cupos_disponibles": max(0, event.cupos - inscritos),
                "tipo": event.tipo,
                "estado": event.estado,
            })

        return {"total": total, "page": page, "page_size": page_size, "results": mapped}

    @staticmethod
    def get_by_id(db: Session, event_id: int) -> Event:
        event = EventService._get_event_orm_by_id(db, event_id)
        return EventService._event_to_out_dict(db, event)

    @staticmethod
    def create(db: Session, data: EventCreate) -> Event:
        event = Event(**data.model_dump())
        db.add(event)
        db.commit()
        db.refresh(event)
        return EventService._event_to_out_dict(db, event)

    @staticmethod
    def update(db: Session, event_id: int, data: EventUpdate) -> Event:
        event = EventService._get_event_orm_by_id(db, event_id)
        updates = data.model_dump(exclude_unset=True)

        # Validar que no se reduzcan cupos por debajo de inscritos actuales
        if "cupos" in updates:
            inscritos = db.query(Registration).filter(Registration.evento_id == event_id).count()
            if updates["cupos"] < inscritos:
                raise BadRequestException("Datos inválidos")(
                    f"No se pueden reducir los cupos a {updates['cupos']}. "
                    f"Ya hay {inscritos} inscritos."
                )

        for field, value in updates.items():
            setattr(event, field, value)

        db.commit()
        db.refresh(event)
        return EventService._event_to_out_dict(db, event)

    @staticmethod
    def delete(db: Session, event_id: int) -> None:
        event = EventService._get_event_orm_by_id(db, event_id)
        db.delete(event)
        db.commit()

    @staticmethod
    def cupos_disponibles(db: Session, event_id: int) -> int:
        event = EventService._get_event_orm_by_id(db, event_id)
        inscritos = db.query(func.count(Registration.id)).filter(
            Registration.evento_id == event_id
        ).scalar()
        return event.cupos - inscritos
