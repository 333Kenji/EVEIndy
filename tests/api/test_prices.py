from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_prices_quotes_mocks_service(monkeypatch) -> None:
    # Mock latest_quotes to avoid DB dependency
    from app.services import prices as svc

    def fake_latest_quotes(region_id: int, type_ids: list[int]):
        class Q:
            def __init__(self, t):
                self.type_id = t
                self.region_id = region_id
                self.bid = Decimal("5")
                self.ask = Decimal("6")
                self.mid = Decimal("5.5")
                self.bid_qty = Decimal("100")
                self.ask_qty = Decimal("80")
                self.depth_qty_1pct = Decimal("250")
                self.depth_qty_5pct = Decimal("1000")
                self.stdev_pct = Decimal("0.02")
                self.spread = Decimal("1")
                from datetime import datetime

                self.ts = datetime(2024, 1, 1)

        return [Q(t) for t in type_ids]

    monkeypatch.setattr(svc, "latest_quotes", fake_latest_quotes)
    resp = client.post("/prices/quotes", json={"region_id": 10000002, "type_ids": [34, 35]})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["quotes"]) == 2
    assert body["quotes"][0]["mid"] == "5.5"
    assert body["quotes"][0]["spread"] == "1"

