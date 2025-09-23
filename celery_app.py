from __future__ import annotations

import os

from celery import Celery

celery_app = Celery(
    "eveindy",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

celery_app.conf.task_routes = {
    "tasks.price_refresh": {"queue": "price"},
    "tasks.indices_refresh": {"queue": "indices"},
    "tasks.esi_sync": {"queue": "esi"},
    "tasks.indicators": {"queue": "indicators"},
    "tasks.alerts": {"queue": "alerts"},
}

