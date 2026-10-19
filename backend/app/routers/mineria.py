from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.mineria import ClasificacionDemanda
from app.models.tela import Tela
from app.models.usuario import Usuario
from app.schemas.mineria import EvaluacionExpertaCreate, ResumenMineriaOut
from app.services import mineria as servicio_mineria
from app.models.mineria import EvaluacionExperta

router = APIRouter(prefix="/mineria", tags=["minería de datos"])


@router.post("/evaluaciones", status_code=status.HTTP_201_CREATED)
def registrar_evaluacion_experta(
    data: EvaluacionExpertaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    tela = db.query(Tela).filter(Tela.id == data.tela_id).first()
    if tela is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tela no encontrada")

    evaluacion = EvaluacionExperta(tela_id=data.tela_id, usuario_id=usuario.id, percepcion=data.percepcion)
    db.add(evaluacion)
    db.commit()
    return {"mensaje": "Percepción registrada", "tela_id": data.tela_id, "percepcion": data.percepcion}


@router.post("/recalcular")
def recalcular_mineria(db: Session = Depends(get_db), _usuario: Usuario = Depends(get_current_user)):
    telas = db.query(Tela).all()
    for tela in telas:
        servicio_mineria.calcular_indice_estacional(db, tela.id)
    clases = servicio_mineria.clasificar_demanda_todas(db)
    return {"telas_procesadas": len(telas), "clasificaciones": clases}


@router.get("/{tela_id}/resumen", response_model=ResumenMineriaOut)
def resumen_mineria(tela_id: int, db: Session = Depends(get_db), _usuario: Usuario = Depends(get_current_user)):
    tela = db.query(Tela).filter(Tela.id == tela_id).first()
    if tela is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tela no encontrada")

    # Se recalcula bajo demanda para que el resumen siempre refleje el
    # historial de ventas más reciente, en vez de depender de un batch previo.
    indices = servicio_mineria.calcular_indice_estacional(db, tela_id)

    ultima_clase = (
        db.query(ClasificacionDemanda)
        .filter(ClasificacionDemanda.tela_id == tela_id)
        .order_by(ClasificacionDemanda.fecha.desc())
        .first()
    )

    hoy = date.today()
    return ResumenMineriaOut(
        tela_id=tela.id,
        tela_codigo=tela.codigo,
        indice_estacional=indices,
        clase_demanda=ultima_clase.clase if ultima_clase else None,
        demanda_relativa=servicio_mineria.demanda_relativa(db, tela_id, hoy),
        tendencia=servicio_mineria.tendencia(db, tela_id, hoy),
        fecha_referencia=hoy,
    )
