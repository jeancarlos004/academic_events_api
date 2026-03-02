from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.schemas.event import EventOut


class RegistrationOut(BaseModel):
    id: int
    evento_id: int
    usuario_id: int
    fecha_inscripcion: datetime
    asistencia: bool

    model_config = {"from_attributes": True}


class RegistrationWithEvent(BaseModel):
    id: int
    evento_id: int
    fecha_inscripcion: datetime
    asistencia: bool
    evento: Optional[EventOut] = None

    model_config = {"from_attributes": True}


class AttendanceUpdate(BaseModel):
    asistencia: bool
