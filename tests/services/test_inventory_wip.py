from __future__ import annotations

import sqlalchemy as sa

from app.services import inventory


def _setup_engine() -> sa.Engine:
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            create table industry_jobs (
                job_id integer primary key,
                owner_scope text,
                char_id integer,
                type_id integer,
                activity text,
                runs integer,
                start_time text,
                end_time text,
                output_qty numeric,
                status text,
                location_id integer,
                facility_id integer,
                fees_isk numeric
            )
            """
        )

        conn.exec_driver_sql(
            """
            insert into industry_jobs (
                job_id, owner_scope, char_id, type_id, activity, runs,
                start_time, end_time, output_qty, status, location_id,
                facility_id, fees_isk
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "corp",
                1001,
                603,
                "manufacturing",
                2,
                "2024-04-01T00:00:00Z",
                None,
                3,
                "active",
                60003760,
                None,
                0,
            ),
        )

        conn.exec_driver_sql(
            """
            insert into industry_jobs (
                job_id, owner_scope, char_id, type_id, activity, runs,
                start_time, end_time, output_qty, status, location_id,
                facility_id, fees_isk
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                2,
                "corp",
                1002,
                4247,
                "reaction",
                1,
                "2024-04-01T00:00:00Z",
                None,
                10,
                "queued",
                60003760,
                None,
                0,
            ),
        )

        conn.exec_driver_sql(
            """
            insert into industry_jobs (
                job_id, owner_scope, char_id, type_id, activity, runs,
                start_time, end_time, output_qty, status, location_id,
                facility_id, fees_isk
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                3,
                "corp",
                1003,
                34,
                "manufacturing",
                5,
                "2024-04-01T00:00:00Z",
                "2024-04-01T12:00:00Z",
                2,
                "delivered",
                60003760,
                None,
                0,
            ),
        )
    return engine


def test_get_wip_sums_active_and_queued(monkeypatch):
    engine = _setup_engine()
    monkeypatch.setattr(inventory, "_engine", lambda: engine)

    wip = inventory.get_wip("corp")

    assert wip == {603: 6.0, 4247: 10.0}
