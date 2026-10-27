"""Diagnostico de conexion. Uso: python -m app.check_db"""
import os

from sqlalchemy import text
from sqlalchemy.engine import make_url

from .config import settings
from .database import engine

url = make_url(settings.DATABASE_URL)
print("Variable de entorno DATABASE_URL del sistema:", "SI (anula el .env)" if os.environ.get("DATABASE_URL") else "no")
print(f"Usuario: {url.username!r}  Host: {url.host}  Puerto: {url.port}  BD: {url.database}")
print("Contraseña configurada:", "SI" if url.password else "NO (vacía)")

try:
    with engine.connect() as conn:
        print("Conexión OK. Usuarios en la tabla:", conn.execute(text("SELECT COUNT(*) FROM USUARIO")).scalar())
except Exception as exc:
    print("FALLO:", exc.__class__.__name__, "-", str(exc).splitlines()[0])
