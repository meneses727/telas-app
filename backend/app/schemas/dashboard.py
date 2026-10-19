from datetime import date
from typing import Optional

from pydantic import BaseModel


class FilaCoberturaOut(BaseModel):
    tela_id: int
    codigo: str
    nombre: str
    color: Optional[str] = None
    categoria: Optional[str] = None
    cobertura_dias: Optional[float] = None
    estado: str
    accion: str


class AlertasOut(BaseModel):
    criticas: int
    exceso: int


class ResumenDashboardOut(BaseModel):
    fecha_referencia: date
    rotacion_inventario_anual: Optional[float] = None
    cobertura_promedio_dias: Optional[float] = None
    alertas: AlertasOut
    telas: list[FilaCoberturaOut]
