from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ItemPropuestaOut(BaseModel):
    item_id: int
    tela_id: int
    tela_codigo: str
    tela_nombre: str
    pct_reposicion: Optional[float] = None
    metros_sugeridos: Optional[float] = None
    metros_ajustados: Optional[float] = None
    metros_finales: Optional[float] = None
    rollos: Optional[int] = None
    no_concluyente: bool
    motivo_ajuste: Optional[str] = None


class PropuestaDetalleOut(BaseModel):
    propuesta_id: int
    estado: str
    fecha: datetime
    responsable: Optional[str] = None
    items: list[ItemPropuestaOut]
    total_metros: float
    total_rollos: int


class ActualizarItemRequest(BaseModel):
    metros_ajustados: float = Field(gt=0)
    motivo_ajuste: Optional[str] = None
