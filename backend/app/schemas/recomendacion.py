from typing import Optional

from pydantic import BaseModel


class ReglaActivadaOut(BaseModel):
    codigo: str
    condiciones: str
    conclusion: str
    grado_activacion: float


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


class RecomendacionCalculoOut(BaseModel):
    tela_id: int
    tela_codigo: str
    stock_actual_metros: Optional[float] = None
    consumo_diario_promedio: Optional[float] = None
    cobertura_dias: Optional[float] = None
    demanda_relativa: DemandaRelativaOut
    tendencia: TendenciaOut
    grados_cobertura: dict[str, float] = {}
    grados_demanda: dict[str, float] = {}
    grados_tendencia: dict[str, float] = {}
    reglas_activadas: list[ReglaActivadaOut] = []
    pct_reposicion: Optional[float] = None
    metros_sugeridos: Optional[float] = None
    rollos_sugeridos: Optional[int] = None
    no_concluyente: bool
    motivo: Optional[str] = None


class AgregarAPropuestaRequest(BaseModel):
    tela_id: int
    metros_ajustados: Optional[float] = None  # si el planificador ajusta el valor sugerido
    motivo_ajuste: Optional[str] = None
    propuesta_id: Optional[int] = None  # si no se da, se usa/crea el borrador abierto del usuario
