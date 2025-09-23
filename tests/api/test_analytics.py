from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_indicators_endpoint_ok() -> None:
    resp = client.get("/analytics/indicators", params={"type_id": 34, "region_id": 10000002, "window": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert "ma" in data and "bollinger" in data and "volatility" in data


def test_spp_plus_endpoint_ok() -> None:
    payload = {
        "type_id": 603,
        "region_id": 10000002,
        "lead_time_days": 1,
        "horizon_days": 3,
        "batch_options": [1, 2, 3],
    }
    resp = client.post("/analytics/spp_plus", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "spp" in data and "recommended_batch" in data

