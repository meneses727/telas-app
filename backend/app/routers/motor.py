from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.motor_difuso import ReglaDifusa
from app.services import motor_difuso as servicio_motor

router = APIRouter(prefix="/motor", tags=["motor difuso"])


@router.get("/evaluar")
def evaluar(
    cobertura: float = Query(..., description="Días de cobertura de inventario"),
    demanda: float = Query(..., description="Ratio de demanda relativa (1.0 = normal)"),
    tendencia: float = Query(..., description="Score de tendencia, -1 a 1"),
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    """Ejecuta el motor Mamdani con valores crudos, para pruebas e inspección."""
    return servicio_motor.generar_recomendacion(db, cobertura, demanda, tendencia)


@router.get("/reglas")
def listar_reglas(db: Session = Depends(get_db), _usuario=Depends(get_current_user)):
    reglas = db.query(ReglaDifusa).order_by(ReglaDifusa.codigo).all()
    return [
        {
            "codigo": r.codigo,
            "cobertura": r.cobertura,
            "demanda_relativa": r.demanda_relativa,
            "tendencia": r.tendencia,
            "reposicion": r.reposicion,
            "peso": float(r.peso),
            "activa": r.activa,
        }
        for r in reglas
    ]
