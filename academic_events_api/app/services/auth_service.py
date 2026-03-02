from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models.user import User
from app.core.security import PasswordManager, JWTManager
from app.schemas.auth import RegisterRequest
from app.core.config import settings


class AuthService:

    @staticmethod
    def register(db: Session, body: RegisterRequest):
        """Crea un nuevo usuario con contraseña hasheada."""
        existing = db.query(User).filter(User.email == body.email).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="El correo ya está registrado"
            )

        hashed_password = PasswordManager.hash(body.password)

        user = User(
            nombre=body.nombre,
            email=body.email,
            password_hash=hashed_password,
            rol="usuario"
        )

        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El correo ya está registrado"
            )
        db.refresh(user)

        return user

    @staticmethod
    def login(db: Session, email: str, password: str):
        """Valida credenciales y retorna tokens."""
        user = db.query(User).filter(User.email == email).first()

        if not user or not PasswordManager.verify(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas"
            )

        access_token = JWTManager.create_access_token({"sub": str(user.id)})
        refresh_token = JWTManager.create_refresh_token({"sub": str(user.id)})

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token
        }