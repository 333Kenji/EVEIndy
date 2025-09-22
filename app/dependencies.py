"""Dependency helpers for the FastAPI service."""

from __future__ import annotations

from functools import lru_cache

from .config import Settings


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()


__all__ = ["get_settings"]
