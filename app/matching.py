"""Compatibilidad entre un inquilino y un arrendador.

Compara el PERFIL del inquilino con las PREFERENCIAS del arrendador. Cada criterio aplicable
puntua de 0 a 1 y el porcentaje es el promedio. Si el arrendador no definio ningun criterio
comparable, no hay base para calcular y se devuelve None.
"""
from dataclasses import dataclass
from datetime import date

from .models import Usuario
from .schemas import age_on

# Los valores guardados pueden venir del front (codigos) o de datos de ejemplo en español.
_SYNONYMS = {
    "alto": "high", "alta": "high",
    "medio": "medium", "media": "medium",
    "bajo": "low", "baja": "low",
    "diurno": "day", "nocturno": "night", "mixto": "mixed",
    "estudiante": "student", "profesional": "professional",
    "ninguna": "none", "ocasionales": "some", "libres": "many",
}

_LEVEL = {"low": 0, "medium": 1, "high": 2}
_ALLOWED = {"none": 0, "some": 1, "many": 2}
_PETS = {"yes": 1.0, "small": 0.5, "no": 0.0}

OCCUPATION_LABEL = {"student": "Estudiante", "professional": "Profesional", "other": "Otra ocupación"}
SCHEDULE_LABEL = {"day": "Horario diurno", "night": "Horario nocturno", "mixed": "Horario mixto"}


def norm(value: str | None) -> str | None:
    if value is None:
        return None
    key = value.strip().lower()
    return _SYNONYMS.get(key, key) or None


def _indifferent(value: str | None) -> bool:
    return value is None or value == "any"


@dataclass
class Match:
    percent: float
    reasons: list[str]  # criterios con coincidencia total, para mostrar en la tarjeta


def profile_complete(user: Usuario) -> bool:
    p = user.perfil
    return bool(
        p
        and p.ocupacion
        and p.horario_actividad
        and p.habito_limpieza
        and p.frecuencia_visitas
        and user.fecha_nacimiento
    )


def compute_match(tenant: Usuario, landlord: Usuario, today: date | None = None) -> Match | None:
    perfil, pref = tenant.perfil, landlord.preferencias
    if perfil is None or pref is None:
        return None

    scores: list[tuple[str, float]] = []

    wanted_occ = norm(pref.ocupacion_preferida)
    if not _indifferent(wanted_occ):
        occ = norm(perfil.ocupacion)
        scores.append(("Ocupación afín", 1.0 if occ == wanted_occ else 0.5 if occ == "other" else 0.0))

    wanted_sched = norm(pref.horario_preferido)
    if not _indifferent(wanted_sched):
        sched = norm(perfil.horario_actividad)
        scores.append(("Mismo horario", 1.0 if sched == wanted_sched else 0.5 if sched == "mixed" else 0.0))

    wanted_clean = norm(pref.limpieza_preferida)
    if wanted_clean in _LEVEL and norm(perfil.habito_limpieza) in _LEVEL:
        mine, need = _LEVEL[norm(perfil.habito_limpieza)], _LEVEL[wanted_clean]
        scores.append(("Hábitos de limpieza afines", 1.0 if mine >= need else 0.5 if need - mine == 1 else 0.0))

    allowed = norm(pref.visitas_permitidas)
    if allowed in _ALLOWED and norm(perfil.frecuencia_visitas) in _LEVEL:
        need, ok = _LEVEL[norm(perfil.frecuencia_visitas)], _ALLOWED[allowed]
        scores.append(("Visitas compatibles", 1.0 if need <= ok else 0.5 if need - ok == 1 else 0.0))

    if perfil.mascotas:
        if pref.mascotas_permitidas in _PETS:
            pets = _PETS[pref.mascotas_permitidas]
        else:
            pets = 1.0 if pref.mascotas else 0.0
        scores.append(("Acepta tus mascotas", pets))

    if (pref.edad_minima or pref.edad_maxima) and tenant.fecha_nacimiento:
        age = age_on(tenant.fecha_nacimiento, today)
        inside = (pref.edad_minima or 0) <= age <= (pref.edad_maxima or 200)
        scores.append(("Dentro del rango de edad", 1.0 if inside else 0.0))

    if not scores:
        return None

    percent = round(sum(s for _, s in scores) / len(scores) * 100, 1)
    return Match(percent=percent, reasons=[label for label, s in scores if s >= 1.0])
