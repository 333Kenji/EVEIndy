from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_bom_cost_monkeypatched(monkeypatch):
    from app.services import costing_service as svc

    class Summary:
        def __init__(self):
            self.product_id = 2; self.runs = 1
            from types import SimpleNamespace
            self.lines = [SimpleNamespace(type_id=34, qty=10, unit_price=5.0, cost=50.0)]
            self.total_cost = 50.0

    monkeypatch.setattr(svc, "cost_product", lambda product_id, region_id, runs=1, me_bonus=0.0: Summary())
    resp = client.post("/bom/cost", json={"product_id": 2, "region_id": 10000002, "runs": 1, "me_bonus": 0.02})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_cost"] == 50.0

