from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date


class EventCreate(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    fecha: date
    hora: str
    lugar: str
    cupos: int
    tipo: str

    @field_validator("cupos")
    @classmethod
    def cupos_positivos(cls, v):
        if v <= 0:
            raise ValueError("Los cupos deben ser mayor a 0")
        return v

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, v):
        allowed = {"taller", "conferencia", "seminario", "otro"}
        if v.lower() not in allowed:
            raise ValueError(f"Tipo inválido. Opciones: {', '.join(allowed)}")
        return v.lower()

    @field_validator("hora")
    @classmethod
    def hora_valida(cls, v):
        import re
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("Formato de hora inválido. Use HH:MM")
        return v


class EventUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    fecha: Optional[date] = None
    hora: Optional[str] = None
    lugar: Optional[str] = None
    cupos: Optional[int] = None
    tipo: Optional[str] = None
    estado: Optional[str] = None

    @field_validator("estado")
    @classmethod
    def estado_valido(cls, v):
        if v is not None:
            allowed = {"activo", "cancelado", "finalizado"}
            if v.lower() not in allowed:
                raise ValueError(f"Estado inválido. Opciones: {', '.join(allowed)}")
            return v.lower()
        return v

    @field_validator("cupos")
    @classmethod
    def cupos_positivos(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Los cupos deben ser mayor a 0")
        return v


class EventOut(BaseModel):
    id: int
    titulo: str
    descripcion: Optional[str]
    fecha: date
    hora: str
    lugar: str
    cupos: int
    inscritos: int = 0
    cupos_disponibles: int = 0
    tipo: str
    estado: str

    model_config = {"from_attributes": True}


class PaginatedEvents(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[EventOut]
