from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AccionAdmin, Rol, Usuario, UsuarioRol
from .auth import require_role

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminUserOut(BaseModel):
    id: int
    nombreDeUsuario: str
    nombre: str
    paterno: str
    email: str
    roles: list[str]
    habilitado: bool
    bloqueado: bool


class EstadoIn(BaseModel):
    valor: bool
    motivo: str | None = Field(default=None, max_length=200)


class AccionOut(BaseModel):
    id: int
    accion: str
    tipo_objetivo: str
    id_objetivo: int
    detalle: str | None
    fecha: str
    ID_admin: int


def _out(u: Usuario) -> AdminUserOut:
    return AdminUserOut(
        id=u.id,
        nombreDeUsuario=u.nombreDeUsuario,
        nombre=u.nombre,
        paterno=u.paterno,
        email=u.email,
        roles=[r.nombreRol for r in u.roles],
        habilitado=u.habilitado,
        bloqueado=u.bloqueado,
    )


def _log(db: Session, admin: Usuario, accion: str, objetivo_id: int, detalle: str | None):
    db.add(
        AccionAdmin(
            accion=accion,
            tipo_objetivo="USUARIO",
            id_objetivo=objetivo_id,
            detalle=detalle,
            ID_admin=admin.id,
        )
    )


def _target(db: Session, admin: Usuario, user_id: int) -> Usuario:
    user = db.get(Usuario, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No puedes modificar tu propia cuenta.")
    return user


@router.get("/usuarios", response_model=list[AdminUserOut])
def list_users(
    q: str | None = Query(default=None, description="Busca por nombre, usuario o correo"),
    rol: str | None = Query(default=None, description="INQUILINO, ARRENDADOR o ADMIN"),
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(require_role("ADMIN")),
):
    stmt = select(Usuario).order_by(Usuario.id).limit(limit).offset(offset)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Usuario.nombre.like(like),
                Usuario.paterno.like(like),
                Usuario.email.like(like),
                Usuario.nombreDeUsuario.like(like),
            )
        )
    if rol:
        stmt = stmt.join(UsuarioRol, UsuarioRol.idUsuario == Usuario.id).join(
            Rol, Rol.idRol == UsuarioRol.idRol
        ).where(Rol.nombreRol == rol)
    return [_out(u) for u in db.scalars(stmt).all()]


@router.patch("/usuarios/{user_id}/bloqueo", response_model=AdminUserOut)
def set_blocked(
    user_id: int,
    data: EstadoIn,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("ADMIN")),
):
    user = _target(db, admin, user_id)
    user.bloqueado = data.valor
    _log(db, admin, "BLOQUEAR_USUARIO" if data.valor else "DESBLOQUEAR_USUARIO", user.id, data.motivo)
    db.commit()
    return _out(user)


@router.patch("/usuarios/{user_id}/habilitado", response_model=AdminUserOut)
def set_enabled(
    user_id: int,
    data: EstadoIn,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("ADMIN")),
):
    user = _target(db, admin, user_id)
    user.habilitado = data.valor
    _log(db, admin, "HABILITAR_USUARIO" if data.valor else "DESHABILITAR_USUARIO", user.id, data.motivo)
    db.commit()
    return _out(user)


@router.get("/estadisticas")
def stats(
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(require_role("ADMIN")),
):
    por_rol = db.execute(
        select(Rol.nombreRol, func.count(UsuarioRol.idUsuario))
        .join(UsuarioRol, UsuarioRol.idRol == Rol.idRol, isouter=True)
        .group_by(Rol.nombreRol)
    ).all()
    return {
        "usuarios_total": db.scalar(select(func.count(Usuario.id))),
        "usuarios_bloqueados": db.scalar(
            select(func.count(Usuario.id)).where(Usuario.bloqueado.is_(True))
        ),
        "usuarios_por_rol": {nombre: total for nombre, total in por_rol},
    }


@router.get("/acciones", response_model=list[AccionOut])
def audit_log(
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(require_role("ADMIN")),
):
    rows = db.scalars(select(AccionAdmin).order_by(AccionAdmin.id.desc()).limit(limit)).all()
    return [
        AccionOut(
            id=a.id,
            accion=a.accion,
            tipo_objetivo=a.tipo_objetivo,
            id_objetivo=a.id_objetivo,
            detalle=a.detalle,
            fecha=a.fecha.isoformat(),
            ID_admin=a.ID_admin,
        )
        for a in rows
    ]
