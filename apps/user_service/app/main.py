from fastapi import FastAPI


from apps.user_service.app.api.routers import router
from shared.core.shared_config import get_global_settings
from shared.core.exception_handlers import GlobalExceptionHandler
from apps.user_service.app.core.exception_handlers import UserExceptionHandler

SETTINGS = get_global_settings()

app = FastAPI(
    title=SETTINGS.API_TITLE,
    version=SETTINGS.API_VERSION,
    description=SETTINGS.API_DESCRIPTION,
)

app.include_router(router.router)

UserExceptionHandler(app).add_handlers()
GlobalExceptionHandler(app).add_handlers()
