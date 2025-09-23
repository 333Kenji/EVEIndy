"""Shared database helpers."""

from __future__ import annotations

from functools import lru_cache

import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .dependencies import get_settings


@lru_cache
def get_engine() -> Engine:
    """Return a cached SQLAlchemy engine."""

    settings = get_settings()
    return sa.create_engine(settings.database_url)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Return a cached SQLAlchemy session factory bound to the shared engine."""

    engine = get_engine()
    return sessionmaker(bind=engine, future=True)


__all__ = ["get_engine", "get_session_factory"]

