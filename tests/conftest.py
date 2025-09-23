import sys
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parent.parent
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)


@pytest.fixture()
def inventory_test_engine(monkeypatch):
    """Provide an in-memory SQLite engine patched into the inventory service."""

    engine = sa.create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                create table inventory (
                    owner_scope text not null,
                    type_id integer not null,
                    qty_on_hand numeric(20, 2) not null,
                    avg_cost numeric(28, 4) not null
                )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                create table industry_jobs (
                    owner_scope text not null,
                    type_id integer not null,
                    runs integer not null,
                    output_qty numeric(20, 2),
                    status text not null
                )
                """
            )
        )

    from app.services import inventory as inventory_service

    monkeypatch.setattr(inventory_service, "_engine", lambda: engine)
    try:
        yield engine
    finally:
        engine.dispose()
