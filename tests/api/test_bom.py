from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_bom_search_monkeypatched(monkeypatch):
    from app.services import bom as svc

    monkeypatch.setattr(svc, "search_products", lambda q, limit=20: [{"type_id": 123, "name": "Test Frigate II"}])
    resp = client.get("/bom/search", params={"q": "frag"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["results"][0]["type_id"] == 123


def test_bom_tree_monkeypatched(monkeypatch):
    from app.services import bom as svc

    class N:
        def __init__(self):
            self.type_id = 1; self.product_id = 2; self.activity = "manufacturing"; self.materials = [{"type_id": 34, "qty": 10}]; self.children = []

    monkeypatch.setattr(svc, "build_bom_tree", lambda pid, max_depth=4: N())
    resp = client.get("/bom/tree", params={"product_id": 2})
    assert resp.status_code == 200
    assert resp.json()["product_id"] == 2

