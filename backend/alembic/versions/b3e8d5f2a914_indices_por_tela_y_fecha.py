"""índices por tela y fecha en ventas e inventario

Con cientos de códigos de tela, cada recomendación consulta las ventas y el
último corte de inventario de una tela; sin estos índices cada consulta
recorre la tabla completa.

Revision ID: b3e8d5f2a914
Revises: 7a2c4e9b1d03
Create Date: 2026-11-04 16:30:00

"""
from typing import Sequence, Union

from alembic import op


revision: str = "b3e8d5f2a914"
down_revision: Union[str, None] = "7a2c4e9b1d03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_ventas_tela_fecha", "ventas_historicas", ["tela_id", "fecha"])
    op.create_index("ix_inventario_tela_fecha", "inventario_snapshots", ["tela_id", "fecha_corte"])


def downgrade() -> None:
    op.drop_index("ix_inventario_tela_fecha", table_name="inventario_snapshots")
    op.drop_index("ix_ventas_tela_fecha", table_name="ventas_historicas")
