from datetime import datetime

from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class IndiceEstacional(Base):
    __tablename__ = "indices_estacionales"

    id = Column(Integer, primary_key=True, index=True)
    tela_id = Column(Integer, ForeignKey("telas.id"), nullable=False)
    mes = Column(Integer, nullable=False)  # 1-12
    indice = Column(Numeric(6, 3), nullable=False)  # 1.0 = promedio

    tela = relationship("Tela")


class ClasificacionDemanda(Base):
    __tablename__ = "clasificaciones_demanda"

    id = Column(Integer, primary_key=True, index=True)
    tela_id = Column(Integer, ForeignKey("telas.id"), nullable=False)
    clase = Column(String(30), nullable=False)  # clúster K-Means: "baja"|"media"|"alta" (o label numérico)
    fecha = Column(DateTime, default=datetime.utcnow)

    tela = relationship("Tela")


class EvaluacionExperta(Base):
    __tablename__ = "evaluaciones_expertas"

    id = Column(Integer, primary_key=True, index=True)
    tela_id = Column(Integer, ForeignKey("telas.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    percepcion = Column(Integer, nullable=False)  # escala 1-5 de tendencia percibida por el planificador
    fecha = Column(DateTime, default=datetime.utcnow)

    tela = relationship("Tela")
