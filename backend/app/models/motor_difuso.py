from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class VariableLinguistica(Base):
    __tablename__ = "variables_linguisticas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(60), nullable=False)  # "cobertura" | "demanda_relativa" | "tendencia"
    minimo = Column(Numeric(10, 2), nullable=False)
    maximo = Column(Numeric(10, 2), nullable=False)

    conjuntos = relationship("ConjuntoDifuso", back_populates="variable")


class ConjuntoDifuso(Base):
    __tablename__ = "conjuntos_difusos"

    id = Column(Integer, primary_key=True, index=True)
    variable_id = Column(Integer, ForeignKey("variables_linguisticas.id"), nullable=False)
    etiqueta = Column(String(60), nullable=False)  # "Crítica" | "Adecuada" | "Exceso" | ...
    # Puntos de la función de pertenencia trapezoidal/triangular: a <= b <= c <= d
    a = Column(Numeric(10, 2), nullable=False)
    b = Column(Numeric(10, 2), nullable=False)
    c = Column(Numeric(10, 2), nullable=False)
    d = Column(Numeric(10, 2), nullable=False)

    variable = relationship("VariableLinguistica", back_populates="conjuntos")


class ReglaDifusa(Base):
    __tablename__ = "reglas_difusas"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(20), unique=True, nullable=False)  # "R01".."R27"
    cobertura = Column(String(30), nullable=False)       # Crítica | Adecuada | Exceso
    demanda_relativa = Column(String(30), nullable=False)  # Normal | Alta
    tendencia = Column(String(30), nullable=False)        # Estable | Ascendente
    reposicion = Column(String(30), nullable=False)       # Baja | Media | Alta
    peso = Column(Numeric(3, 2), default=1.0)
    activa = Column(Boolean, default=True)
