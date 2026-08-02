from fastapi import APIRouter


from shared.core.shared_config import get_global_settings
from apps.order_service.app.api.routers import cart, order

GlOBAL_SETTINGS = get_global_settings()

router = APIRouter(prefix=GlOBAL_SETTINGS.API_PREFIX)
router.include_router(cart.router, tags=["Cart"])
router.include_router(order.router, tags=["Order"])
