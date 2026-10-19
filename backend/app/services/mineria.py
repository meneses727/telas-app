"""Módulo de minería de datos (sección 9 del documento de contexto).

Calcula, a partir del historial de ventas:
- Índice estacional por mes y por tela (1.0 = demanda promedio de esa tela).
- Clasificación de demanda por tela (Baja / Media / Alta) vía K-Means,
  comparando el nivel de ventas recientes entre todas las telas.
- Demanda relativa (Normal / Alta): ventas recientes frente a lo esperado
  según el índice estacional del mes actual.
- Tendencia (Estable / Ascendente): variación de ventas recientes combinada
  con la percepción del planificador (escala 1-5).

Estos resultados son las tres variables de entrada del motor Mamdani
(cobertura se calcula aparte, a partir del inventario).
"""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
from sklearn.cluster import KMeans
from sqlalchemy.orm import Session

from app.models.importacion import VentaHistorica
from app.models.mineria import IndiceEstacional, ClasificacionDemanda, EvaluacionExperta
from app.models.tela import Tela

VENTANA_RECIENTE_DIAS = 30
VENTANA_PREVIA_DIAS = 30
UMBRAL_DEMANDA_ALTA = Decimal("1.3")  # ratio ventas reales / esperadas
UMBRAL_TENDENCIA_ASCENDENTE = 0.15  # score combinado (ver `tendencia`)


def _ventas_de(db: Session, tela_id: int) -> list[VentaHistorica]:
    return db.query(VentaHistorica).filter(VentaHistorica.tela_id == tela_id).all()


def calcular_indice_estacional(db: Session, tela_id: int) -> dict[int, float]:
    """Recalcula y persiste el índice estacional (1-12) de una tela.

    índice[mes] = promedio de ventas de ese mes / promedio general de ventas.
    Si no hay suficiente historial (menos de 2 meses distintos con ventas),
    se asume índice neutro (1.0) para todos los meses.
    """
    ventas = _ventas_de(db, tela_id)

    db.query(IndiceEstacional).filter(IndiceEstacional.tela_id == tela_id).delete()

    if not ventas:
        indices = {mes: 1.0 for mes in range(1, 13)}
    else:
        por_mes: dict[int, list[float]] = defaultdict(list)
        for v in ventas:
            por_mes[v.fecha.month].append(float(v.metros))

        promedio_general = sum(float(v.metros) for v in ventas) / len(ventas)
        meses_con_datos = len(por_mes)

        if meses_con_datos < 2 or promedio_general == 0:
            indices = {mes: 1.0 for mes in range(1, 13)}
        else:
            indices = {}
            for mes in range(1, 13):
                if mes in por_mes:
                    promedio_mes = sum(por_mes[mes]) / len(por_mes[mes])
                    indices[mes] = round(promedio_mes / promedio_general, 3)
                else:
                    indices[mes] = 1.0

    for mes, indice in indices.items():
        db.add(IndiceEstacional(tela_id=tela_id, mes=mes, indice=Decimal(str(indice))))
    db.commit()
    return indices


def clasificar_demanda_todas(db: Session, fecha_referencia: date | None = None) -> dict[int, str]:
    """Clasifica la demanda reciente de TODAS las telas con K-Means (Baja/Media/Alta).

    El clustering compara el total de metros vendidos en los últimos
    `VENTANA_RECIENTE_DIAS` días entre telas, porque "alta" o "baja" demanda
    solo tiene sentido en relación a las demás telas del catálogo.
    """
    fecha_referencia = fecha_referencia or date.today()
    desde = fecha_referencia - timedelta(days=VENTANA_RECIENTE_DIAS)

    telas = db.query(Tela).all()
    totales: dict[int, float] = {}
    for tela in telas:
        total = (
            db.query(VentaHistorica)
            .filter(
                VentaHistorica.tela_id == tela.id,
                VentaHistorica.fecha >= desde,
                VentaHistorica.fecha <= fecha_referencia,
            )
            .all()
        )
        totales[tela.id] = sum(float(v.metros) for v in total)

    resultado: dict[int, str] = {}
    telas_con_ventas = {tid: val for tid, val in totales.items() if val > 0}

    if len(telas_con_ventas) < 3:
        # Sin suficiente variedad para 3 clústeres: clasificación simple por valor.
        for tid in totales:
            resultado[tid] = "media" if totales[tid] > 0 else "baja"
    else:
        ids = list(telas_con_ventas.keys())
        X = np.array([[telas_con_ventas[tid]] for tid in ids])
        n_clusters = min(3, len(ids))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit(X)

        # Ordena los clústeres por su centroide para asignar las etiquetas
        # Baja/Media/Alta de forma consistente (K-Means no las ordena solo).
        centroides = kmeans.cluster_centers_.flatten()
        orden = np.argsort(centroides)
        etiquetas_por_cluster = {}
        nombres = ["baja", "media", "alta"][:n_clusters]
        for posicion, cluster_idx in enumerate(orden):
            etiquetas_por_cluster[cluster_idx] = nombres[posicion]

        for idx, tid in enumerate(ids):
            resultado[tid] = etiquetas_por_cluster[kmeans.labels_[idx]]

        for tid in totales:
            if tid not in resultado:
                resultado[tid] = "baja"

    for tid, clase in resultado.items():
        db.add(ClasificacionDemanda(tela_id=tid, clase=clase))
    db.commit()
    return resultado


def demanda_relativa(db: Session, tela_id: int, fecha_referencia: date | None = None) -> dict:
    """Compara las ventas recientes contra lo esperado según el índice estacional.

    ratio = ventas reales en la ventana reciente / ventas esperadas
            (promedio histórico mensual del mes actual * índice estacional de ese mes)
    """
    fecha_referencia = fecha_referencia or date.today()
    desde = fecha_referencia - timedelta(days=VENTANA_RECIENTE_DIAS)

    ventas_recientes = (
        db.query(VentaHistorica)
        .filter(
            VentaHistorica.tela_id == tela_id,
            VentaHistorica.fecha >= desde,
            VentaHistorica.fecha <= fecha_referencia,
        )
        .all()
    )
    total_reciente = sum(float(v.metros) for v in ventas_recientes)

    todas = _ventas_de(db, tela_id)
    if not todas:
        return {"ratio": None, "categoria": "Normal", "motivo": "Sin historial de ventas"}

    # Promedio mensual histórico = total vendido / meses equivalentes que cubre
    # el historial (no el promedio por transacción, que subestimaría el total
    # si hay varias ventas registradas dentro del mismo mes).
    total_historico = sum(float(v.metros) for v in todas)
    fechas = [v.fecha for v in todas]
    rango_dias = (max(fechas) - min(fechas)).days + 1
    meses_equivalentes = max(rango_dias / 30.0, 1.0)
    promedio_mensual_historico = (total_historico / meses_equivalentes) * (VENTANA_RECIENTE_DIAS / 30.0)

    indice_mes = (
        db.query(IndiceEstacional)
        .filter(IndiceEstacional.tela_id == tela_id, IndiceEstacional.mes == fecha_referencia.month)
        .first()
    )
    factor_estacional = float(indice_mes.indice) if indice_mes else 1.0

    esperado = promedio_mensual_historico * factor_estacional
    if esperado <= 0:
        return {"ratio": None, "categoria": "Normal", "motivo": "Demanda esperada no calculable"}

    ratio = round(total_reciente / esperado, 3)
    categoria = "Alta" if Decimal(str(ratio)) >= UMBRAL_DEMANDA_ALTA else "Normal"
    return {"ratio": ratio, "categoria": categoria, "total_reciente": total_reciente, "esperado": round(esperado, 2)}


def tendencia(db: Session, tela_id: int, fecha_referencia: date | None = None) -> dict:
    """Combina la variación de ventas con la percepción del planificador (1-5).

    - variación = (ventas últimos 30 días - ventas 30 días previos) / ventas 30 días previos
    - percepción normalizada = (percepcion - 3) / 2  →  rango [-1, 1], 3 = neutro
    - score = 0.6 * variación (acotada a [-1, 1]) + 0.4 * percepción normalizada
    - "Ascendente" si score > UMBRAL_TENDENCIA_ASCENDENTE, si no "Estable"
    """
    fecha_referencia = fecha_referencia or date.today()
    fin_reciente = fecha_referencia
    inicio_reciente = fin_reciente - timedelta(days=VENTANA_RECIENTE_DIAS)
    inicio_previo = inicio_reciente - timedelta(days=VENTANA_PREVIA_DIAS)

    def _total_en_rango(desde: date, hasta: date) -> float:
        ventas = (
            db.query(VentaHistorica)
            .filter(VentaHistorica.tela_id == tela_id, VentaHistorica.fecha > desde, VentaHistorica.fecha <= hasta)
            .all()
        )
        return sum(float(v.metros) for v in ventas)

    reciente = _total_en_rango(inicio_reciente, fin_reciente)
    previo = _total_en_rango(inicio_previo, inicio_reciente)

    if previo > 0:
        variacion = (reciente - previo) / previo
    elif reciente > 0:
        variacion = 1.0  # pasó de no vender nada a vender: variación máxima
    else:
        variacion = 0.0
    variacion_acotada = max(-1.0, min(1.0, variacion))

    ultima_evaluacion = (
        db.query(EvaluacionExperta)
        .filter(EvaluacionExperta.tela_id == tela_id)
        .order_by(EvaluacionExperta.fecha.desc())
        .first()
    )
    percepcion = ultima_evaluacion.percepcion if ultima_evaluacion else 3
    percepcion_normalizada = (percepcion - 3) / 2

    score = 0.6 * variacion_acotada + 0.4 * percepcion_normalizada
    categoria = "Ascendente" if score > UMBRAL_TENDENCIA_ASCENDENTE else "Estable"

    return {
        "variacion_ventas": round(variacion_acotada, 3),
        "percepcion_planificador": percepcion,
        "score": round(score, 3),
        "categoria": categoria,
    }
