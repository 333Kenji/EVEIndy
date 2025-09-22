"""FastAPI application entrypoint for EVEINDY."""

from __future__ import annotations

from fastapi import FastAPI, status

from .api import router as api_router
from .dependencies import get_settings

app = FastAPI(title="EVEINDY API", version="0.1.0")
app.include_router(api_router)


@app.on_event("startup")
def load_settings_cache() -> None:
    """Prime configuration cache during startup."""

    get_settings()


@app.get("/health/live", status_code=status.HTTP_200_OK, include_in_schema=False)
def health_live() -> dict[str, str]:
    """Return service liveness."""

    return {"status": "live"}


@app.get("/health/ready", status_code=status.HTTP_200_OK, include_in_schema=False)
def health_ready() -> dict[str, str]:
    """Return readiness information, including environment."""

    settings = get_settings()
    return {"status": "ready", "environment": settings.app_env}


@app.get("/health/startup", status_code=status.HTTP_200_OK, include_in_schema=False)
def health_startup() -> dict[str, str]:
    """Return startup probe information."""

    return {"status": "started"}


__all__ = ["app"]
