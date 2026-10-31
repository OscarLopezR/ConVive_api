import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

MIN_AGE = 18
MAX_AGE = 100

NAME_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:[ '\-][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)*$")

# Los codigos coinciden con los ids que usa el front (register.ts).
RoleCode = Literal["tenant", "landlord"]
Occupation = Literal["student", "professional", "other"]
Schedule = Literal["day", "night", "mixed"]
Level = Literal["high", "medium", "low"]
PetsOwned = Literal["none", "dog", "cat", "other"]
PetPreference = Literal["no-pets", "pets-ok", "any"]
AgeRange = Literal["18-20", "20-30", "30-40", "40+", "any"]
Gender = Literal["any", "female", "male"]
TenantOccupation = Literal["any", "student", "professional"]
TenantSchedule = Literal["any", "day", "night"]
VisitsAllowed = Literal["none", "some", "many"]
PetsAllowed = Literal["no", "small", "yes"]
Smoking = Literal["no", "any"]


def validate_password_strength(value: str) -> str:
    """Minimo 8 caracteres, con mayuscula, minuscula y numero."""
    if len(value) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    if len(value.encode()) > 72:
        raise ValueError("La contraseña es demasiado larga (máximo 72 bytes).")
    if not re.search(r"[A-Z]", value):
        raise ValueError("La contraseña debe incluir al menos una mayúscula.")
    if not re.search(r"[a-z]", value):
        raise ValueError("La contraseña debe incluir al menos una minúscula.")
    if not re.search(r"\d", value):
        raise ValueError("La contraseña debe incluir al menos un número.")
    return value


def _clean_name(value: str, label: str) -> str:
    value = " ".join(value.split())
    if not NAME_RE.match(value):
        raise ValueError(f"{label} solo puede contener letras, espacios, guiones y apóstrofos.")
    return value


def age_on(born: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


class RegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: RoleCode
    nombre: str = Field(min_length=1, max_length=50)
    apellidos: str = Field(min_length=1, max_length=100, description="Paterno y materno juntos")
    email: EmailStr
    telefono: str | None = None
    password: str
    fecha_nacimiento: date

    # Inquilino: estilo de vida y preferencias
    occupation: Occupation | None = None
    schedule: Schedule | None = None
    cleanliness: Level | None = None
    visits: Level | None = None
    pets: PetsOwned | None = None
    pet_preference: PetPreference | None = None
    age_range: AgeRange | None = None
    gender_preference: Gender | None = None

    # Arrendador: perfil ideal de quien compartira el espacio
    tenant_occupation: TenantOccupation | None = None
    tenant_schedule: TenantSchedule | None = None
    tenant_cleanliness: Level | None = None
    visits_allowed: VisitsAllowed | None = None
    pets_allowed: PetsAllowed | None = None
    smoking: Smoking | None = None

    @field_validator("nombre")
    @classmethod
    def _nombre(cls, v: str) -> str:
        return _clean_name(v, "El nombre")

    @field_validator("apellidos")
    @classmethod
    def _apellidos(cls, v: str) -> str:
        return _clean_name(v, "Los apellidos")

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return v.lower()

    @field_validator("telefono")
    @classmethod
    def _telefono(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        digits = re.sub(r"[\s\-()]", "", v)
        if not re.fullmatch(r"\d{10}", digits):
            raise ValueError("El teléfono debe tener 10 dígitos.")
        return digits

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return validate_password_strength(v)

    @field_validator("fecha_nacimiento")
    @classmethod
    def _birth(cls, v: date) -> date:
        age = age_on(v)
        if age < 0:
            raise ValueError("La fecha de nacimiento no puede ser futura.")
        if age < MIN_AGE:
            raise ValueError(f"Debes ser mayor de {MIN_AGE} años para registrarte.")
        if age > MAX_AGE:
            raise ValueError("La fecha de nacimiento no es válida.")
        return v

    @model_validator(mode="after")
    def _role_fields(self):
        if self.role == "tenant":
            required = ["occupation", "schedule", "cleanliness", "visits", "pets",
                        "pet_preference", "age_range", "gender_preference"]
        else:
            required = ["tenant_occupation", "tenant_schedule", "tenant_cleanliness",
                        "visits_allowed", "pets_allowed", "smoking"]
        missing = [f for f in required if getattr(self, f) is None]
        if missing:
            raise ValueError(f"Faltan datos de estilo de vida: {', '.join(missing)}.")
        return self


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return v.lower()


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

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return v.lower()


class ResetIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    password: str

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return validate_password_strength(v)


class MessageOut(BaseModel):
    message: str
