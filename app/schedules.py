from __future__ import annotations

from datetime import timedelta


SCHEDULE = {
    "price_refresh": {"task": "tasks.price_refresh", "interval": timedelta(minutes=12)},
    "indices_refresh": {"task": "tasks.indices_refresh", "cron": "0 11 * * *"},
    "esi_jobs_sync": {"task": "tasks.esi_sync", "interval": timedelta(minutes=30)},
    "assets_sync": {"task": "tasks.esi_sync", "interval": timedelta(minutes=60)},
    "indicators": {"task": "tasks.indicators", "interval": timedelta(hours=1)},
    "alerts": {"task": "tasks.alerts", "interval": timedelta(minutes=15)},
}

