import re
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..matching import (
    OCCUPATION_LABEL,
    SCHEDULE_LABEL,
    compute_match,
    norm,
    profile_complete,
)
from ..models import Habitacion, Usuario
from .auth import require_role

router = APIRouter(prefix="/inquilino", tags=["inquilino"])

# Por debajo de este porcentaje no se recomienda la habitación.
MIN_COMPATIBILITY = 50.0


class LandlordOut(BaseModel):
    nombre: str
    ocupacion: str | None
    horario: str | None


class RoomMatchOut(BaseModel):
    id: int
    titulo: str
    colonia: str | None
    delegacion: str | None
    estado: str | None
    metros: float | None
    servicios: list[str]
    precio: float
    compatibilidad: float
    coincidencias: list[str]
    arrendador: LandlordOut


class RecommendationsOut(BaseModel):
    perfil_completo: bool
    total: int
    items: list[RoomMatchOut]


def _services(room: Habitacion) -> list[str]:
    pairs = [
        (room.serv_agua, "Agua"),
        (room.serv_luz, "Luz"),
        (room.serv_internet, "Internet"),
        (room.serv_gas, "Gas"),
    ]
    return [label for on, label in pairs if on]


def _landlord_out(landlord: Usuario) -> LandlordOut:
    perfil = landlord.perfil
    occupation = schedule = None
    if perfil:
        key = norm(perfil.ocupacion)
        occupation = OCCUPATION_LABEL.get(key, perfil.ocupacion)
        schedule = SCHEDULE_LABEL.get(norm(perfil.horario_actividad))
    return LandlordOut(nombre=landlord.nombre, ocupacion=occupation, horario=schedule)


@router.get("/recomendaciones", response_model=RecommendationsOut)
def recommendations(
    ubicacion: str | None = Query(default=None, max_length=100, description="Colonias separadas por coma o 'y'"),
    presupuesto_max: float | None = Query(default=None, ge=0),
    orden: Literal["compatibilidad", "precio_asc", "precio_desc"] = "compatibilidad",
    db: Session = Depends(get_db),
    tenant: Usuario = Depends(require_role("INQUILINO")),
):
    complete = profile_complete(tenant)

    stmt = (
        select(Habitacion)
        .join(Usuario, Usuario.id == Habitacion.ID_arrendador)
        .where(
            Habitacion.disponibilidad.is_(True),
            Usuario.habilitado.is_(True),
            Usuario.bloqueado.is_(False),
        )
    )
    if presupuesto_max is not None:
        stmt = stmt.where(Habitacion.precio <= presupuesto_max)

    terms = [t.strip() for t in re.split(r",|\sy\s", ubicacion or "") if t.strip()]
    if terms:
        conditions = []
        for term in terms:
            like = f"%{term}%"
            conditions += [
                Habitacion.colonia.like(like),
                Habitacion.delegacion.like(like),
                Habitacion.estado.like(like),
                Habitacion.calle.like(like),
            ]
        stmt = stmt.where(or_(*conditions))

    items: list[RoomMatchOut] = []
    for room in db.scalars(stmt).unique().all():
        match = compute_match(tenant, room.arrendador)
        if match is None or match.percent < MIN_COMPATIBILITY:
            continue
        items.append(
            RoomMatchOut(
                id=room.id,
                titulo=room.titulo,
                colonia=room.colonia,
                delegacion=room.delegacion,
                estado=room.estado,
                metros=float(room.metros) if room.metros is not None else None,
                servicios=_services(room),
                precio=float(room.precio),
                compatibilidad=match.percent,
                coincidencias=match.reasons[:3],
                arrendador=_landlord_out(room.arrendador),
            )
        )

    if orden == "precio_asc":
        items.sort(key=lambda r: r.precio)
    elif orden == "precio_desc":
        items.sort(key=lambda r: -r.precio)
    else:
        items.sort(key=lambda r: (-r.compatibilidad, r.precio))

    return RecommendationsOut(perfil_completo=complete, total=len(items), items=items)
