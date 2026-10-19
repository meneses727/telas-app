from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.tela import Tela, CategoriaTela, Proveedor
from app.schemas.tela import TelaCreate, TelaUpdate, TelaOut, CategoriaTelaOut, ProveedorOut

router = APIRouter(prefix="/telas", tags=["catálogo de telas"])


@router.get("", response_model=list[TelaOut])
def listar_telas(
    busqueda: Optional[str] = Query(None, description="Busca por código o nombre"),
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    query = db.query(Tela).options(joinedload(Tela.categoria), joinedload(Tela.proveedor))
    if busqueda:
        patron = f"%{busqueda.strip()}%"
        query = query.filter(or_(Tela.codigo.ilike(patron), Tela.nombre.ilike(patron)))
    return query.order_by(Tela.nombre).all()


@router.get("/categorias", response_model=list[CategoriaTelaOut])
def listar_categorias(db: Session = Depends(get_db), _usuario=Depends(get_current_user)):
    return db.query(CategoriaTela).order_by(CategoriaTela.nombre).all()


@router.get("/proveedores", response_model=list[ProveedorOut])
def listar_proveedores(db: Session = Depends(get_db), _usuario=Depends(get_current_user)):
    return db.query(Proveedor).order_by(Proveedor.nombre).all()


@router.get("/{tela_id}", response_model=TelaOut)
def obtener_tela(tela_id: int, db: Session = Depends(get_db), _usuario=Depends(get_current_user)):
    tela = (
        db.query(Tela)
        .options(joinedload(Tela.categoria), joinedload(Tela.proveedor))
        .filter(Tela.id == tela_id)
        .first()
    )
    if tela is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tela no encontrada")
    return tela


def _validar_referencias(db: Session, data: TelaCreate | TelaUpdate):
    if data.categoria_id is not None:
        if not db.query(CategoriaTela).filter(CategoriaTela.id == data.categoria_id).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Categoría no existe")
    if data.proveedor_id is not None:
        if not db.query(Proveedor).filter(Proveedor.id == data.proveedor_id).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Proveedor no existe")


@router.post("", response_model=TelaOut, status_code=status.HTTP_201_CREATED)
def crear_tela(
    data: TelaCreate,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    if db.query(Tela).filter(Tela.codigo == data.codigo).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una tela con el código '{data.codigo}'",
        )
    _validar_referencias(db, data)

    tela = Tela(**data.model_dump())
    db.add(tela)
    db.commit()
    db.refresh(tela)
    return tela


@router.put("/{tela_id}", response_model=TelaOut)
def actualizar_tela(
    tela_id: int,
    data: TelaUpdate,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    tela = db.query(Tela).filter(Tela.id == tela_id).first()
    if tela is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tela no encontrada")

    duplicado = (
        db.query(Tela)
        .filter(Tela.codigo == data.codigo, Tela.id != tela_id)
        .first()
    )
    if duplicado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una tela con el código '{data.codigo}'",
        )
    _validar_referencias(db, data)

    for campo, valor in data.model_dump().items():
        setattr(tela, campo, valor)

    db.commit()
    db.refresh(tela)
    return tela


@router.delete("/{tela_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_tela(tela_id: int, db: Session = Depends(get_db), _usuario=Depends(get_current_user)):
    tela = db.query(Tela).filter(Tela.id == tela_id).first()
    if tela is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tela no encontrada")
    db.delete(tela)
    db.commit()
