"""Servicio de recomendación de compra (sección 9 y pantalla 10.5).

Integra:
  cobertura (de inventario + consumo) + demanda relativa y tendencia
  (del módulo de minería, `app/services/mineria.py`)
  → motor Mamdani (`app/services/motor_difuso.py`)
  → conversión del % de reposición a metros y rollos a pedir.
"""
import math
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.importacion import VentaHistorica, InventarioSnapshot
from app.models.tela import Tela
from app.services import mineria as servicio_mineria
from app.services import motor_difuso as servicio_motor

VENTANA_CONSUMO_DIAS = 30


def _consumo_diario_promedio(db: Session, tela_id: int, fecha_referencia: date) -> float:
    desde = fecha_referencia - timedelta(days=VENTANA_CONSUMO_DIAS)
    ventas = (
        db.query(VentaHistorica)
        .filter(
            VentaHistorica.tela_id == tela_id,
            VentaHistorica.fecha > desde,
            VentaHistorica.fecha <= fecha_referencia,
        )
        .all()
    )
    total = sum(float(v.metros) for v in ventas)
    return total / VENTANA_CONSUMO_DIAS


def _cobertura_dias(db: Session, tela_id: int, fecha_referencia: date) -> dict:
    snapshot = (
        db.query(InventarioSnapshot)
        .filter(InventarioSnapshot.tela_id == tela_id)
        .order_by(InventarioSnapshot.fecha_corte.desc())
        .first()
    )
    if snapshot is None:
        return {"cobertura_dias": None, "stock_actual": None, "consumo_diario": None,
                "motivo": "No hay un registro de inventario cargado para esta tela"}

    stock_actual = float(snapshot.stock_metros)
    en_transito = float(snapshot.en_transito_metros or 0)
    # Posición de inventario = disponible + ya pedido al proveedor. La cobertura
    # se mide sobre ella para no volver a pedir lo que ya está en camino.
    posicion = stock_actual + en_transito
    consumo_diario = _consumo_diario_promedio(db, tela_id, fecha_referencia)

    if consumo_diario <= 0:
        # Sin consumo reciente: la cobertura es efectivamente "sin límite" (mucho exceso)
        # si hay stock, o indefinida si tampoco hay stock.
        cobertura_dias = float("inf") if posicion > 0 else 0.0
    else:
        cobertura_dias = posicion / consumo_diario

    return {
        "cobertura_dias": cobertura_dias,
        "stock_actual": stock_actual,
        "en_transito": en_transito,
        "posicion_inventario": posicion,
        "consumo_diario": round(consumo_diario, 3),
        "motivo": None,
    }


def cobertura_dias_tela(db: Session, tela_id: int, fecha_referencia: date | None = None) -> dict:
    """Wrapper público de `_cobertura_dias`, para que otros módulos (p. ej. el
    dashboard) reutilicen el mismo cálculo sin duplicar la lógica."""
    return _cobertura_dias(db, tela_id, fecha_referencia or date.today())


def _cantidad_a_pedir(db: Session, pct_reposicion: float, info_cobertura: dict, m_por_rollo: float) -> tuple[float, int]:
    """Convierte el % de reposición del motor en metros y rollos (Sección 3.6).

    R* fija la cobertura objetivo como fracción del horizonte H (el máximo del
    universo de 'cobertura'): se pide lo que falta para que la posición de
    inventario alcance R*/100 · H días de consumo, redondeado a rollos enteros.
    """
    horizonte = float(servicio_motor.cargar_variable(db, "cobertura").maximo)
    objetivo = (pct_reposicion / 100.0) * horizonte * info_cobertura["consumo_diario"]
    metros = max(0.0, objetivo - info_cobertura["posicion_inventario"])
    rollos = math.ceil(metros / m_por_rollo) if metros > 0 else 0
    return metros, rollos


def generar_recomendacion_compra(db: Session, tela_id: int, fecha_referencia: date | None = None) -> dict:
    fecha_referencia = fecha_referencia or date.today()

    tela = db.query(Tela).filter(Tela.id == tela_id).first()
    if tela is None:
        raise ValueError("Tela no encontrada")

    info_cobertura = _cobertura_dias(db, tela_id, fecha_referencia)
    info_demanda = servicio_mineria.demanda_relativa(db, tela_id, fecha_referencia)
    info_tendencia = servicio_mineria.tendencia(db, tela_id, fecha_referencia)

    base = {
        "tela_id": tela.id,
        "tela_codigo": tela.codigo,
        "stock_actual_metros": info_cobertura["stock_actual"],
        "en_transito_metros": info_cobertura.get("en_transito"),
        "consumo_diario_promedio": info_cobertura["consumo_diario"],
        "cobertura_dias": (
            round(info_cobertura["cobertura_dias"], 1)
            if info_cobertura["cobertura_dias"] not in (None, float("inf"))
            else info_cobertura["cobertura_dias"]
        ),
        "demanda_relativa": info_demanda,
        "tendencia": info_tendencia,
    }

    # Casos en los que no hay suficiente información para que el motor concluya
    # algo con sentido (independientemente de que las reglas se activen o no).
    if info_cobertura["cobertura_dias"] is None:
        return {
            **base,
            "grados_cobertura": {}, "grados_demanda": {}, "grados_tendencia": {},
            "reglas_activadas": [], "pct_reposicion": None,
            "metros_sugeridos": None, "rollos_sugeridos": None,
            "no_concluyente": True, "motivo": info_cobertura["motivo"],
        }
    if info_demanda.get("ratio") is None:
        return {
            **base,
            "grados_cobertura": {}, "grados_demanda": {}, "grados_tendencia": {},
            "reglas_activadas": [], "pct_reposicion": None,
            "metros_sugeridos": None, "rollos_sugeridos": None,
            "no_concluyente": True, "motivo": info_demanda.get("motivo", "Sin historial de ventas"),
        }

    resultado_motor = servicio_motor.generar_recomendacion(
        db,
        cobertura_dias=info_cobertura["cobertura_dias"],
        demanda_ratio=info_demanda["ratio"],
        tendencia_score=info_tendencia["score"],
    )

    if resultado_motor["no_concluyente"]:
        return {
            **base,
            **resultado_motor,
            "metros_sugeridos": None, "rollos_sugeridos": None,
            "motivo": "Ninguna regla del motor se activó con estos valores",
        }

    metros_sugeridos, rollos_sugeridos = _cantidad_a_pedir(
        db, resultado_motor["pct_reposicion"], info_cobertura, float(tela.m_por_rollo)
    )

    return {
        **base,
        **resultado_motor,
        "metros_sugeridos": round(metros_sugeridos, 1),
        "rollos_sugeridos": rollos_sugeridos,
        "motivo": None,
    }


def generar_recomendacion_simulada(
    db: Session,
    tela_id: int,
    demanda_relativa_pct: float,
    tendencia_pct: float,
    fecha_referencia: date | None = None,
) -> dict:
    """Pantalla 10.6: recalcula la recomendación reemplazando la demanda
    relativa y la tendencia reales por los valores de los sliders del
    planificador (0%-200% y -50%/+50%). La cobertura NO se simula: sigue
    saliendo del inventario real, porque el slider del mockup solo cubre
    demanda y tendencia.

    100% de demanda = ratio 1.0 (la variable 'demanda_relativa' del motor
    usa esa misma escala). El % de tendencia se traduce directamente a la
    escala -1..1 del score (p. ej. -50% → -0.5).
    """
    fecha_referencia = fecha_referencia or date.today()

    tela = db.query(Tela).filter(Tela.id == tela_id).first()
    if tela is None:
        raise ValueError("Tela no encontrada")

    info_cobertura = _cobertura_dias(db, tela_id, fecha_referencia)
    if info_cobertura["cobertura_dias"] is None:
        raise ValueError(info_cobertura["motivo"])

    demanda_ratio_simulado = demanda_relativa_pct / 100.0
    tendencia_score_simulado = tendencia_pct / 100.0

    resultado_motor = servicio_motor.generar_recomendacion(
        db,
        cobertura_dias=info_cobertura["cobertura_dias"],
        demanda_ratio=demanda_ratio_simulado,
        tendencia_score=tendencia_score_simulado,
    )

    if resultado_motor["no_concluyente"]:
        return {
            "tela_id": tela.id, "tela_codigo": tela.codigo,
            **resultado_motor,
            "metros_sugeridos": None, "rollos_sugeridos": None,
        }

    metros_sugeridos, rollos_sugeridos = _cantidad_a_pedir(
        db, resultado_motor["pct_reposicion"], info_cobertura, float(tela.m_por_rollo)
    )

    return {
        "tela_id": tela.id, "tela_codigo": tela.codigo,
        **resultado_motor,
        "metros_sugeridos": round(metros_sugeridos, 1),
        "rollos_sugeridos": rollos_sugeridos,
    }
