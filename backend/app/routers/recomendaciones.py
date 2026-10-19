import math

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.recomendacion import PropuestaCompra, RecomendacionCompra
from app.models.tela import Tela
from app.models.usuario import Usuario
from app.schemas.recomendacion import RecomendacionCalculoOut, AgregarAPropuestaRequest
from app.services import recomendacion as servicio_recomendacion

router = APIRouter(prefix="/recomendaciones", tags=["recomendación de compra"])


@router.get("/{tela_id}/calcular", response_model=RecomendacionCalculoOut)
def calcular_recomendacion(
    tela_id: int, db: Session = Depends(get_db), _usuario: Usuario = Depends(get_current_user)
):
    try:
        resultado = servicio_recomendacion.generar_recomendacion_compra(db, tela_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return resultado


def _obtener_o_crear_borrador(db: Session, usuario_id: int, propuesta_id: int | None) -> PropuestaCompra:
    if propuesta_id is not None:
        propuesta = db.query(PropuestaCompra).filter(PropuestaCompra.id == propuesta_id).first()
        if propuesta is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Propuesta no encontrada")
        return propuesta

    propuesta = (
        db.query(PropuestaCompra)
        .filter(PropuestaCompra.usuario_id == usuario_id, PropuestaCompra.estado == "borrador")
        .order_by(PropuestaCompra.fecha.desc())
        .first()
    )
    if propuesta is None:
        propuesta = PropuestaCompra(usuario_id=usuario_id, estado="borrador")
        db.add(propuesta)
        db.flush()
    return propuesta


@router.post("/agregar-a-propuesta", status_code=status.HTTP_201_CREATED)
def agregar_a_propuesta(
    data: AgregarAPropuestaRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Recalcula la recomendación (nunca confía en un valor recibido del cliente
    sin recomputarlo) y la agrega como ítem de la propuesta de compra en borrador,
    aplicando el ajuste manual del planificador si lo hay."""
    try:
        resultado = servicio_recomendacion.generar_recomendacion_compra(db, data.tela_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    if resultado["no_concluyente"] and data.metros_ajustados is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La recomendación no es concluyente; indica un valor manual en 'metros_ajustados' si deseas agregarla igual.",
        )

    propuesta = _obtener_o_crear_borrador(db, usuario.id, data.propuesta_id)

    tela = db.query(Tela).filter(Tela.id == data.tela_id).first()
    metros_finales = data.metros_ajustados if data.metros_ajustados is not None else resultado["metros_sugeridos"]
    rollos_finales = math.ceil(metros_finales / float(tela.m_por_rollo)) if metros_finales else 0

    item = RecomendacionCompra(
        tela_id=data.tela_id,
        propuesta_id=propuesta.id,
        pct_reposicion=resultado["pct_reposicion"],
        metros_sugeridos=resultado["metros_sugeridos"],
        metros_ajustados=data.metros_ajustados,
        rollos=rollos_finales,
        no_concluyente=resultado["no_concluyente"],
        motivo_ajuste=data.motivo_ajuste,
        reglas_activadas=resultado["reglas_activadas"],
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "propuesta_id": propuesta.id,
        "item_id": item.id,
        "tela_codigo": tela.codigo,
        "metros_finales": metros_finales,
        "rollos_finales": rollos_finales,
    }
