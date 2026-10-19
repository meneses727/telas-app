from datetime import datetime

from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class LoteImportacion(Base):
    __tablename__ = "lotes_importacion"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    tipo = Column(String(20), nullable=False)  # "ventas" | "inventario"
    archivo = Column(String(255), nullable=False)
    fecha_carga = Column(DateTime, default=datetime.utcnow)
    filas_totales = Column(Integer, default=0)
    filas_validas = Column(Integer, default=0)
    filas_con_error = Column(Integer, default=0)
    estado = Column(String(20), default="procesado")  # "procesado" | "con_errores" | "fallido"

    usuario = relationship("Usuario", back_populates="lotes_importacion")
    ventas = relationship("VentaHistorica", back_populates="lote")
    inventarios = relationship("InventarioSnapshot", back_populates="lote")


class VentaHistorica(Base):
    __tablename__ = "ventas_historicas"

    id = Column(Integer, primary_key=True, index=True)
    tela_id = Column(Integer, ForeignKey("telas.id"), nullable=False)
    lote_id = Column(Integer, ForeignKey("lotes_importacion.id"), nullable=True)
    fecha = Column(Date, nullable=False)
    metros = Column(Numeric(10, 2), nullable=False)
    cliente_tipo = Column(String(60), nullable=True)

    tela = relationship("Tela", back_populates="ventas")
    lote = relationship("LoteImportacion", back_populates="ventas")


class InventarioSnapshot(Base):
    __tablename__ = "inventario_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    tela_id = Column(Integer, ForeignKey("telas.id"), nullable=False)
    lote_id = Column(Integer, ForeignKey("lotes_importacion.id"), nullable=True)
    fecha_corte = Column(Date, nullable=False)
    stock_metros = Column(Numeric(10, 2), nullable=False)
    rollos = Column(Integer, nullable=True)

    tela = relationship("Tela", back_populates="inventarios")
    lote = relationship("LoteImportacion", back_populates="inventarios")
