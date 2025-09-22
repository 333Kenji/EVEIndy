"""Initial schema for EVEINDY."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20240416_01"
down_revision = None
branch_labels = None
depends_on = None


def create_timestamp_trigger() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = timezone('utc', now());
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def drop_timestamp_trigger() -> None:
    op.execute("DROP FUNCTION IF EXISTS set_updated_at() CASCADE;")


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
    create_timestamp_trigger()

    acquisition_source = sa.Enum(
        "market",
        "industry_excess",
        "contract",
        name="acquisition_source",
    )
    consumption_reason = sa.Enum(
        "job_run",
        "writeoff",
        name="consumption_reason",
    )
    job_activity = sa.Enum(
        "manufacturing",
        "reaction",
        "invention",
        "research",
        name="job_activity",
    )
    job_status = sa.Enum(
        "queued",
        "active",
        "delivered",
        "cancelled",
        name="job_status",
    )
    buy_order_status = sa.Enum(
        "open",
        "filled",
        "cancelled",
        name="buy_order_status",
    )
    order_side = sa.Enum("bid", "ask", name="order_side")

    for enum in (
        acquisition_source,
        consumption_reason,
        job_activity,
        job_status,
        buy_order_status,
        order_side,
    ):
        enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "inventory",
        sa.Column("owner_scope", sa.Text(), nullable=False),
        sa.Column("type_id", sa.Integer(), nullable=False),
        sa.Column("qty_on_hand", sa.Numeric(20, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("avg_cost", sa.Numeric(28, 4), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.PrimaryKeyConstraint("owner_scope", "type_id", name="inventory_pkey"),
    )
    op.create_index(
        "ix_inventory_owner_scope_avg_cost",
        "inventory",
        ["owner_scope", "avg_cost"],
    )
    op.execute(
        "CREATE TRIGGER inventory_set_updated_at BEFORE UPDATE ON inventory "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at();"
    )

    op.create_table(
        "inventory_by_loc",
        sa.Column("owner_scope", sa.Text(), nullable=False),
        sa.Column("type_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.BigInteger(), nullable=False),
        sa.Column("qty_on_hand", sa.Numeric(20, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("qty_reserved", sa.Numeric(20, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("qty_in_transit", sa.Numeric(20, 2), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.PrimaryKeyConstraint(
            "owner_scope", "type_id", "location_id", name="inventory_by_loc_pkey"
        ),
    )
    op.create_index(
        "ix_inventory_by_loc_reserved",
        "inventory_by_loc",
        ["owner_scope", "qty_reserved"],
        postgresql_where=sa.text("qty_reserved > 0"),
    )
    op.execute(
        "CREATE TRIGGER inventory_by_loc_set_updated_at BEFORE UPDATE ON inventory_by_loc "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at();"
    )

    op.create_table(
        "industry_jobs",
        sa.Column("job_id", sa.BigInteger(), nullable=False),
        sa.Column("owner_scope", sa.Text(), nullable=False),
        sa.Column("char_id", sa.BigInteger(), nullable=False),
        sa.Column("type_id", sa.Integer(), nullable=False),
        sa.Column("activity", job_activity, nullable=False),
        sa.Column("runs", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("end_time", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("output_qty", sa.Numeric(20, 2), nullable=True),
        sa.Column("status", job_status, nullable=False),
        sa.Column("location_id", sa.BigInteger(), nullable=True),
        sa.Column("facility_id", sa.BigInteger(), nullable=True),
        sa.Column("fees_isk", sa.Numeric(28, 4), nullable=True, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.PrimaryKeyConstraint("job_id", name="industry_jobs_pkey"),
    )
    op.create_index(
        "ix_industry_jobs_status_end_time",
        "industry_jobs",
        ["status", "end_time"],
    )
    op.create_index(
        "ix_industry_jobs_owner_scope_status",
        "industry_jobs",
        ["owner_scope", "status"],
    )
    op.execute(
        "CREATE TRIGGER industry_jobs_set_updated_at BEFORE UPDATE ON industry_jobs "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at();"
    )

    op.create_table(
        "buy_orders",
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("owner_scope", sa.Text(), nullable=False),
        sa.Column("type_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.BigInteger(), nullable=False),
        sa.Column("region_id", sa.BigInteger(), nullable=False),
        sa.Column("price", sa.Numeric(28, 4), nullable=False),
        sa.Column("remaining_qty", sa.Numeric(20, 2), nullable=False),
        sa.Column("issued_ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_seen_ts", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status", buy_order_status, nullable=False, server_default="open"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.PrimaryKeyConstraint("order_id", name="buy_orders_pkey"),
    )
    op.create_index(
        "ix_buy_orders_owner_scope_status",
        "buy_orders",
        ["owner_scope", "status"],
    )
    op.create_index(
        "ix_buy_orders_type_region",
        "buy_orders",
        ["type_id", "region_id"],
    )
    op.execute(
        "CREATE TRIGGER buy_orders_set_updated_at BEFORE UPDATE ON buy_orders "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at();"
    )

    op.create_table(
        "acquisitions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("timezone('utc', now())")),
        sa.Column("owner_scope", sa.Text(), nullable=False),
        sa.Column("type_id", sa.Integer(), nullable=False),
        sa.Column("qty", sa.Numeric(20, 2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(28, 4), nullable=False),
        sa.Column("source", acquisition_source, nullable=False),
        sa.Column("location_id", sa.BigInteger(), nullable=True),
        sa.Column("ref_job_id", sa.BigInteger(), nullable=True),
        sa.Column("ref_order_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["ref_job_id"], ["industry_jobs.job_id"], onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["ref_order_id"], ["buy_orders.order_id"], onupdate="CASCADE"),
    )
    op.create_index(
        "ix_acquisitions_owner_scope_ts",
        "acquisitions",
        ["owner_scope", "ts"],
    )

    op.create_table(
        "consumptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("timezone('utc', now())")),
        sa.Column("owner_scope", sa.Text(), nullable=False),
        sa.Column("type_id", sa.Integer(), nullable=False),
        sa.Column("qty", sa.Numeric(20, 2), nullable=False),
        sa.Column("reason", consumption_reason, nullable=False),
        sa.Column("location_id", sa.BigInteger(), nullable=True),
        sa.Column("ref_job_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["ref_job_id"], ["industry_jobs.job_id"], onupdate="CASCADE"),
    )
    op.create_index(
        "ix_consumptions_job_type",
        "consumptions",
        ["ref_job_id", "type_id"],
    )

    op.create_table(
        "orderbook_snapshots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("region_id", sa.BigInteger(), nullable=False),
        sa.Column("type_id", sa.Integer(), nullable=False),
        sa.Column("side", order_side, nullable=False),
        sa.Column("best_px", sa.Numeric(28, 4), nullable=True),
        sa.Column("best_qty", sa.Numeric(20, 2), nullable=True),
        sa.Column("depth_qty_1pct", sa.Numeric(20, 2), nullable=True),
        sa.Column("depth_qty_5pct", sa.Numeric(20, 2), nullable=True),
        sa.Column("stdev_pct", sa.Numeric(10, 5), nullable=True),
    )
    op.create_index(
        "ix_orderbook_snapshots_type_region_ts",
        "orderbook_snapshots",
        ["type_id", "region_id", "ts"],
    )
    op.create_unique_constraint(
        "uq_orderbook_snapshots_side_ts",
        "orderbook_snapshots",
        ["region_id", "type_id", "side", "ts"],
    )

    op.create_table(
        "consumption_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("timezone('utc', now())")),
        sa.Column("owner_scope", sa.Text(), nullable=False),
        sa.Column("type_id", sa.Integer(), nullable=False),
        sa.Column("qty", sa.Numeric(20, 2), nullable=False),
        sa.Column("location_id", sa.BigInteger(), nullable=True),
        sa.Column("ref_job_id", sa.BigInteger(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["ref_job_id"], ["industry_jobs.job_id"], onupdate="CASCADE"),
    )
    op.create_index(
        "ix_consumption_log_ts",
        "consumption_log",
        ["ts"],
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW inventory_coverage_view AS
        SELECT
            owner_scope,
            type_id,
            SUM(qty_on_hand) AS total_on_hand,
            SUM(qty_reserved) AS total_reserved,
            SUM(qty_in_transit) AS total_in_transit
        FROM inventory_by_loc
        GROUP BY owner_scope, type_id;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS inventory_coverage_view;")

    op.drop_index("ix_consumption_log_ts", table_name="consumption_log")
    op.drop_table("consumption_log")

    op.drop_constraint("uq_orderbook_snapshots_side_ts", "orderbook_snapshots", type_="unique")
    op.drop_index("ix_orderbook_snapshots_type_region_ts", table_name="orderbook_snapshots")
    op.drop_table("orderbook_snapshots")

    op.drop_index("ix_consumptions_job_type", table_name="consumptions")
    op.drop_table("consumptions")

    op.drop_index("ix_acquisitions_owner_scope_ts", table_name="acquisitions")
    op.drop_table("acquisitions")

    op.drop_index("ix_buy_orders_type_region", table_name="buy_orders")
    op.drop_index("ix_buy_orders_owner_scope_status", table_name="buy_orders")
    op.drop_table("buy_orders")

    op.drop_index("ix_industry_jobs_owner_scope_status", table_name="industry_jobs")
    op.drop_index("ix_industry_jobs_status_end_time", table_name="industry_jobs")
    op.drop_table("industry_jobs")

    op.drop_index("ix_inventory_by_loc_reserved", table_name="inventory_by_loc")
    op.drop_table("inventory_by_loc")

    op.drop_index("ix_inventory_owner_scope_avg_cost", table_name="inventory")
    op.drop_table("inventory")

    drop_timestamp_trigger()

    for enum_name in (
        "order_side",
        "buy_order_status",
        "job_status",
        "job_activity",
        "consumption_reason",
        "acquisition_source",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
