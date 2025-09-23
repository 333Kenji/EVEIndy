from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text

from app.services import inventory as inventory_service


def test_get_on_hand_returns_decimals(inventory_test_engine):
    with inventory_test_engine.begin() as conn:
        conn.execute(text("delete from inventory"))
        conn.execute(
            text(
                """
                insert into inventory (owner_scope, type_id, qty_on_hand, avg_cost)
                values (:owner_scope, :type_id, :qty_on_hand, :avg_cost)
                """
            ),
            {
                "owner_scope": "corp",
                "type_id": 1001,
                "qty_on_hand": "7.12",
                "avg_cost": "42.9876",
            },
        )

    result = inventory_service.get_on_hand("corp")
    assert result[1001]["qty"] == Decimal("7.12")
    assert result[1001]["avg_cost"] == Decimal("42.9876")


def test_get_wip_returns_decimals(inventory_test_engine):
    with inventory_test_engine.begin() as conn:
        conn.execute(text("delete from industry_jobs"))
        conn.execute(
            text(
                """
                insert into industry_jobs (owner_scope, type_id, runs, output_qty, status)
                values (:owner_scope, :type_id, :runs, :output_qty, :status)
                """
            ),
            {
                "owner_scope": "corp",
                "type_id": 2002,
                "runs": 3,
                "output_qty": "0.750",
                "status": "queued",
            },
        )
        conn.execute(
            text(
                """
                insert into industry_jobs (owner_scope, type_id, runs, output_qty, status)
                values (:owner_scope, :type_id, :runs, :output_qty, :status)
                """
            ),
            {
                "owner_scope": "corp",
                "type_id": 2002,
                "runs": 1,
                "output_qty": "1.2500",
                "status": "active",
            },
        )

    result = inventory_service.get_wip("corp")
    assert result[2002] == Decimal("3.50")
