from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.recomendacion import Simulacion
from app.models.usuario import Usuario
from app.schemas.simulacion import SimulacionRequest, ComparacionSimulacionOut, SimulacionHistorialOut
from app.services import recomendacion as servicio_recomendacion

router = APIRouter(prefix="/simulaciones", tags=["simulación de escenarios"])


@router.post("", response_model=ComparacionSimulacionOut)
def simular(
    data: SimulacionRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    try:
        base = servicio_recomendacion.generar_recomendacion_compra(db, data.tela_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    try:
        simulado = servicio_recomendacion.generar_recomendacion_simulada(
            db, data.tela_id, data.demanda_relativa_pct, data.tendencia_pct
        )
    except ValueError as exc:
        # Sin inventario cargado: no hay cobertura con la que simular nada.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    def _diferencia(campo, es_entero=False):
        v_base = base.get(campo)
        v_sim = simulado.get(campo)
        if v_base is None or v_sim is None:
            return None
        diff = v_sim - v_base
        return round(diff) if es_entero else round(diff, 1)

    diferencia = {
        "metros": _diferencia("metros_sugeridos"),
        "rollos": _diferencia("rollos_sugeridos", es_entero=True),
        "pct_reposicion": _diferencia("pct_reposicion"),
    }

    resultado_guardado = {
        "escenario_base": {
            "pct_reposicion": base["pct_reposicion"],
            "metros_sugeridos": base["metros_sugeridos"],
            "rollos_sugeridos": base["rollos_sugeridos"],
            "no_concluyente": base["no_concluyente"],
        },
        "escenario_simulado": {
            "pct_reposicion": simulado["pct_reposicion"],
            "metros_sugeridos": simulado["metros_sugeridos"],
            "rollos_sugeridos": simulado["rollos_sugeridos"],
            "no_concluyente": simulado["no_concluyente"],
        },
        "diferencia": diferencia,
    }

    registro = Simulacion(
        tela_id=data.tela_id,
        usuario_id=usuario.id,
        parametros={
            "demanda_relativa_pct": data.demanda_relativa_pct,
            "tendencia_pct": data.tendencia_pct,
        },
        resultado=resultado_guardado,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)

    return ComparacionSimulacionOut(
        tela_id=base["tela_id"],
        tela_codigo=base["tela_codigo"],
        simulacion_id=registro.id,
        parametros=data,
        escenario_base=resultado_guardado["escenario_base"],
        escenario_simulado=resultado_guardado["escenario_simulado"],
        diferencia=diferencia,
    )


@router.get("/{tela_id}/historial", response_model=list[SimulacionHistorialOut])
def historial_simulaciones(
    tela_id: int, db: Session = Depends(get_db), _usuario: Usuario = Depends(get_current_user)
):
    return (
        db.query(Simulacion)
        .filter(Simulacion.tela_id == tela_id)
        .order_by(Simulacion.fecha.desc())
        .limit(20)
        .all()
    )
