from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    correo: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioOut(BaseModel):
    id: int
    nombre: str
    correo: EmailStr
    rol: str

    class Config:
        from_attributes = True
