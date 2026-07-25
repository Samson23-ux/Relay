from fastapi import FastAPI


from apps.user_service import router
from shared import get_global_settings

SETTINGS = get_global_settings()

app = FastAPI(
    title=SETTINGS.API_TITLE,
    version=SETTINGS.API_VERSION,
    description=SETTINGS.API_DESCRIPTION,
)

app.include_router(router.router)
