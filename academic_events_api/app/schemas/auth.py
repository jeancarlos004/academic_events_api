from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional


# ---------------------------
# Esquemas de Usuario
# ---------------------------
class UserBase(BaseModel):
    nombre: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class RegisterRequest(UserCreate):
    rol: str = "usuario"

    @field_validator("rol")
    @classmethod
    def validate_rol(cls, v: str):
        allowed = {"admin", "usuario"}
        if v not in allowed:
            raise ValueError("Rol inválido")
        return v


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


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str