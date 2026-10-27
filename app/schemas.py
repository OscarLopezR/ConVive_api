from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Los codigos coinciden con los ids que usa el front (register.ts).
RoleCode = Literal["tenant", "landlord"]


class RegisterIn(BaseModel):
    role: RoleCode
    nombre: str = Field(min_length=1, max_length=50)
    apellidos: str = Field(min_length=1, max_length=100, description="Paterno y materno juntos")
    email: EmailStr
    telefono: str | None = Field(default=None, max_length=20)
    password: str = Field(min_length=8, max_length=72)
    fecha_nacimiento: date

    # Inquilino: estilo de vida y preferencias
    occupation: str | None = None
    schedule: str | None = None
    cleanliness: str | None = None
    visits: str | None = None
    pets: str | None = None  # none | dog | cat | other
    pet_preference: str | None = None  # no-pets | pets-ok | any
    age_range: str | None = None  # '20-30', '40+', 'any'
    gender_preference: str | None = None

    # Arrendador: perfil ideal de quien compartira el espacio
    tenant_occupation: str | None = None
    tenant_schedule: str | None = None
    tenant_cleanliness: str | None = None
    visits_allowed: str | None = None
    pets_allowed: str | None = None  # no | small | yes
    smoking: str | None = None  # no | any


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombreDeUsuario: str
    nombre: str
    paterno: str
    materno: str | None
    email: EmailStr
    telefono: str | None
    roles: list[str]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str = Field(min_length=10)
    password: str = Field(min_length=8, max_length=72)


class MessageOut(BaseModel):
    message: str
