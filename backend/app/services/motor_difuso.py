"""Motor de inferencia difusa Mamdani (sección 9 del documento de contexto).

Las funciones de pertenencia y la base de reglas se leen de la base de datos
(tablas `variables_linguisticas`, `conjuntos_difusos`, `reglas_difusas`) para
que la jefa de planificación pueda ajustarlas sin tocar código. El seed
(`app/seed_difuso.py`) carga un borrador inicial de 12 reglas, pendiente de
validación con ella (ver la conversación de diseño: Cobertura 3 conjuntos,
Demanda relativa 2, Tendencia 2 → 3×2×2 = 12 reglas).

Pasos del método Mamdani implementados:
1. Fuzzificación: convierte cada entrada numérica en grados de pertenencia
   (0 a 1) a cada conjunto difuso de su variable, usando funciones
   trapezoidales/triangulares (a,b,c,d).
2. Inferencia: para cada regla, el grado de activación es el mínimo (AND)
   entre los grados de pertenencia de sus tres antecedentes, multiplicado
   por el peso de la regla.
3. Agregación: para cada etiqueta de salida (Baja/Media/Alta), se agregan
   (máximo) las activaciones de todas las reglas que concluyen en ella.
4. Defuzzificación por centroide: se combina (máximo) el conjunto de salida
   recortado por su grado agregado, y se calcula el centroide numérico de
   esa función resultante sobre el universo de discurso de "reposición" (0-100%).
"""
from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session

from app.models.motor_difuso import VariableLinguistica, ConjuntoDifuso, ReglaDifusa

PASOS_UNIVERSO_SALIDA = 500  # resolución de la discretización para el centroide


def grado_pertenencia_trapezoidal(x: float, a: float, b: float, c: float, d: float) -> float:
    """Función de pertenencia trapezoidal (triangular si b == c).

    a----b====c----d
    0    1    1    0   (sube de a a b, se mantiene de b a c, baja de c a d)
    """
    if x <= a or x >= d:
        return 0.0
    if b <= x <= c:
        return 1.0
    if a < x < b:
        return (x - a) / (b - a) if b != a else 1.0
    if c < x < d:
        return (d - x) / (d - c) if d != c else 1.0
    return 0.0


def cargar_variable(db: Session, nombre_variable: str) -> VariableLinguistica:
    variable = db.query(VariableLinguistica).filter(VariableLinguistica.nombre == nombre_variable).first()
    if variable is None:
        raise ValueError(f"Variable lingüística '{nombre_variable}' no está configurada")
    return variable


def cargar_conjuntos(db: Session, nombre_variable: str) -> list[ConjuntoDifuso]:
    variable = cargar_variable(db, nombre_variable)
    return db.query(ConjuntoDifuso).filter(ConjuntoDifuso.variable_id == variable.id).all()


def _acotar_al_universo(db: Session, nombre_variable: str, valor: float) -> float:
    """Recorta el valor crudo al universo de discurso [mínimo, máximo] de la variable.

    Sin esto, un valor extremo (p. ej. una tela con muchísimo exceso de stock)
    podría caer fuera del último conjunto difuso (cuyo trapecio termina en un
    punto 'd' finito) y dar grado de pertenencia 0 en TODO, generando un falso
    "no concluyente" — ese estado debe reservarse para cuando falta información
    (sin ventas, sin inventario), no para valores simplemente muy altos/bajos.
    """
    variable = cargar_variable(db, nombre_variable)
    return max(float(variable.minimo), min(float(variable.maximo), valor))


def fuzzificar(db: Session, nombre_variable: str, valor: float) -> dict[str, float]:
    valor = _acotar_al_universo(db, nombre_variable, valor)
    conjuntos = cargar_conjuntos(db, nombre_variable)
    return {
        c.etiqueta: round(
            grado_pertenencia_trapezoidal(valor, float(c.a), float(c.b), float(c.c), float(c.d)), 4
        )
        for c in conjuntos
    }


@dataclass
class ReglaActivada:
    codigo: str
    cobertura: str
    demanda: str
    tendencia: str
    reposicion: str
    grado_activacion: float


def evaluar_reglas(
    db: Session,
    grados_cobertura: dict[str, float],
    grados_demanda: dict[str, float],
    grados_tendencia: dict[str, float],
) -> list[ReglaActivada]:
    reglas = db.query(ReglaDifusa).filter(ReglaDifusa.activa.is_(True)).all()
    activadas = []
    for r in reglas:
        g_cob = grados_cobertura.get(r.cobertura, 0.0)
        g_dem = grados_demanda.get(r.demanda_relativa, 0.0)
        g_ten = grados_tendencia.get(r.tendencia, 0.0)
        grado = min(g_cob, g_dem, g_ten) * float(r.peso)
        if grado > 0:
            activadas.append(
                ReglaActivada(
                    codigo=r.codigo,
                    cobertura=r.cobertura,
                    demanda=r.demanda_relativa,
                    tendencia=r.tendencia,
                    reposicion=r.reposicion,
                    grado_activacion=round(grado, 4),
                )
            )
    return sorted(activadas, key=lambda x: x.grado_activacion, reverse=True)


def defuzzificar_centroide(db: Session, reglas_activadas: list[ReglaActivada]) -> float | None:
    """Centroide de la función de pertenencia agregada de 'reposición'.

    Devuelve None si ninguna regla se activó (caso "no concluyente").
    """
    if not reglas_activadas:
        return None

    conjuntos_salida = cargar_conjuntos(db, "reposicion")
    if not conjuntos_salida:
        raise ValueError("Variable de salida 'reposicion' no está configurada")

    universo_min = min(float(c.a) for c in conjuntos_salida)
    universo_max = max(float(c.d) for c in conjuntos_salida)
    xs = np.linspace(universo_min, universo_max, PASOS_UNIVERSO_SALIDA)

    # Grado agregado (máximo) por etiqueta de salida, entre todas las reglas que la concluyen.
    grado_por_etiqueta: dict[str, float] = {}
    for regla in reglas_activadas:
        actual = grado_por_etiqueta.get(regla.reposicion, 0.0)
        grado_por_etiqueta[regla.reposicion] = max(actual, regla.grado_activacion)

    mu_agregada = np.zeros_like(xs)
    for conjunto in conjuntos_salida:
        grado = grado_por_etiqueta.get(conjunto.etiqueta, 0.0)
        if grado <= 0:
            continue
        mu_conjunto = np.array(
            [
                grado_pertenencia_trapezoidal(
                    x, float(conjunto.a), float(conjunto.b), float(conjunto.c), float(conjunto.d)
                )
                for x in xs
            ]
        )
        mu_recortada = np.minimum(mu_conjunto, grado)  # recorte por el grado de activación
        mu_agregada = np.maximum(mu_agregada, mu_recortada)

    area = mu_agregada.sum()
    if area == 0:
        return None
    centroide = float((xs * mu_agregada).sum() / area)
    return round(centroide, 2)


def generar_recomendacion(
    db: Session, cobertura_dias: float, demanda_ratio: float, tendencia_score: float
) -> dict:
    """Ejecuta el pipeline Mamdani completo para una tela y devuelve el detalle
    necesario tanto para calcular metros/rollos (paso siguiente) como para
    explicar el resultado al planificador (pantalla de recomendación)."""
    grados_cobertura = fuzzificar(db, "cobertura", cobertura_dias)
    grados_demanda = fuzzificar(db, "demanda_relativa", demanda_ratio)
    grados_tendencia = fuzzificar(db, "tendencia", tendencia_score)

    reglas_activadas = evaluar_reglas(db, grados_cobertura, grados_demanda, grados_tendencia)
    pct_reposicion = defuzzificar_centroide(db, reglas_activadas)

    return {
        "grados_cobertura": grados_cobertura,
        "grados_demanda": grados_demanda,
        "grados_tendencia": grados_tendencia,
        "reglas_activadas": [
            {
                "codigo": r.codigo,
                "condiciones": f"SI cobertura={r.cobertura} Y demanda={r.demanda} Y tendencia={r.tendencia}",
                "conclusion": r.reposicion,
                "grado_activacion": r.grado_activacion,
            }
            for r in reglas_activadas
        ],
        "pct_reposicion": pct_reposicion,
        "no_concluyente": pct_reposicion is None,
    }
