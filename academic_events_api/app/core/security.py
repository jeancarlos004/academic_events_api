import uuid
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db


class PasswordManager:
    _context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @classmethod
    def hash(cls, plain_password: str) -> str:
        return cls._context.hash(plain_password)

    @classmethod
    def verify(cls, plain_password: str, hashed_password: str) -> bool:
        return cls._context.verify(plain_password, hashed_password)


class TokenBlacklist:
    _revoked: set = set()

    @classmethod
    def revoke(cls, jti: str) -> None:
        cls._revoked.add(jti)

    @classmethod
    def is_revoked(cls, jti: str) -> bool:
        return jti in cls._revoked


class JWTManager:
    _oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

    @classmethod
    def create_access_token(cls, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        payload = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
        payload.update({"exp": expire, "iat": datetime.utcnow(), "type": "access", "jti": str(uuid.uuid4())})
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @classmethod
    def create_refresh_token(cls, data: dict) -> str:
        payload = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        payload.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh", "jti": str(uuid.uuid4())})
        return jwt.encode(payload, settings.REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)

    @classmethod
    def decode(cls, token: str, secret: str, expected_type: str) -> dict:
        try:
            payload = jwt.decode(token, secret, algorithms=[settings.ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado", headers={"WWW-Authenticate": "Bearer"})
        if payload.get("type") != expected_type:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Se esperaba un token de tipo '{expected_type}'")
        jti = payload.get("jti")
        if not jti or TokenBlacklist.is_revoked(jti):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="El token ha sido revocado")
        return payload

    @classmethod
    def decode_access(cls, token: str) -> dict:
        return cls.decode(token, settings.SECRET_KEY, expected_type="access")

    @classmethod
    def decode_refresh(cls, token: str) -> dict:
        return cls.decode(token, settings.REFRESH_SECRET_KEY, expected_type="refresh")


oauth2_scheme = JWTManager._oauth2_scheme


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    from app.models.user import User
    payload = JWTManager.decode_access(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin identidad")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return user


def get_token_payload(token: str = Depends(oauth2_scheme)) -> dict:
    return JWTManager.decode_access(token)


def require_admin(current_user=Depends(get_current_user)):
    if current_user.rol != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso restringido a administradores")
    return current_user
