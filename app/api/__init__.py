"""Application API routers."""

from fastapi import APIRouter
from .routes.analytics import router as analytics_router
from .routes.plan import router as plan_router
from .routes.prices import router as prices_router
from .routes.metrics import router as metrics_router
from .routes.bom import router as bom_router
from .routes.ui_state import router as ui_router
from .routes.systems import router as systems_router
from .routes.structures import router as structures_router
from .routes.inventory import router as inventory_router
from .routes.market import router as market_router

router = APIRouter()
router.include_router(analytics_router)
router.include_router(plan_router)
router.include_router(prices_router)
router.include_router(metrics_router)
router.include_router(bom_router)
router.include_router(ui_router)
router.include_router(systems_router)
router.include_router(structures_router)
router.include_router(inventory_router)
router.include_router(market_router)

__all__ = ["router"]
