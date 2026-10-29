"""stock en tránsito en los cortes de inventario

Revision ID: 7a2c4e9b1d03
Revises: 1cd9fc19c52e
Create Date: 2026-10-28 22:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a2c4e9b1d03"
down_revision: Union[str, None] = "1cd9fc19c52e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "inventario_snapshots",
        sa.Column("en_transito_metros", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("inventario_snapshots", "en_transito_metros")
