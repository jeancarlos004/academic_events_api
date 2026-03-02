from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(String(20), default="usuario", nullable=False)  # "admin" | "usuario"

    inscripciones = relationship("Registration", back_populates="usuario", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} email={self.email} rol={self.rol}>"
