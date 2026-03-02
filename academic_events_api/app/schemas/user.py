from pydantic import BaseModel, EmailStr, field_validator

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        # Verificar longitud mínima y máxima en caracteres
        if len(v) < 6:
            raise ValueError('La contraseña debe tener al menos 6 caracteres')
        if len(v) > 50:
            raise ValueError('La contraseña no puede tener más de 50 caracteres')
        
        # Asegurar que solo use caracteres ASCII (evita problemas de encoding)
        try:
            v.encode('ascii')
        except UnicodeEncodeError:
            raise ValueError('La contraseña solo puede contener caracteres ASCII (letras sin acentos, números y símbolos básicos)')
        
        return v

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr

    class Config:
        from_attributes = True