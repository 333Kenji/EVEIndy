from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_systems_index_monkeypatched(monkeypatch):
    from app.services import systems as svc

    captured: dict = {}

    def fake_list_systems(**kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return {
            "items": [
                {
                    "system_id": 30000142,
                    "name": "Jita",
                    "region_id": 10000002,
                    "constellation_id": 20000020,
                    "indices": {"manufacturing": 0.021},
                }
            ],
            "next_cursor": None,
            "has_more": False,
        }

    monkeypatch.setattr(svc, "list_systems", fake_list_systems)
    resp = client.get("/systems", params={"region_id": 10000002})
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"][0]["name"] == "Jita"
    assert captured["region_id"] == 10000002


def test_list_rigs(monkeypatch):
    from app.api.routes import structures as r

    # Force fallback list (simulate DB failure)
    monkeypatch.setattr(r, "_engine", lambda: (_ for _ in ()).throw(RuntimeError("no db")))
    with TestClient(app) as c:
        resp = c.get("/structures/rigs", params={"activity": "Manufacturing"})
        assert resp.status_code == 200
        rigs = resp.json()["rigs"]
        assert any("Manufacturing" == rig["activity"] for rig in rigs)
