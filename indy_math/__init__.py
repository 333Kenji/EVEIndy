"""Stateless math core for EVEINDY."""

from .costing import CostContext, CostResult, cost_item
from .indicators import BollingerBands, DepthPoint, DepthSummary, moving_average, bollinger_bands, shallow_depth_metrics, simple_volatility
from .planner import (
    ActivitySchedule,
    Assignment,
    Character,
    CharacterSchedule,
    Facility,
    Job,
    PlanResult,
    PlanningError,
    ScheduledBatch,
    plan_window,
    recommend_assignments,
)
from .spp import (
    DepthForecast,
    PricePolicy,
    SPPDiagnostics,
    SPPResult,
    recommend_batch_size,
    spp_lead_time_aware,
)

__all__ = [
    "CostContext",
    "CostResult",
    "cost_item",
    "BollingerBands",
    "DepthPoint",
    "DepthSummary",
    "moving_average",
    "bollinger_bands",
    "shallow_depth_metrics",
    "simple_volatility",
    "ActivitySchedule",
    "Assignment",
    "Character",
    "CharacterSchedule",
    "Facility",
    "Job",
    "PlanResult",
    "PlanningError",
    "ScheduledBatch",
    "plan_window",
    "recommend_assignments",
    "DepthForecast",
    "PricePolicy",
    "SPPDiagnostics",
    "SPPResult",
    "recommend_batch_size",
    "spp_lead_time_aware",
]
