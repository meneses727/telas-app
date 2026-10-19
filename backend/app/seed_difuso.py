"""Carga inicial del motor difuso: variables, conjuntos y la base de reglas.

IMPORTANTE: la base de 12 reglas cargada aquí es un BORRADOR propuesto con
lógica estándar de gestión de inventarios (cobertura crítica → siempre
reponer; exceso → casi nunca reponer salvo demanda alta y ascendente a la
vez). Falta validarla con la jefa de planificación de Corporación Textil
Montalvan antes de usarla para decisiones reales. El diseño es:
  - Cobertura (días): Crítica / Adecuada / Exceso        (3 conjuntos)
  - Demanda relativa (ratio real/esperado): Normal / Alta (2 conjuntos)
  - Tendencia (score -1..1): Estable / Ascendente         (2 conjuntos)
  → 3 x 2 x 2 = 12 reglas (no 27; ver nota de diseño en el chat con Adrián).

Uso: python -m app.seed_difuso
"""
from app.core.database import SessionLocal
from app.models.motor_difuso import VariableLinguistica, ConjuntoDifuso, ReglaDifusa

# (nombre_variable, minimo, maximo, [(etiqueta, a, b, c, d), ...])
VARIABLES = [
    (
        "cobertura",
        0,
        60,
        [
            ("Crítica", 0, 0, 5, 15),
            ("Adecuada", 10, 20, 30, 40),
            ("Exceso", 35, 45, 60, 60),
        ],
    ),
    (
        "demanda_relativa",
        0,
        2.5,
        [
            ("Normal", 0, 0, 1.0, 1.3),
            ("Alta", 1.1, 1.5, 2.5, 2.5),
        ],
    ),
    (
        "tendencia",
        -1,
        1,
        [
            ("Estable", -1, -1, -0.1, 0.15),
            ("Ascendente", 0.0, 0.3, 1, 1),
        ],
    ),
    (
        "reposicion",
        0,
        100,
        [
            ("Baja", 0, 0, 15, 30),
            ("Media", 20, 45, 45, 70),
            ("Alta", 55, 75, 100, 100),
        ],
    ),
]

# (codigo, cobertura, demanda, tendencia, reposicion)
REGLAS = [
    ("R01", "Crítica", "Normal", "Estable", "Alta"),
    ("R02", "Crítica", "Normal", "Ascendente", "Alta"),
    ("R03", "Crítica", "Alta", "Estable", "Alta"),
    ("R04", "Crítica", "Alta", "Ascendente", "Alta"),
    ("R05", "Adecuada", "Normal", "Estable", "Baja"),
    ("R06", "Adecuada", "Normal", "Ascendente", "Media"),
    ("R07", "Adecuada", "Alta", "Estable", "Media"),
    ("R08", "Adecuada", "Alta", "Ascendente", "Alta"),
    ("R09", "Exceso", "Normal", "Estable", "Baja"),
    ("R10", "Exceso", "Normal", "Ascendente", "Baja"),
    ("R11", "Exceso", "Alta", "Estable", "Baja"),
    ("R12", "Exceso", "Alta", "Ascendente", "Media"),
]


def run():
    db = SessionLocal()
    try:
        db.query(ReglaDifusa).delete()
        db.query(ConjuntoDifuso).delete()
        db.query(VariableLinguistica).delete()
        db.commit()

        for nombre, minimo, maximo, conjuntos in VARIABLES:
            variable = VariableLinguistica(nombre=nombre, minimo=minimo, maximo=maximo)
            db.add(variable)
            db.flush()
            for etiqueta, a, b, c, d in conjuntos:
                db.add(ConjuntoDifuso(variable_id=variable.id, etiqueta=etiqueta, a=a, b=b, c=c, d=d))
        db.commit()

        for codigo, cobertura, demanda, tendencia, reposicion in REGLAS:
            db.add(
                ReglaDifusa(
                    codigo=codigo,
                    cobertura=cobertura,
                    demanda_relativa=demanda,
                    tendencia=tendencia,
                    reposicion=reposicion,
                    peso=1.0,
                    activa=True,
                )
            )
        db.commit()

        print(f"Motor difuso cargado: {len(VARIABLES)} variables, {len(REGLAS)} reglas (borrador).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
