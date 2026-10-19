from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class EvaluacionExpertaCreate(BaseModel):
    tela_id: int
    percepcion: int = Field(ge=1, le=5, description="Percepción de tendencia del planificador, escala 1-5")


class DemandaRelativaOut(BaseModel):
    ratio: Optional[float] = None
    categoria: str
    total_reciente: Optional[float] = None
    esperado: Optional[float] = None
    motivo: Optional[str] = None


class TendenciaOut(BaseModel):
    variacion_ventas: float
    percepcion_planificador: int
    score: float
    categoria: str


class ResumenMineriaOut(BaseModel):
    tela_id: int
    tela_codigo: str
    indice_estacional: dict[int, float]
    clase_demanda: Optional[str] = None
    demanda_relativa: DemandaRelativaOut
    tendencia: TendenciaOut
    fecha_referencia: date
