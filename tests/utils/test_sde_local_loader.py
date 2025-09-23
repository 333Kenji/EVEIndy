from __future__ import annotations

from pathlib import Path

from utils import manage_sde as sde


def test_load_local_parses_and_calls_upsert(tmp_path, monkeypatch):
    # Copy fixtures into tmp_path
    root = tmp_path / "data/SDE/_downloads"
    (root).mkdir(parents=True, exist_ok=True)
    (root / "typeIDs.yaml").write_text((Path("tests/fixtures/sde/typeIDs.yaml")).read_text())
    (root / "industryBlueprints.yaml").write_text((Path("tests/fixtures/sde/industryBlueprints.yaml")).read_text())

    called = {"upsert": 0, "exec": 0}

    def fake_upsert(payload, dsn):  # noqa: ANN001
        called["upsert"] += 1

    monkeypatch.setattr(sde, "upsert_sde_to_db", fake_upsert)

    # Monkeypatch SQLAlchemy engine used for upserting blueprints/materials/universe ids
    class FakeConn:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def execute(self, *args, **kwargs):
            called["exec"] += 1
        def begin(self):
            return self

    class FakeEngine:
        def begin(self):
            return FakeConn()

    import sqlalchemy as sa
    monkeypatch.setattr(sa, "create_engine", lambda dsn: FakeEngine())

    class Args:
        dir = str(root)
        no_db = False
        version = None

    # Also monkeypatch Settings to avoid requiring real DATABASE_URL
    from app import config as cfg
    monkeypatch.setattr(cfg, "Settings", lambda: type("S", (), {"database_url": "postgresql+psycopg2://test"})())

    sde.load_local(Args())
    # Second pass should remain idempotent (no duplicate work beyond normal SQL upserts)
    sde.load_local(Args())
    assert called["upsert"] == 2
    assert called["exec"] > 0

