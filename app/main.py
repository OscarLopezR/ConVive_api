from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .errors import validation_exception_handler
from .routers import admin, auth, inquilino

app = FastAPI(title="ConVive API", version="0.1.0")
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(inquilino.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
