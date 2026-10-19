from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.recomendacion import PropuestaCompra
from app.models.usuario import Usuario
from app.schemas.propuesta import PropuestaDetalleOut, ActualizarItemRequest
from app.services import propuesta as servicio_propuesta

router = APIRouter(prefix="/propuestas", tags=["propuesta de compra"])


@router.get("", response_model=list[dict])
def listar_propuestas(db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    propuestas = (
        db.query(PropuestaCompra)
        .options(joinedload(PropuestaCompra.items))
        .filter(PropuestaCompra.usuario_id == usuario.id)
        .order_by(PropuestaCompra.fecha.desc())
        .all()
    )
    return [
        {"id": p.id, "estado": p.estado, "fecha": p.fecha.isoformat(), "cantidad_items": len(p.items)}
        for p in propuestas
    ]


@router.get("/{propuesta_id}", response_model=PropuestaDetalleOut)
def obtener_propuesta(
    propuesta_id: int, db: Session = Depends(get_db), _usuario: Usuario = Depends(get_current_user)
):
    try:
        return servicio_propuesta.obtener_detalle(db, propuesta_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.put("/{propuesta_id}/items/{item_id}", response_model=PropuestaDetalleOut)
def actualizar_item(
    propuesta_id: int,
    item_id: int,
    data: ActualizarItemRequest,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    try:
        return servicio_propuesta.actualizar_item(db, propuesta_id, item_id, data.metros_ajustados, data.motivo_ajuste)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/{propuesta_id}/items/{item_id}", response_model=PropuestaDetalleOut)
def quitar_item(
    propuesta_id: int, item_id: int, db: Session = Depends(get_db), _usuario: Usuario = Depends(get_current_user)
):
    try:
        return servicio_propuesta.eliminar_item(db, propuesta_id, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{propuesta_id}/cerrar", response_model=PropuestaDetalleOut)
def cerrar_propuesta(
    propuesta_id: int, db: Session = Depends(get_db), _usuario: Usuario = Depends(get_current_user)
):
    try:
        return servicio_propuesta.cerrar_propuesta(db, propuesta_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/{propuesta_id}/exportar.xlsx")
def exportar_excel(
    propuesta_id: int, db: Session = Depends(get_db), _usuario: Usuario = Depends(get_current_user)
):
    try:
        contenido = servicio_propuesta.generar_excel(db, propuesta_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return StreamingResponse(
        iter([contenido]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=propuesta_{propuesta_id}.xlsx"},
    )


@router.get("/{propuesta_id}/exportar.pdf")
def exportar_pdf(
    propuesta_id: int, db: Session = Depends(get_db), _usuario: Usuario = Depends(get_current_user)
):
    try:
        contenido = servicio_propuesta.generar_pdf(db, propuesta_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return StreamingResponse(
        iter([contenido]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=propuesta_{propuesta_id}.pdf"},
    )
