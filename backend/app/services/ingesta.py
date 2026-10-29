"""Validación e importación de archivos de ventas e inventario (CSV/XLSX).

Reglas (sección 10.3 del documento de contexto):
- El archivo debe tener las columnas esperadas según el tipo.
- Cada fila se valida de forma independiente; las filas inválidas no bloquean
  la importación de las válidas.
- El código de tela debe existir en el catálogo (tabla `telas`).
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation

import pandas as pd
from sqlalchemy.orm import Session

from app.models.tela import Tela
from app.models.importacion import VentaHistorica, InventarioSnapshot

COLUMNAS_VENTAS = {"codigo_tela", "fecha", "metros"}
COLUMNAS_INVENTARIO = {"codigo_tela", "fecha_corte", "stock_metros"}

TAMANO_MAXIMO_MB = 10


@dataclass
class ErrorFila:
    fila: int
    motivo: str


@dataclass
class ResultadoValidacion:
    filas_totales: int
    registros_validos: list = field(default_factory=list)
    errores: list[ErrorFila] = field(default_factory=list)

    @property
    def filas_validas(self) -> int:
        return len(self.registros_validos)

    @property
    def filas_con_error(self) -> int:
        return len(self.errores)


def leer_dataframe(contenido: bytes, nombre_archivo: str) -> pd.DataFrame:
    nombre = nombre_archivo.lower()
    if nombre.endswith(".csv"):
        import io

        return pd.read_csv(io.BytesIO(contenido), dtype=str, keep_default_na=False)
    if nombre.endswith(".xlsx") or nombre.endswith(".xls"):
        import io

        return pd.read_excel(io.BytesIO(contenido), dtype=str)
    raise ValueError("Formato de archivo no soportado. Usa CSV o Excel (.xlsx).")


def _parsear_fecha(valor: str):
    valor = (valor or "").strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(valor, formato).date()
        except ValueError:
            continue
    return None


def _parsear_decimal(valor: str):
    try:
        d = Decimal((valor or "").strip().replace(",", "."))
        return d
    except (InvalidOperation, AttributeError):
        return None


def validar_ventas(df: pd.DataFrame, db: Session) -> ResultadoValidacion:
    columnas = {c.strip().lower() for c in df.columns}
    faltantes = COLUMNAS_VENTAS - columnas
    if faltantes:
        raise ValueError(f"Faltan columnas requeridas: {', '.join(sorted(faltantes))}")

    df.columns = [c.strip().lower() for c in df.columns]
    telas_por_codigo = {t.codigo: t for t in db.query(Tela).all()}

    resultado = ResultadoValidacion(filas_totales=len(df))
    for idx, fila in df.iterrows():
        num_fila = idx + 2  # +1 por índice 0-based, +1 por la fila de encabezado
        codigo = (fila.get("codigo_tela") or "").strip().upper()
        if not codigo:
            resultado.errores.append(ErrorFila(num_fila, "El código de tela está vacío"))
            continue
        tela = telas_por_codigo.get(codigo)
        if tela is None:
            resultado.errores.append(ErrorFila(num_fila, f"La tela '{codigo}' no está en el catálogo"))
            continue

        fecha = _parsear_fecha(fila.get("fecha"))
        if fecha is None:
            resultado.errores.append(ErrorFila(num_fila, "Fecha inválida (usa AAAA-MM-DD)"))
            continue

        metros = _parsear_decimal(fila.get("metros"))
        if metros is None or metros <= 0:
            resultado.errores.append(ErrorFila(num_fila, "Metros debe ser un número positivo"))
            continue

        cliente_tipo = (fila.get("cliente_tipo") or "").strip() or None

        resultado.registros_validos.append(
            VentaHistorica(tela_id=tela.id, fecha=fecha, metros=metros, cliente_tipo=cliente_tipo)
        )

    return resultado


def validar_inventario(df: pd.DataFrame, db: Session) -> ResultadoValidacion:
    columnas = {c.strip().lower() for c in df.columns}
    faltantes = COLUMNAS_INVENTARIO - columnas
    if faltantes:
        raise ValueError(f"Faltan columnas requeridas: {', '.join(sorted(faltantes))}")

    df.columns = [c.strip().lower() for c in df.columns]
    telas_por_codigo = {t.codigo: t for t in db.query(Tela).all()}

    resultado = ResultadoValidacion(filas_totales=len(df))
    for idx, fila in df.iterrows():
        num_fila = idx + 2
        codigo = (fila.get("codigo_tela") or "").strip().upper()
        if not codigo:
            resultado.errores.append(ErrorFila(num_fila, "El código de tela está vacío"))
            continue
        tela = telas_por_codigo.get(codigo)
        if tela is None:
            resultado.errores.append(ErrorFila(num_fila, f"La tela '{codigo}' no está en el catálogo"))
            continue

        fecha_corte = _parsear_fecha(fila.get("fecha_corte"))
        if fecha_corte is None:
            resultado.errores.append(ErrorFila(num_fila, "Fecha de corte inválida (usa AAAA-MM-DD)"))
            continue

        stock = _parsear_decimal(fila.get("stock_metros"))
        if stock is None or stock < 0:
            resultado.errores.append(ErrorFila(num_fila, "Stock en metros debe ser un número válido (>= 0)"))
            continue

        rollos_raw = _texto_opcional(fila.get("rollos"))
        rollos = None
        if rollos_raw:
            try:
                rollos = int(rollos_raw)
            except ValueError:
                resultado.errores.append(ErrorFila(num_fila, "Rollos debe ser un número entero"))
                continue

        transito_raw = _texto_opcional(fila.get("en_transito_metros"))
        en_transito = Decimal("0")
        if transito_raw:
            en_transito = _parsear_decimal(transito_raw)
            if en_transito is None or en_transito < 0:
                resultado.errores.append(ErrorFila(num_fila, "En tránsito debe ser un número válido (>= 0)"))
                continue

        resultado.registros_validos.append(
            InventarioSnapshot(
                tela_id=tela.id, fecha_corte=fecha_corte, stock_metros=stock, rollos=rollos,
                en_transito_metros=en_transito,
            )
        )

    return resultado


def _texto_opcional(valor) -> str:
    """Celda opcional como texto; vacía si falta o si Excel la dejó como NaN."""
    if valor is None:
        return ""
    texto = str(valor).strip()
    return "" if texto.lower() == "nan" else texto
