"""Script de carga inicial: roles base y un usuario administrador de prueba.

Uso: python -m app.seed
"""
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.usuario import Rol, Usuario
from app.models.tela import CategoriaTela, Proveedor

ROLES_BASE = ["Administrador", "Planificador"]
CATEGORIAS_BASE = ["Algodón", "Poliéster", "Mezcla", "Drill", "Jersey"]
PROVEEDORES_BASE = [("Textil Piura S.A.", 10), ("Importadora Andina", 20), ("Hilos del Sur", 7)]


def run():
    db = SessionLocal()
    try:
        for nombre_rol in ROLES_BASE:
            existe = db.query(Rol).filter(Rol.nombre == nombre_rol).first()
            if not existe:
                db.add(Rol(nombre=nombre_rol))
        db.commit()

        admin_rol = db.query(Rol).filter(Rol.nombre == "Administrador").first()
        admin_correo = "admin@textilmontalvan.com"
        admin_existente = db.query(Usuario).filter(Usuario.correo == admin_correo).first()
        if not admin_existente:
            db.add(
                Usuario(
                    nombre="Administrador",
                    correo=admin_correo,
                    password_hash=hash_password("Admin123*"),
                    estado=True,
                    rol_id=admin_rol.id,
                )
            )
            db.commit()
            print(f"Usuario administrador creado: {admin_correo} / Admin123*")
        else:
            print("El usuario administrador ya existía.")

        for nombre_cat in CATEGORIAS_BASE:
            if not db.query(CategoriaTela).filter(CategoriaTela.nombre == nombre_cat).first():
                db.add(CategoriaTela(nombre=nombre_cat))
        for nombre_prov, lead_time in PROVEEDORES_BASE:
            if not db.query(Proveedor).filter(Proveedor.nombre == nombre_prov).first():
                db.add(Proveedor(nombre=nombre_prov, lead_time_dias=lead_time))
        db.commit()

        print("Seed completado.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
