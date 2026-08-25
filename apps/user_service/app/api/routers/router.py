from fastapi import APIRouter


from apps.user_service.app.api.routers import user, admin


router = APIRouter()

router.include_router(user.router, tags=["Users"])
router.include_router(admin.router, tags=["Admin"])
