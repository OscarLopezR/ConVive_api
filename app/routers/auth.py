import re
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..email_service import RESET_SUBJECT, deliver_reset_email
from ..models import Perfil, Preferencias, RegistroCorreo, Rol, TokenRecuperacion, Usuario
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

# Máximo de correos de recuperación por usuario dentro de la ventana (minutos).
RESET_MAX_REQUESTS = 3
RESET_WINDOW_MINUTES = 15


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


def require_role(role_name: str):
    """Dependencia que exige que el usuario autenticado tenga el rol indicado."""

    def checker(user: Usuario = Depends(get_current_user)) -> Usuario:
        if role_name not in [r.nombreRol for r in user.roles]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para esta acción.")
        return user

    return checker


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = data.email
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
def forgot_password(
    data: ForgotIn, background: BackgroundTasks, db: Session = Depends(get_db)
):
    # Respuesta siempre igual para no revelar qué correos existen.
    generic = MessageOut(
        message="Si existe una cuenta asociada, recibirás un enlace de recuperación."
    )
    user = db.scalar(select(Usuario).where(Usuario.email == data.email))
    if user is None or not user.habilitado or user.bloqueado:
        return generic

    # Límite de solicitudes: un token se creó hace menos de RESET_WINDOW si su
    # expiración está a más de (vigencia - ventana) minutos en el futuro.
    now = datetime.utcnow()
    recent_after = now + timedelta(minutes=settings.RESET_TOKEN_MINUTES - RESET_WINDOW_MINUTES)
    recent = db.scalar(
        select(func.count(TokenRecuperacion.id)).where(
            TokenRecuperacion.ID_usuario == user.id, TokenRecuperacion.expira > recent_after
        )
    )
    if recent >= RESET_MAX_REQUESTS:
        return generic  # misma respuesta: no se envía ni se revela el límite

    # Un solo enlace vigente por usuario: invalida los anteriores.
    db.execute(
        update(TokenRecuperacion)
        .where(TokenRecuperacion.ID_usuario == user.id, TokenRecuperacion.usado.is_(False))
        .values(usado=True)
    )
    token, token_hash = new_reset_token()
    db.add(
        TokenRecuperacion(
            token_hash=token_hash,
            expira=now + timedelta(minutes=settings.RESET_TOKEN_MINUTES),
            ID_usuario=user.id,
        )
    )
    registro = RegistroCorreo(
        asunto=RESET_SUBJECT,
        destinatario=user.email,
        estado_envio="PENDIENTE",
        fecha_envio=now,
        ID_usuario=user.id,
    )
    db.add(registro)
    db.commit()

    link = f"{settings.FRONTEND_URL}/recuperar/nueva?token={token}"
    background.add_task(deliver_reset_email, registro.id, user.email, link)
    return generic


def _valid_reset_token(db: Session, token: str) -> TokenRecuperacion:
    rec = db.scalar(
        select(TokenRecuperacion).where(TokenRecuperacion.token_hash == hash_reset_token(token))
    )
    if rec is None or rec.usado or rec.expira < datetime.utcnow():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El enlace es inválido o ya expiró.")
    return rec


@router.get("/recuperar/validar", response_model=MessageOut)
def validate_reset_token(
    token: str = Query(min_length=10, max_length=200), db: Session = Depends(get_db)
):
    """Permite al front comprobar el enlace del correo antes de mostrar el formulario."""
    _valid_reset_token(db, token)
    return MessageOut(message="Enlace válido.")


@router.post("/recuperar/confirmar", response_model=MessageOut)
def reset_password(data: ResetIn, db: Session = Depends(get_db)):
    rec = _valid_reset_token(db, data.token)

    user = db.get(Usuario, rec.ID_usuario)
    if verify_password(data.password, user.claveDeUsuario):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "La nueva contraseña debe ser distinta de la actual."
        )
    user.claveDeUsuario = hash_password(data.password)
    rec.usado = True
    db.commit()
    return MessageOut(message="Contraseña actualizada. Ya puedes iniciar sesión.")
