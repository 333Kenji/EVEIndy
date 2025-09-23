"""Compatibility layer re-exporting the stateless math core."""

from __future__ import annotations

from indy_math import (
    BollingerBands,
    CostContext,
    CostResult,
    DepthForecast,
    DepthPoint,
    DepthSummary,
    PricePolicy,
    SPPDiagnostics,
    SPPResult,
    bollinger_bands,
    cost_item,
    moving_average,
    recommend_batch_size,
    shallow_depth_metrics,
    simple_volatility,
    spp_lead_time_aware,
)

__all__ = [
    "BollingerBands",
    "CostContext",
    "CostResult",
    "DepthForecast",
    "DepthPoint",
    "DepthSummary",
    "PricePolicy",
    "SPPDiagnostics",
    "SPPResult",
    "bollinger_bands",
    "cost_item",
    "moving_average",
    "recommend_batch_size",
    "shallow_depth_metrics",
    "simple_volatility",
    "spp_lead_time_aware",
]
