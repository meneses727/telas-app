from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.dashboard import ResumenDashboardOut
from app.services import dashboard as servicio_dashboard

router = APIRouter(prefix="/dashboard", tags=["panel de control"])


@router.get("/resumen", response_model=ResumenDashboardOut)
def resumen(
    categoria_id: Optional[int] = Query(None, description="Filtra por categoría de tela"),
    color: Optional[str] = Query(None, description="Filtra por color (coincidencia parcial)"),
    estado: Optional[str] = Query(None, description="Filtra por estado: Crítica | Adecuada | Exceso | Sin datos"),
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    return servicio_dashboard.obtener_resumen(db, categoria_id=categoria_id, color=color, estado=estado)
