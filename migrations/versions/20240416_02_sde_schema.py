"""SDE schema tables for types, blueprints, structures, and cost indices."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20240416_02"
down_revision = "20240416_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "type_ids",
        sa.Column("type_id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
    )

    op.create_table(
        "blueprints",
        sa.Column("type_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("activity", sa.Text(), nullable=False),
        sa.Column("materials", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("type_id", "product_id", "activity", name="blueprints_pkey"),
    )

    op.create_table(
        "structures",
        sa.Column("structure_id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("rig_slots", sa.Integer(), nullable=True),
        sa.Column("bonuses", sa.JSON(), nullable=True),
    )

    op.create_table(
        "cost_indices",
        sa.Column("system_id", sa.BigInteger(), nullable=False),
        sa.Column("activity", sa.Text(), nullable=False),
        sa.Column("index_value", sa.Numeric(10, 6), nullable=False),
        sa.PrimaryKeyConstraint("system_id", "activity", name="cost_indices_pkey"),
    )


def downgrade() -> None:
    op.drop_table("cost_indices")
    op.drop_table("structures")
    op.drop_table("blueprints")
    op.drop_table("type_ids")

