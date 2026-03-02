from sqlalchemy.orm import Session
import logging
import hashlib
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import PasswordManager

logger = logging.getLogger(__name__)

def create_user_service(user: UserCreate, db: Session):
    try:
        logger.info(f"Creando usuario: {user.email}")

        # Convertir contraseña a bytes y hacer pre-hash con SHA256
        password_bytes = user.password.encode('utf-8')
        password_hash_input = hashlib.sha256(password_bytes).hexdigest()  # 64 chars hex
        
        # Ahora pasar a bcrypt
        hashed_password = PasswordManager.hash(password_hash_input)
        logger.info("Password hashed successfully")

        new_user = User(
            nombre=user.name,
            email=user.email,
            password_hash=hashed_password
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info(f"Usuario creado exitosamente: {new_user.id}")
        return new_user

    except Exception as e:
        logger.error(f"Error creando usuario: {str(e)}", exc_info=True)
        raise e