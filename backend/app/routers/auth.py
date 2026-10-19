from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import verify_password, create_access_token
from app.models.usuario import Usuario, BitacoraAcceso
from app.schemas.auth import LoginRequest, TokenResponse, UsuarioOut

router = APIRouter(prefix="/auth", tags=["autenticación"])

MAX_INTENTOS_FALLIDOS = 3
MINUTOS_BLOQUEO = 15


def _registrar_evento(db: Session, usuario_id: int, evento: str):
    db.add(BitacoraAcceso(usuario_id=usuario_id, evento=evento))
    db.commit()


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Correo o contraseña incorrectos",
    )

    usuario = db.query(Usuario).filter(Usuario.correo == data.correo).first()
    if usuario is None:
        raise credenciales_invalidas

    ahora = datetime.now(timezone.utc)
    bloqueado_hasta = usuario.bloqueado_hasta
    if bloqueado_hasta is not None:
        if bloqueado_hasta.tzinfo is None:
            bloqueado_hasta = bloqueado_hasta.replace(tzinfo=timezone.utc)
        if bloqueado_hasta > ahora:
            minutos_restantes = int((bloqueado_hasta - ahora).total_seconds() // 60) + 1
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Cuenta bloqueada temporalmente. Intenta de nuevo en {minutos_restantes} minuto(s).",
            )

    if not usuario.estado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo. Contacta al administrador.",
        )

    if not verify_password(data.password, usuario.password_hash):
        usuario.intentos_fallidos += 1
        evento = "login_fallido"
        if usuario.intentos_fallidos >= MAX_INTENTOS_FALLIDOS:
            usuario.bloqueado_hasta = ahora + timedelta(minutes=MINUTOS_BLOQUEO)
            usuario.intentos_fallidos = 0
            evento = "bloqueo"
        db.commit()
        _registrar_evento(db, usuario.id, evento)
        raise credenciales_invalidas

    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    db.commit()
    _registrar_evento(db, usuario.id, "login_ok")

    token = create_access_token(subject=usuario.correo, rol=usuario.rol.nombre)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UsuarioOut)
def me(usuario: Usuario = Depends(get_current_user)):
    return UsuarioOut(id=usuario.id, nombre=usuario.nombre, correo=usuario.correo, rol=usuario.rol.nombre)
