from fastapi import APIRouter


from apps.product_service.app.api.routers import product
from shared.core.shared_config import get_global_settings

GlOBAL_SETTINGS = get_global_settings()


router = APIRouter(prefix=GlOBAL_SETTINGS.API_PREFIX)
router.include_router(product.router, tags=["Product"])
