from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import PasswordManager

logger = logging.getLogger(__name__)

def create_user_service(user: UserCreate, db: Session):
    try:
        logger.info(f"Creando usuario: {user.email}")

        existing = db.query(User).filter(User.email == user.email).first()
        if existing:
            raise ValueError("El email ya está registrado")

        hashed_password = PasswordManager.hash(user.password)
        logger.info("Password hashed successfully")

        new_user = User(
            nombre=user.nombre,
            email=user.email,
            password_hash=hashed_password
        )

        db.add(new_user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise ValueError("El email ya está registrado")
        db.refresh(new_user)

        logger.info(f"Usuario creado exitosamente: {new_user.id}")
        return new_user

    except Exception as e:
        db.rollback()
        logger.error(f"Error creando usuario: {str(e)}", exc_info=True)
        raise e