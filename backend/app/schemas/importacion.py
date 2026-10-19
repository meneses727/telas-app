from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ErrorFila(BaseModel):
    fila: int
    motivo: str


class ResultadoImportacion(BaseModel):
    lote_id: int
    tipo: str
    archivo: str
    filas_totales: int
    filas_validas: int
    filas_con_error: int
    estado: str
    errores: list[ErrorFila]  # primeros N errores, para previsualización


class LoteImportacionOut(BaseModel):
    id: int
    tipo: str
    archivo: str
    fecha_carga: datetime
    filas_totales: int
    filas_validas: int
    filas_con_error: int
    estado: str
    usuario_nombre: Optional[str] = None

    class Config:
        from_attributes = True
