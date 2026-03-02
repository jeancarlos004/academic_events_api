from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    JWTManager,
    TokenBlacklist,
    get_token_payload
)
from app.services.auth_service import AuthService
from app.schemas.auth import (
    LoginRequest, RegisterRequest, TokenResponse,
    UserOut, RefreshRequest, AccessTokenResponse
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])


# REGISTRO
@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    user = AuthService.register(db, body)
    return user


# LOGIN
@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    result = AuthService.login(db, body.email, body.password)

    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        user=UserOut.model_validate(result["user"])
    )


# REFRESH TOKEN
@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(body: RefreshRequest):
    payload = JWTManager.decode_refresh(body.refresh_token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Refresh token inválido")

    new_access = JWTManager.create_access_token({"sub": user_id})

    return AccessTokenResponse(access_token=new_access)


# LOGOUT
@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(payload: dict = Depends(get_token_payload)):
    """Revoca el access token actual."""
    jti = payload.get("jti")
    if jti:
        TokenBlacklist.revoke(jti)

    return {"message": "Sesión cerrada correctamente"}