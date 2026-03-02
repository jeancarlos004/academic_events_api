from pydantic import BaseModel


class EventReport(BaseModel):
    evento_id: int
    titulo: str
    tipo: str
    fecha: str
    cupos: int
    inscritos: int
    asistentes: int
    cupos_disponibles: int
    porcentaje_asistencia: float
