from fastapi import APIRouter


from apps.user_service.app.api.routers import user, admin
from shared.core.shared_config import get_global_settings


router = APIRouter(prefix=get_global_settings().API_PREFIX)

router.include_router(user.router, tags=["Users"])
router.include_router(admin.router, tags=["Admin"])
