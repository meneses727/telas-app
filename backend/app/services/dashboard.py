"""Panel de control / dashboard (pantalla 10.2).

Calcula, para el catálogo completo (o el subconjunto filtrado):
- Rotación de inventario promedio (veces/año).
- Cobertura promedio (días).
- Alertas: telas en riesgo de desabastecimiento (cobertura Crítica) y
  telas en riesgo de sobrestock (cobertura en Exceso).
- Tabla de cobertura por tela, con estado y la acción sugerida.

Los cortes Crítica/Adecuada/Exceso usados aquí son una clasificación nítida
(para mostrar un estado único por tela en la tabla), distinta de los grados
difusos del motor Mamdani (que sí permiten pertenencia parcial a varios
conjuntos a la vez). Se alinean con los mismos puntos de corte cargados en
`seed_difuso.py` para no mostrarle al planificador dos nociones distintas
de "crítico".
"""
from datetime import date

from sqlalchemy.orm import Session, joinedload

from app.models.tela import Tela
from app.services.recomendacion import cobertura_dias_tela

DIAS_COBERTURA_CRITICA = 15  # coincide con el punto 'd' del conjunto Crítica
DIAS_COBERTURA_EXCESO = 35  # coincide con el punto 'a' del conjunto Exceso
DIAS_ANIO = 365


def _estado_por_cobertura(cobertura_dias: float | None) -> str:
    if cobertura_dias is None:
        return "Sin datos"
    if cobertura_dias == float("inf") or cobertura_dias >= DIAS_COBERTURA_EXCESO:
        return "Exceso"
    if cobertura_dias <= DIAS_COBERTURA_CRITICA:
        return "Crítica"
    return "Adecuada"


def _accion_para_estado(estado: str) -> str:
    return {
        "Crítica": "Sugerir compra",
        "Sin datos": "Sugerir compra",
    }.get(estado, "Ver recomendación")


def obtener_resumen(
    db: Session,
    categoria_id: int | None = None,
    color: str | None = None,
    estado: str | None = None,
    fecha_referencia: date | None = None,
) -> dict:
    fecha_referencia = fecha_referencia or date.today()

    query = db.query(Tela).options(joinedload(Tela.categoria), joinedload(Tela.proveedor))
    if categoria_id is not None:
        query = query.filter(Tela.categoria_id == categoria_id)
    if color:
        query = query.filter(Tela.color.ilike(f"%{color.strip()}%"))
    telas = query.order_by(Tela.nombre).all()

    filas = []
    coberturas_validas: list[float] = []
    rotaciones_validas: list[float] = []
    conteo_alertas = {"Crítica": 0, "Exceso": 0}

    for tela in telas:
        info = cobertura_dias_tela(db, tela.id, fecha_referencia)
        cobertura = info["cobertura_dias"]
        estado_tela = _estado_por_cobertura(cobertura)

        if cobertura is not None and cobertura != float("inf"):
            coberturas_validas.append(cobertura)
        if info["stock_actual"] and info["stock_actual"] > 0 and info["consumo_diario"]:
            rotaciones_validas.append((info["consumo_diario"] * DIAS_ANIO) / info["stock_actual"])

        if estado_tela in conteo_alertas:
            conteo_alertas[estado_tela] += 1

        filas.append(
            {
                "tela_id": tela.id,
                "codigo": tela.codigo,
                "nombre": tela.nombre,
                "color": tela.color,
                "categoria": tela.categoria.nombre if tela.categoria else None,
                "cobertura_dias": round(cobertura, 1) if cobertura not in (None, float("inf")) else cobertura,
                "estado": estado_tela,
                "accion": _accion_para_estado(estado_tela),
            }
        )

    if estado:
        filas = [f for f in filas if f["estado"].lower() == estado.strip().lower()]

    cobertura_promedio = round(sum(coberturas_validas) / len(coberturas_validas), 1) if coberturas_validas else None
    rotacion_promedio = round(sum(rotaciones_validas) / len(rotaciones_validas), 2) if rotaciones_validas else None

    return {
        "fecha_referencia": fecha_referencia,
        "rotacion_inventario_anual": rotacion_promedio,
        "cobertura_promedio_dias": cobertura_promedio,
        "alertas": {
            "criticas": conteo_alertas["Crítica"],
            "exceso": conteo_alertas["Exceso"],
        },
        "telas": filas,
    }
