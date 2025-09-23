from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_plan_next_window_returns_schedule() -> None:
    payload = {
        "start": "2024-04-01T00:00:00",
        "duration_hours": 24,
        "characters": [
            {
                "character_id": 101,
                "name": "Builder One",
                "activity_slots": {"Manufacturing": 2},
                "time_multipliers": {"Manufacturing": "0.9"},
            }
        ],
        "structures": [
            {"structure_id": "rait", "name": "Raitaru", "activity": "Manufacturing", "time_multiplier": "0.95"}
        ],
        "jobs": [
            {
                "job_id": "t2-hull",
                "type_id": 1234,
                "activity": "Manufacturing",
                "runs": 4,
                "per_run_minutes": "60",
                "batch_size": 2,
            }
        ],
    }
    resp = client.post("/plan/next-window", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["assignments"][0]["character_id"] == 101
    assert data["characters"][0]["activities"]["Manufacturing"]["tasks"]


def test_plan_recommend_endpoint_returns_assignments() -> None:
    payload = {
        "characters": [
            {"character_id": 1, "activity_slots": {"Manufacturing": 1}, "time_multipliers": {"Manufacturing": "1.0"}},
            {"character_id": 2, "activity_slots": {"Manufacturing": 1}, "time_multipliers": {"Manufacturing": "0.8"}},
        ],
        "jobs": [
            {"job_id": "widget", "activity": "Manufacturing", "runs": 2, "per_run_minutes": "30"},
        ],
    }
    resp = client.post("/plan/recommend", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["assignments"][0]["character_id"] == 2

