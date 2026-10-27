import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..email_service import send_reset_email
from ..models import Perfil, Preferencias, Rol, TokenRecuperacion, Usuario
from ..schemas import (
    ForgotIn,
    LoginIn,
    MessageOut,
    RegisterIn,
    ResetIn,
    TokenOut,
    UserOut,
)
from ..security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_reset_token,
    new_reset_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)

ROLE_NAMES = {"tenant": "INQUILINO", "landlord": "ARRENDADOR"}


def _user_out(user: Usuario) -> UserOut:
    return UserOut(
        id=user.id,
        nombreDeUsuario=user.nombreDeUsuario,
        nombre=user.nombre,
        paterno=user.paterno,
        materno=user.materno,
        email=user.email,
        telefono=user.telefono,
        roles=[r.nombreRol for r in user.roles],
    )


def _unique_username(db: Session, email: str) -> str:
    base = re.sub(r"[^a-z0-9._-]", "", email.split("@")[0].lower()) or "usuario"
    candidate, n = base, 1
    while db.scalar(select(Usuario.id).where(Usuario.nombreDeUsuario == candidate)):
        n += 1
        candidate = f"{base}{n}"
    return candidate


def _age_range(code: str | None) -> tuple[int | None, int | None]:
    if not code or code == "any":
        return None, None
    if code.endswith("+"):
        return int(code[:-1]), None
    low, high = code.split("-")
    return int(low), int(high)


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida o expirada.")
    if cred is None:
        raise unauthorized
    try:
        user_id = int(decode_access_token(cred.credentials)["sub"])
    except Exception:
        raise unauthorized
    user = db.get(Usuario, user_id)
    if user is None or not user.habilitado or user.bloqueado:
        raise unauthorized
    return user


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(Usuario.id).where(Usuario.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una cuenta con ese correo.")

    rol = db.scalar(select(Rol).where(Rol.nombreRol == ROLE_NAMES[data.role]))
    if rol is None:
        raise HTTPException(500, "Los roles no están inicializados en la base de datos.")

    partes = data.apellidos.split()
    user = Usuario(
        nombreDeUsuario=_unique_username(db, email),
        nombre=data.nombre.strip(),
        paterno=partes[0],
        materno=" ".join(partes[1:]) or None,
        email=email,
        claveDeUsuario=hash_password(data.password),
        telefono=data.telefono,
        fecha_nacimiento=data.fecha_nacimiento,
        habilitado=True,
        bloqueado=False,
        roles=[rol],
    )

    if data.role == "tenant":
        low, high = _age_range(data.age_range)
        user.perfil = Perfil(
            ocupacion=data.occupation,
            mascotas=data.pets not in (None, "none"),
            habito_limpieza=data.cleanliness,
            frecuencia_visitas=data.visits,
            horario_actividad=data.schedule,
        )
        user.preferencias = Preferencias(
            mascotas=data.pet_preference == "pets-ok",
            edad_minima=low,
            edad_maxima=high,
            genero_preferido=data.gender_preference,
        )
    else:
        user.preferencias = Preferencias(
            mascotas=data.pets_allowed in ("small", "yes"),
            mascotas_permitidas=data.pets_allowed,
            ocupacion_preferida=data.tenant_occupation,
            horario_preferido=data.tenant_schedule,
            limpieza_preferida=data.tenant_cleanliness,
            visitas_permitidas=data.visits_allowed,
            fumar=data.smoking == "any",
        )

    db.add(user)
    db.commit()
    db.refresh(user)
    roles = [r.nombreRol for r in user.roles]
    return TokenOut(access_token=create_access_token(user.id, roles), user=_user_out(user))


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(Usuario).where(Usuario.email == data.email.lower()))
    if user is None or not verify_password(data.password, user.claveDeUsuario):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos.")
    if not user.habilitado or user.bloqueado:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tu cuenta está deshabilitada o bloqueada.")
    roles = [r.nombreRol for r in user.roles]
    return TokenOut(access_token=create_access_token(user.id, roles), user=_user_out(user))


@router.get("/me", response_model=UserOut)
def me(user: Usuario = Depends(get_current_user)):
    return _user_out(user)


@router.post("/recuperar", response_model=MessageOut)
def forgot_password(data: ForgotIn, db: Session = Depends(get_db)):
    # Respuesta siempre igual para no revelar qué correos existen.
    generic = MessageOut(
        message="Si existe una cuenta asociada, recibirás un enlace de recuperación."
    )
    user = db.scalar(select(Usuario).where(Usuario.email == data.email.lower()))
    if user is None or not user.habilitado or user.bloqueado:
        return generic

    token, token_hash = new_reset_token()
    db.add(
        TokenRecuperacion(
            token_hash=token_hash,
            expira=datetime.utcnow() + timedelta(minutes=settings.RESET_TOKEN_MINUTES),
            ID_usuario=user.id,
        )
    )
    db.commit()
    send_reset_email(user.email, f"{settings.FRONTEND_URL}/recuperar/nueva?token={token}")
    return generic


@router.post("/recuperar/confirmar", response_model=MessageOut)
def reset_password(data: ResetIn, db: Session = Depends(get_db)):
    rec = db.scalar(
        select(TokenRecuperacion).where(
            TokenRecuperacion.token_hash == hash_reset_token(data.token)
        )
    )
    if rec is None or rec.usado or rec.expira < datetime.utcnow():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El enlace es inválido o ya expiró.")

    user = db.get(Usuario, rec.ID_usuario)
    user.claveDeUsuario = hash_password(data.password)
    rec.usado = True
    db.commit()
    return MessageOut(message="Contraseña actualizada. Ya puedes iniciar sesión.")
