from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_validator


class CategoriaTelaOut(BaseModel):
    id: int
    nombre: str

    class Config:
        from_attributes = True


class ProveedorOut(BaseModel):
    id: int
    nombre: str
    lead_time_dias: int

    class Config:
        from_attributes = True


class TelaBase(BaseModel):
    codigo: str
    nombre: str
    color: Optional[str] = None
    composicion: Optional[str] = None
    ancho_m: Decimal
    m_por_rollo: Decimal
    categoria_id: Optional[int] = None
    proveedor_id: Optional[int] = None

    @field_validator("codigo")
    @classmethod
    def codigo_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El código no puede estar vacío")
        return v.upper()

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío")
        return v

    @field_validator("ancho_m", "m_por_rollo")
    @classmethod
    def valores_positivos(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("El valor debe ser mayor que cero")
        return v


class TelaCreate(TelaBase):
    pass


class TelaUpdate(TelaBase):
    pass


class TelaOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    color: Optional[str] = None
    composicion: Optional[str] = None
    ancho_m: Decimal
    m_por_rollo: Decimal
    categoria: Optional[CategoriaTelaOut] = None
    proveedor: Optional[ProveedorOut] = None

    class Config:
        from_attributes = True
