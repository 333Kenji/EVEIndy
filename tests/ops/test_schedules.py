from __future__ import annotations

from app.schedules import SCHEDULE


def test_schedule_definitions_exist() -> None:
    assert "price_refresh" in SCHEDULE
    assert "indices_refresh" in SCHEDULE
    assert "esi_jobs_sync" in SCHEDULE
    assert "indicators" in SCHEDULE
    assert "alerts" in SCHEDULE

