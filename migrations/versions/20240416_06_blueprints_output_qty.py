"""Add output_qty to blueprints."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20240416_06"
down_revision = "20240416_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("blueprints", sa.Column("output_qty", sa.Numeric(20, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("blueprints", "output_qty")

