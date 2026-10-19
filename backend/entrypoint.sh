#!/bin/sh
set -e

echo "Aplicando migraciones de base de datos..."
alembic upgrade head

echo "Cargando datos semilla (roles, admin, catalogo base)..."
python -m app.seed

echo "Cargando motor difuso (variables y reglas)..."
python -m app.seed_difuso

echo "Iniciando servidor..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
