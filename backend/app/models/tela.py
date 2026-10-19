from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class CategoriaTela(Base):
    __tablename__ = "categorias_tela"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(255), nullable=True)

    telas = relationship("Tela", back_populates="categoria")


class Proveedor(Base):
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    lead_time_dias = Column(Integer, nullable=False, default=7)

    telas = relationship("Tela", back_populates="proveedor")


class Tela(Base):
    __tablename__ = "telas"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(30), unique=True, nullable=False, index=True)
    nombre = Column(String(150), nullable=False)
    color = Column(String(60), nullable=True)
    composicion = Column(String(150), nullable=True)
    ancho_m = Column(Numeric(6, 2), nullable=False)
    m_por_rollo = Column(Numeric(8, 2), nullable=False)
    categoria_id = Column(Integer, ForeignKey("categorias_tela.id"), nullable=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True)

    categoria = relationship("CategoriaTela", back_populates="telas")
    proveedor = relationship("Proveedor", back_populates="telas")
    umbral = relationship("UmbralStock", back_populates="tela", uselist=False)
    ventas = relationship("VentaHistorica", back_populates="tela")
    inventarios = relationship("InventarioSnapshot", back_populates="tela")


class UmbralStock(Base):
    __tablename__ = "umbrales_stock"

    id = Column(Integer, primary_key=True, index=True)
    tela_id = Column(Integer, ForeignKey("telas.id"), unique=True, nullable=False)
    cobertura_min_dias = Column(Integer, nullable=False, default=15)
    ciclo_pedido_dias = Column(Integer, nullable=False, default=30)

    tela = relationship("Tela", back_populates="umbral")
