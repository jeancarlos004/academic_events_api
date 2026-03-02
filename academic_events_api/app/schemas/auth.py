from pydantic import BaseModel, EmailStr
from typing import Optional


# ---------------------------
# Esquemas de Usuario
# ---------------------------
class UserBase(BaseModel):
    nombre: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: int
    rol: str

    class Config:
        from_attributes = True


# ---------------------------
# Esquemas de Autenticación
# ---------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(UserCreate):
    pass


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str