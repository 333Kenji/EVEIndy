from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_plan_next_window_validates_and_returns_payload() -> None:
    payload = {"start": "2024-04-01T00:00:00", "duration_hours": 8, "owner_scope": "corp"}
    resp = client.post("/plan/next-window", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "characters" in data and isinstance(data["characters"], list)

