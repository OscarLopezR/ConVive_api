from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Rol(Base):
    __tablename__ = "ROL"

    idRol: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombreRol: Mapped[str] = mapped_column(String(30), unique=True)
    descripcionRol: Mapped[str | None] = mapped_column(String(255))
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class UsuarioRol(Base):
    __tablename__ = "USUARIO_ROL"

    idUsuario: Mapped[int] = mapped_column(
        ForeignKey("USUARIO.ID", ondelete="CASCADE"), primary_key=True
    )
    idRol: Mapped[int] = mapped_column(ForeignKey("ROL.idRol"), primary_key=True)


class Usuario(Base):
    __tablename__ = "USUARIO"

    id: Mapped[int] = mapped_column("ID", Integer, primary_key=True, autoincrement=True)
    nombreDeUsuario: Mapped[str] = mapped_column(String(60), unique=True)
    nombre: Mapped[str] = mapped_column(String(50))
    paterno: Mapped[str] = mapped_column(String(50))
    materno: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    claveDeUsuario: Mapped[str] = mapped_column(String(255))
    telefono: Mapped[str | None] = mapped_column(String(15))
    foto: Mapped[str | None] = mapped_column(String(255))
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date)
    habilitado: Mapped[bool] = mapped_column(Boolean, default=True)
    bloqueado: Mapped[bool] = mapped_column(Boolean, default=False)

    roles: Mapped[list[Rol]] = relationship(secondary="USUARIO_ROL", lazy="selectin")
    perfil: Mapped["Perfil | None"] = relationship(uselist=False, cascade="all, delete-orphan")
    preferencias: Mapped["Preferencias | None"] = relationship(
        uselist=False, cascade="all, delete-orphan"
    )


class Perfil(Base):
    __tablename__ = "PERFIL"

    id: Mapped[int] = mapped_column("ID", Integer, primary_key=True, autoincrement=True)
    ocupacion: Mapped[str | None] = mapped_column(String(100))
    mascotas: Mapped[bool] = mapped_column(Boolean, default=False)
    habito_limpieza: Mapped[str | None] = mapped_column(String(50))
    frecuencia_visitas: Mapped[str | None] = mapped_column(String(50))
    horario_actividad: Mapped[str | None] = mapped_column(String(50))
    ID_usuario: Mapped[int] = mapped_column(ForeignKey("USUARIO.ID"), unique=True)


class Preferencias(Base):
    __tablename__ = "PREFERENCIAS"

    id: Mapped[int] = mapped_column("ID", Integer, primary_key=True, autoincrement=True)
    mascotas: Mapped[bool] = mapped_column(Boolean, default=False)
    edad_minima: Mapped[int | None] = mapped_column(Integer)
    edad_maxima: Mapped[int | None] = mapped_column(Integer)
    genero_preferido: Mapped[str | None] = mapped_column(String(30))
    ocupacion_preferida: Mapped[str | None] = mapped_column(String(20))
    horario_preferido: Mapped[str | None] = mapped_column(String(20))
    limpieza_preferida: Mapped[str | None] = mapped_column(String(20))
    visitas_permitidas: Mapped[str | None] = mapped_column(String(20))
    mascotas_permitidas: Mapped[str | None] = mapped_column(String(20))
    fumar: Mapped[bool | None] = mapped_column(Boolean)
    ID_usuario: Mapped[int] = mapped_column(ForeignKey("USUARIO.ID"), unique=True)


class TokenRecuperacion(Base):
    __tablename__ = "TOKEN_RECUPERACION"

    id: Mapped[int] = mapped_column("ID", Integer, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expira: Mapped[datetime] = mapped_column(DateTime)
    usado: Mapped[bool] = mapped_column(Boolean, default=False)
    ID_usuario: Mapped[int] = mapped_column(ForeignKey("USUARIO.ID"))
