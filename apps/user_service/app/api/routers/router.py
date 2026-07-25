from fastapi import APIRouter


from apps.user_service import users
from shared import get_global_settings


router = APIRouter(prefix=get_global_settings().API_PREFIX)

router.include_router(users.router, tags=["Users"])
