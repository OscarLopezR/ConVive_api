from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

FIELD_LABELS = {
    "role": "Tipo de cuenta",
    "nombre": "Nombre",
    "apellidos": "Apellidos",
    "email": "Correo electrónico",
    "telefono": "Teléfono",
    "password": "Contraseña",
    "fecha_nacimiento": "Fecha de nacimiento",
    "token": "Enlace de recuperación",
}

TYPE_MESSAGES = {
    "missing": "Este campo es obligatorio.",
    "string_too_short": "Es demasiado corto.",
    "string_too_long": "Es demasiado largo.",
    "literal_error": "Opción no válida.",
    "date_from_datetime_parsing": "Fecha no válida.",
    "date_parsing": "Fecha no válida.",
    "date_type": "Fecha no válida.",
    "value_error": "Valor no válido.",
    "extra_forbidden": "Campo no permitido.",
    "string_type": "Debe ser texto.",
    "json_invalid": "El cuerpo de la petición no es JSON válido.",
}


def _message(err: dict) -> str:
    if err["type"] == "value_error":
        msg = err.get("msg", "")
        # Pydantic antepone "Value error, " a los mensajes de los validadores propios.
        msg = msg.removeprefix("Value error, ")
        if err.get("loc", ())[-1:] == ("email",) and "email" in msg.lower():
            return "Ingresa un correo electrónico válido."
        return msg or TYPE_MESSAGES["value_error"]
    return TYPE_MESSAGES.get(err["type"], "Valor no válido.")


async def validation_exception_handler(_: Request, exc: RequestValidationError):
    errors: dict[str, str] = {}
    for err in exc.errors():
        loc = [str(p) for p in err["loc"] if p not in ("body", "query", "path")]
        field = ".".join(loc) or "body"
        errors.setdefault(field, _message(err))

    first_field, first_msg = next(iter(errors.items()))
    label = FIELD_LABELS.get(first_field)
    detail = f"{label}: {first_msg}" if label and not first_msg.startswith(label) else first_msg
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"detail": detail, "errors": errors}),
    )
