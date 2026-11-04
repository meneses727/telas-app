"""Vaciar los datos de negocio para volver a cargar los Excel desde cero.

Borra el catálogo de telas, las ventas, el inventario, las cargas, los
resultados de minería, las propuestas y las simulaciones. Conserva los
usuarios, los roles, la bitácora de accesos y el motor difuso (variables,
conjuntos y reglas). Luego vuelve a crear las categorías y los proveedores base.
"""
from sqlalchemy.orm import Session

from app.models.importacion import LoteImportacion, VentaHistorica, InventarioSnapshot
from app.models.mineria import IndiceEstacional, ClasificacionDemanda, EvaluacionExperta
from app.models.recomendacion import PropuestaCompra, RecomendacionCompra, Simulacion
from app.models.tela import Tela, UmbralStock, CategoriaTela, Proveedor
from app.seed import CATEGORIAS_BASE, PROVEEDORES_BASE

# Orden: primero las tablas que apuntan a otras.
TABLAS = [
    ("recomendaciones", RecomendacionCompra),
    ("propuestas", PropuestaCompra),
    ("simulaciones", Simulacion),
    ("indices_estacionales", IndiceEstacional),
    ("clasificaciones", ClasificacionDemanda),
    ("evaluaciones_expertas", EvaluacionExperta),
    ("ventas", VentaHistorica),
    ("inventarios", InventarioSnapshot),
    ("cargas", LoteImportacion),
    ("umbrales", UmbralStock),
    ("telas", Tela),
    ("categorias", CategoriaTela),
    ("proveedores", Proveedor),
]


def vaciar_datos(db: Session) -> dict[str, int]:
    borrados = {}
    try:
        for nombre, modelo in TABLAS:
            borrados[nombre] = db.query(modelo).delete(synchronize_session=False)
        for nombre in CATEGORIAS_BASE:
            db.add(CategoriaTela(nombre=nombre))
        for nombre, plazo in PROVEEDORES_BASE:
            db.add(Proveedor(nombre=nombre, lead_time_dias=plazo))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return borrados
