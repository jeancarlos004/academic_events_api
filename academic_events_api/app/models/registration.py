from sqlalchemy import Column, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Registration(Base):
    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    evento_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    fecha_inscripcion = Column(DateTime, default=datetime.utcnow, nullable=False)
    asistencia = Column(Boolean, default=False, nullable=False)

    usuario = relationship("User", back_populates="inscripciones")
    evento = relationship("Event", back_populates="inscripciones")

    def __repr__(self):
        return f"<Registration id={self.id} usuario={self.usuario_id} evento={self.evento_id}>"
