"""FastAPI application entrypoint for EVEINDY."""

from __future__ import annotations

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from .sde_autoload import schedule_autoload

from .api import router as api_router
from .dependencies import get_settings

app = FastAPI(title="EVEINDY API", version="0.1.0")
app.include_router(api_router)

# Enable CORS for local frontend dev (Vite default port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def load_settings_cache() -> None:
    """Prime configuration cache during startup."""

    get_settings()
    # Start SDE autoload scheduler
    try:
        schedule_autoload()
    except Exception:
        # Do not crash the app if scheduler fails to start
        pass


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
