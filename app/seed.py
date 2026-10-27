"""Asigna hash bcrypt a los usuarios de prueba cargados desde db_vivienda.sql.

Uso: python -m app.seed
Contrasena de prueba: Convive123
"""
from sqlalchemy import select

from .database import SessionLocal
from .models import Usuario
from .security import hash_password

DEMO_PASSWORD = "Convive123"


def main() -> None:
    with SessionLocal() as db:
        users = db.scalars(
            select(Usuario).where(Usuario.claveDeUsuario == "PENDIENTE_SEED")
        ).all()
        for user in users:
            user.claveDeUsuario = hash_password(DEMO_PASSWORD)
        db.commit()
        print(f"{len(users)} usuarios actualizados (contraseña: {DEMO_PASSWORD}).")


if __name__ == "__main__":
    main()
