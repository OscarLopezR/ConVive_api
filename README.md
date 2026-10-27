# ConVive API

Backend de ConVive (FastAPI + SQLAlchemy + MySQL/MariaDB).

## Puesta en marcha

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # edita DATABASE_URL y SECRET_KEY
python -m app.seed            # hash de contraseñas de prueba (Convive123)
uvicorn app.main:app --reload
```

Documentación interactiva: http://localhost:8000/docs

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/register` | Crea cuenta (role `tenant` o `landlord`) y devuelve JWT |
| POST | `/auth/login` | Inicia sesión con email y contraseña |
| GET | `/auth/me` | Usuario actual (Bearer token) |
| POST | `/auth/recuperar` | Solicita enlace de recuperación (sin SMTP se imprime en consola) |
| POST | `/auth/recuperar/confirmar` | Cambia la contraseña con el token del enlace |

## Modelo de seguridad

`ROL`, `USUARIO` y `USUARIO_ROL` siguen el esquema del profesor. Las contraseñas
(`claveDeUsuario`) se guardan con bcrypt y los tokens de recuperación solo como SHA-256.
