from datetime import datetime

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class PropuestaCompra(Base):
    __tablename__ = "propuestas_compra"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)
    estado = Column(String(20), default="borrador")  # "borrador" | "cerrada"

    items = relationship("RecomendacionCompra", back_populates="propuesta")
    usuario = relationship("Usuario")


class RecomendacionCompra(Base):
    __tablename__ = "recomendaciones_compra"

    id = Column(Integer, primary_key=True, index=True)
    tela_id = Column(Integer, ForeignKey("telas.id"), nullable=False)
    propuesta_id = Column(Integer, ForeignKey("propuestas_compra.id"), nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow)
    pct_reposicion = Column(Numeric(5, 2), nullable=True)
    metros_sugeridos = Column(Numeric(10, 2), nullable=True)
    metros_ajustados = Column(Numeric(10, 2), nullable=True)
    rollos = Column(Integer, nullable=True)
    no_concluyente = Column(Boolean, default=False)
    motivo_ajuste = Column(String(255), nullable=True)
    reglas_activadas = Column(JSON, nullable=True)  # detalle de reglas Mamdani activadas

    propuesta = relationship("PropuestaCompra", back_populates="items")
    tela = relationship("Tela")


class Simulacion(Base):
    __tablename__ = "simulaciones"

    id = Column(Integer, primary_key=True, index=True)
    tela_id = Column(Integer, ForeignKey("telas.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)
    parametros = Column(JSON, nullable=False)  # {"demanda_relativa_pct":.., "tendencia_pct":..}
    resultado = Column(JSON, nullable=True)
