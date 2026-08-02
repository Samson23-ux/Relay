from fastapi import APIRouter


from apps.order_service.app.api.routers import cart
from shared.core.shared_config import get_global_settings

GlOBAL_SETTINGS = get_global_settings()

router = APIRouter(prefix=GlOBAL_SETTINGS.API_PREFIX)
router.include_router(cart.router, tags=["Cart"])
