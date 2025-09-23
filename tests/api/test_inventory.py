from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_inventory_valuation_monkeypatched(monkeypatch):
    from app.services import inventory as svc

    monkeypatch.setattr(svc, "get_on_hand", lambda owner_scope, type_ids=None: {34: {"qty": 100.0, "avg_cost": 5.0}})
    resp = client.get("/inventory/valuation", params={"owner_scope": "corp"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"][0]["avg_cost"] == 5.0


def test_inventory_wip_monkeypatched(monkeypatch):
    from app.services import inventory as svc

    monkeypatch.setattr(svc, "get_wip", lambda owner_scope: {603: 2.0})
    resp = client.get("/inventory/wip", params={"owner_scope": "corp"})
    assert resp.status_code == 200
    assert resp.json()["items"][0]["type_id"] == 603

