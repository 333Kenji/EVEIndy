"""Subset schema extensions: rigs, services, universe_ids, market_snapshots."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20240416_03"
down_revision = "20240416_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rigs",
        sa.Column("rig_id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("activity", sa.Text(), nullable=True),
        sa.Column("me_bonus", sa.Numeric(10, 6), nullable=True),
        sa.Column("te_bonus", sa.Numeric(10, 6), nullable=True),
    )
    op.create_table(
        "services",
        sa.Column("service_id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("activity", sa.Text(), nullable=True),
        sa.Column("bonus", sa.JSON(), nullable=True),
    )
    op.create_table(
        "universe_ids",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("kind", sa.Text(), nullable=False),  # system|region|constellation
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
    )
    op.create_index("ix_universe_ids_kind", "universe_ids", ["kind"]) 

    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("region_id", sa.BigInteger(), nullable=False),
        sa.Column("type_id", sa.Integer(), nullable=False),
        sa.Column("bid", sa.Numeric(28, 4), nullable=True),
        sa.Column("ask", sa.Numeric(28, 4), nullable=True),
        sa.Column("mid", sa.Numeric(28, 4), nullable=True),
        sa.Column("depth_qty_1pct", sa.Numeric(20, 2), nullable=True),
        sa.Column("depth_qty_5pct", sa.Numeric(20, 2), nullable=True),
    )
    op.create_index("ix_market_snapshots_type_region_ts", "market_snapshots", ["type_id", "region_id", "ts"])


def downgrade() -> None:
    op.drop_index("ix_market_snapshots_type_region_ts", table_name="market_snapshots")
    op.drop_table("market_snapshots")
    op.drop_index("ix_universe_ids_kind", table_name="universe_ids")
    op.drop_table("universe_ids")
    op.drop_table("services")
    op.drop_table("rigs")

