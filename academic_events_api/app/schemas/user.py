from pydantic import BaseModel, EmailStr, field_validator, Field, AliasChoices, ConfigDict

class UserCreate(BaseModel):
    nombre: str = Field(validation_alias=AliasChoices("nombre", "name"))
    email: EmailStr
    password: str
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        # Verificar longitud mínima y máxima en caracteres
        if len(v) < 6:
            raise ValueError('La contraseña debe tener al menos 6 caracteres')
        if len(v) > 128:
            raise ValueError('La contraseña no puede tener más de 128 caracteres')
        
        return v

class UserOut(BaseModel):
    id: int
    nombre: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)