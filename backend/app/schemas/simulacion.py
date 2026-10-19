from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SimulacionRequest(BaseModel):
    tela_id: int
    demanda_relativa_pct: float = Field(ge=0, le=200, description="0% a 200% (100% = demanda normal)")
    tendencia_pct: float = Field(ge=-50, le=50, description="-50% a +50%")


class ResultadoEscenario(BaseModel):
    pct_reposicion: Optional[float] = None
    metros_sugeridos: Optional[float] = None
    rollos_sugeridos: Optional[int] = None
    no_concluyente: bool


class DiferenciaEscenario(BaseModel):
    metros: Optional[float] = None
    rollos: Optional[int] = None
    pct_reposicion: Optional[float] = None


class ComparacionSimulacionOut(BaseModel):
    tela_id: int
    tela_codigo: str
    simulacion_id: Optional[int] = None
    parametros: SimulacionRequest
    escenario_base: ResultadoEscenario
    escenario_simulado: ResultadoEscenario
    diferencia: DiferenciaEscenario


class SimulacionHistorialOut(BaseModel):
    id: int
    fecha: datetime
    parametros: dict
    resultado: Optional[dict] = None

    class Config:
        from_attributes = True
