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

from app.models.tela import Tela, Proveedor, CategoriaTela
from app.models.importacion import VentaHistorica, InventarioSnapshot  # noqa: F401  (tablas destino)

COLUMNAS_VENTAS = {"codigo_tela", "fecha", "metros"}
COLUMNAS_INVENTARIO = {"codigo_tela", "fecha_corte", "stock_metros"}
COLUMNAS_CATALOGO = {"codigo_tela", "nombre", "metros_por_rollo"}
ANCHO_DEFECTO_M = Decimal("1.50")

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
    # Una celda de fecha de Excel leída como texto llega como "2025-11-01 00:00:00".
    for formato in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d-%m-%Y"):
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
    # Se recorre como lista de diccionarios y se guardan diccionarios (no objetos
    # del ORM): con decenas de miles de filas, el servidor gratuito se queda sin memoria.
    for idx, fila in enumerate(df.to_dict("records")):
        num_fila = idx + 2  # +1 por índice 0-based, +1 por la fila de encabezado
        codigo = _texto_opcional(fila.get("codigo_tela")).upper()
        if not codigo:
            resultado.errores.append(ErrorFila(num_fila, "El código de tela está vacío"))
            continue
        tela = telas_por_codigo.get(codigo)
        if tela is None:
            resultado.errores.append(ErrorFila(num_fila, f"La tela '{codigo}' no está en el catálogo"))
            continue

        fecha = _parsear_fecha(_texto_opcional(fila.get("fecha")))
        if fecha is None:
            resultado.errores.append(ErrorFila(num_fila, "Fecha inválida (usa AAAA-MM-DD)"))
            continue

        metros = _parsear_decimal(_texto_opcional(fila.get("metros")))
        if metros is None or metros <= 0:
            resultado.errores.append(ErrorFila(num_fila, "Metros debe ser un número positivo"))
            continue

        cliente_tipo = _texto_opcional(fila.get("cliente_tipo")) or None

        resultado.registros_validos.append(
            {"tela_id": tela.id, "fecha": fecha, "metros": metros, "cliente_tipo": cliente_tipo}
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
    for idx, fila in enumerate(df.to_dict("records")):
        num_fila = idx + 2
        codigo = _texto_opcional(fila.get("codigo_tela")).upper()
        if not codigo:
            resultado.errores.append(ErrorFila(num_fila, "El código de tela está vacío"))
            continue
        tela = telas_por_codigo.get(codigo)
        if tela is None:
            resultado.errores.append(ErrorFila(num_fila, f"La tela '{codigo}' no está en el catálogo"))
            continue

        fecha_corte = _parsear_fecha(_texto_opcional(fila.get("fecha_corte")))
        if fecha_corte is None:
            resultado.errores.append(ErrorFila(num_fila, "Fecha de corte inválida (usa AAAA-MM-DD)"))
            continue

        stock = _parsear_decimal(_texto_opcional(fila.get("stock_metros")))
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

        resultado.registros_validos.append({
            "tela_id": tela.id, "fecha_corte": fecha_corte, "stock_metros": stock, "rollos": rollos,
            "en_transito_metros": en_transito,
        })

    return resultado


def validar_catalogo(df: pd.DataFrame, db: Session) -> ResultadoValidacion:
    """Catálogo de telas: un código por tipo de tela y color/diseño.

    Columnas requeridas: codigo_tela, nombre, metros_por_rollo.
    Opcionales: tipo_tela, color, proveedor, plazo_entrega_dias, ancho_m.
    Cada fila válida se devuelve como un diccionario; `aplicar_catalogo` crea
    o actualiza la tela, su tipo (categoría) y su proveedor con su plazo.
    """
    columnas = {c.strip().lower() for c in df.columns}
    faltantes = COLUMNAS_CATALOGO - columnas
    if faltantes:
        raise ValueError(f"Faltan columnas requeridas: {', '.join(sorted(faltantes))}")
    df.columns = [c.strip().lower() for c in df.columns]

    resultado = ResultadoValidacion(filas_totales=len(df))
    vistos = set()
    for idx, fila in enumerate(df.to_dict("records")):
        num_fila = idx + 2
        codigo = _texto_opcional(fila.get("codigo_tela")).upper()
        if not codigo:
            resultado.errores.append(ErrorFila(num_fila, "El código de tela está vacío"))
            continue
        if len(codigo) > 30:
            resultado.errores.append(ErrorFila(num_fila, "El código de tela tiene más de 30 caracteres"))
            continue
        if codigo in vistos:
            resultado.errores.append(ErrorFila(num_fila, f"El código '{codigo}' está repetido en el archivo"))
            continue
        nombre = _texto_opcional(fila.get("nombre"))
        if not nombre:
            resultado.errores.append(ErrorFila(num_fila, "El nombre de la tela está vacío"))
            continue
        m_rollo = _parsear_decimal(_texto_opcional(fila.get("metros_por_rollo")))
        if m_rollo is None or m_rollo <= 0:
            resultado.errores.append(ErrorFila(num_fila, "Metros por rollo debe ser un número positivo"))
            continue
        ancho = ANCHO_DEFECTO_M
        ancho_raw = _texto_opcional(fila.get("ancho_m"))
        if ancho_raw:
            ancho = _parsear_decimal(ancho_raw)
            if ancho is None or ancho <= 0:
                resultado.errores.append(ErrorFila(num_fila, "El ancho debe ser un número positivo"))
                continue
        proveedor = _texto_opcional(fila.get("proveedor"))
        plazo = None
        plazo_raw = _texto_opcional(fila.get("plazo_entrega_dias"))
        if plazo_raw:
            try:
                plazo = int(float(plazo_raw))
            except ValueError:
                plazo = None
            if plazo is None or plazo <= 0:
                resultado.errores.append(ErrorFila(num_fila, "El plazo de entrega debe ser un número de días positivo"))
                continue
            if not proveedor:
                resultado.errores.append(ErrorFila(num_fila, "Indica el proveedor al que corresponde el plazo de entrega"))
                continue

        vistos.add(codigo)
        resultado.registros_validos.append({
            "codigo": codigo,
            "nombre": nombre,
            "tipo_tela": _texto_opcional(fila.get("tipo_tela")) or None,
            "color": _texto_opcional(fila.get("color")) or None,
            "proveedor": proveedor or None,
            "plazo": plazo,
            "m_por_rollo": m_rollo,
            "ancho_m": ancho,
        })
    return resultado


def aplicar_catalogo(db: Session, filas: list[dict]) -> None:
    proveedores = {p.nombre.lower(): p for p in db.query(Proveedor).all()}
    categorias = {c.nombre.lower(): c for c in db.query(CategoriaTela).all()}
    telas = {t.codigo: t for t in db.query(Tela).all()}
    for f in filas:
        proveedor = None
        if f["proveedor"]:
            proveedor = proveedores.get(f["proveedor"].lower())
            if proveedor is None:
                proveedor = Proveedor(nombre=f["proveedor"], lead_time_dias=f["plazo"] or 60)
                db.add(proveedor)
                db.flush()
                proveedores[f["proveedor"].lower()] = proveedor
            elif f["plazo"]:
                proveedor.lead_time_dias = f["plazo"]
        categoria = None
        if f["tipo_tela"]:
            categoria = categorias.get(f["tipo_tela"].lower())
            if categoria is None:
                categoria = CategoriaTela(nombre=f["tipo_tela"])
                db.add(categoria)
                db.flush()
                categorias[f["tipo_tela"].lower()] = categoria
        tela = telas.get(f["codigo"])
        if tela is None:
            tela = Tela(codigo=f["codigo"])
            db.add(tela)
            telas[f["codigo"]] = tela
        tela.nombre = f["nombre"]
        tela.color = f["color"]
        tela.m_por_rollo = f["m_por_rollo"]
        tela.ancho_m = f["ancho_m"]
        if categoria is not None:
            tela.categoria_id = categoria.id
        if proveedor is not None:
            tela.proveedor_id = proveedor.id


def _texto_opcional(valor) -> str:
    """Celda opcional como texto; vacía si falta o si Excel la dejó como NaN."""
    if valor is None:
        return ""
    texto = str(valor).strip()
    return "" if texto.lower() == "nan" else texto
