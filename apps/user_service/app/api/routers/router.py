from fastapi import APIRouter


from apps.user_service import user
from shared import get_global_settings


router = APIRouter(prefix=get_global_settings().API_PREFIX)

router.include_router(user.router, tags=["Users"])
