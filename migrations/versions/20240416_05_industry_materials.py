"""Industry materials subset table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20240416_05"
down_revision = "20240416_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "industry_materials",
        sa.Column("type_id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False, server_default="bp_material"),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("industry_materials")

