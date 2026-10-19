from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class Rol(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, nullable=False)  # "Planificador" | "Administrador"

    usuarios = relationship("Usuario", back_populates="rol")


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    correo = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    estado = Column(Boolean, default=True, nullable=False)  # activo/inactivo
    intentos_fallidos = Column(Integer, default=0, nullable=False)
    bloqueado_hasta = Column(DateTime, nullable=True)
    rol_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    rol = relationship("Rol", back_populates="usuarios")
    bitacora = relationship("BitacoraAcceso", back_populates="usuario")
    lotes_importacion = relationship("LoteImportacion", back_populates="usuario")


class BitacoraAcceso(Base):
    __tablename__ = "bitacora_accesos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)
    evento = Column(String(50), nullable=False)  # "login_ok" | "login_fallido" | "bloqueo"
    ip = Column(String(45), nullable=True)

    usuario = relationship("Usuario", back_populates="bitacora")
