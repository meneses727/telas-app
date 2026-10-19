import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.importacion import LoteImportacion
from app.models.usuario import Usuario
from app.schemas.importacion import ResultadoImportacion, ErrorFila, LoteImportacionOut
from app.services.ingesta import (
    leer_dataframe,
    validar_ventas,
    validar_inventario,
    TAMANO_MAXIMO_MB,
)

router = APIRouter(prefix="/datos", tags=["carga de datos"])

MAX_ERRORES_PREVIEW = 50

# Guardamos en memoria (por lote) el detalle completo de errores para poder
# descargarlo luego sin volver a pedir el archivo. En un entorno con varios
# workers esto debería ir a almacenamiento persistente (tabla o blob storage).
_ERRORES_POR_LOTE: dict[int, list[ErrorFila]] = {}


@router.post("/cargar", response_model=ResultadoImportacion)
async def cargar_archivo(
    tipo: str = Query(..., pattern="^(ventas|inventario)$"),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    contenido = await archivo.read()
    tamano_mb = len(contenido) / (1024 * 1024)
    if tamano_mb > TAMANO_MAXIMO_MB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El archivo supera el máximo de {TAMANO_MAXIMO_MB} MB",
        )

    try:
        df = leer_dataframe(contenido, archivo.filename or "")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    try:
        if tipo == "ventas":
            resultado = validar_ventas(df, db)
        else:
            resultado = validar_inventario(df, db)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    estado = "procesado" if not resultado.errores else (
        "con_errores" if resultado.registros_validos else "fallido"
    )

    lote = LoteImportacion(
        usuario_id=usuario.id,
        tipo=tipo,
        archivo=archivo.filename or "sin_nombre",
        filas_totales=resultado.filas_totales,
        filas_validas=resultado.filas_validas,
        filas_con_error=resultado.filas_con_error,
        estado=estado,
    )
    db.add(lote)
    db.flush()  # obtiene lote.id antes de asociar los registros

    for registro in resultado.registros_validos:
        registro.lote_id = lote.id
        db.add(registro)

    db.commit()
    db.refresh(lote)

    _ERRORES_POR_LOTE[lote.id] = resultado.errores

    return ResultadoImportacion(
        lote_id=lote.id,
        tipo=tipo,
        archivo=lote.archivo,
        filas_totales=resultado.filas_totales,
        filas_validas=resultado.filas_validas,
        filas_con_error=resultado.filas_con_error,
        estado=estado,
        errores=[ErrorFila(fila=e.fila, motivo=e.motivo) for e in resultado.errores[:MAX_ERRORES_PREVIEW]],
    )


@router.get("/lotes", response_model=list[LoteImportacionOut])
def historial_cargas(db: Session = Depends(get_db), _usuario: Usuario = Depends(get_current_user)):
    lotes = (
        db.query(LoteImportacion)
        .options(joinedload(LoteImportacion.usuario))
        .order_by(LoteImportacion.fecha_carga.desc())
        .all()
    )
    return [
        LoteImportacionOut(
            id=l.id,
            tipo=l.tipo,
            archivo=l.archivo,
            fecha_carga=l.fecha_carga,
            filas_totales=l.filas_totales,
            filas_validas=l.filas_validas,
            filas_con_error=l.filas_con_error,
            estado=l.estado,
            usuario_nombre=l.usuario.nombre if l.usuario else None,
        )
        for l in lotes
    ]


@router.get("/lotes/{lote_id}/errores")
def descargar_informe_errores(
    lote_id: int, db: Session = Depends(get_db), _usuario: Usuario = Depends(get_current_user)
):
    lote = db.query(LoteImportacion).filter(LoteImportacion.id == lote_id).first()
    if lote is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado")

    errores = _ERRORES_POR_LOTE.get(lote_id, [])

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["fila", "motivo"])
    for err in errores:
        writer.writerow([err.fila, err.motivo])
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=errores_lote_{lote_id}.csv"},
    )
