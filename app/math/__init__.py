"""Pure math helpers placeholder.

Functions here must stay side-effect free so unit tests can enforce determinism.
"""

from __future__ import annotations

from typing import Sequence


def identity(value: float) -> float:
    """Return the supplied value unchanged."""

    return value


def mean(values: Sequence[float]) -> float:
    """Compute a deterministic arithmetic mean for non-empty sequences."""

    if not values:
        raise ValueError("values must contain at least one entry")
    return sum(values) / len(values)


__all__ = ["identity", "mean"]
