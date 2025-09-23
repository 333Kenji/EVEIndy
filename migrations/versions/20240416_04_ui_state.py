"""UI state persistence table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20240416_04"
down_revision = "20240416_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ui_state",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ui_state")

