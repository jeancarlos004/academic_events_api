from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.orm import relationship
from app.core.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(String(1000), nullable=True)
    fecha = Column(Date, nullable=False)
    hora = Column(String(10), nullable=False)
    lugar = Column(String(200), nullable=False)
    cupos = Column(Integer, nullable=False)
    tipo = Column(String(50), nullable=False)       # taller | conferencia | seminario | otro
    estado = Column(String(20), default="activo", nullable=False)  # activo | cancelado | finalizado

    inscripciones = relationship("Registration", back_populates="evento", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Event id={self.id} titulo={self.titulo} estado={self.estado}>"
