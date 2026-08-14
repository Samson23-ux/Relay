from fastapi import FastAPI
from contextlib import asynccontextmanager


from apps.user_service.app.api.routers import router
from shared.database.shared_session import redis_client
from shared.middlewares.log import RequestLogMiddleware
from apps.user_service.app.core.security import Security
from shared.core.shared_config import get_global_settings
from starlette.middleware.sessions import SessionMiddleware
from apps.user_service.app.core.config import get_user_settings
from shared.core.exception_handlers import GlobalExceptionHandler
from apps.user_service.app.core.exception_handlers import UserExceptionHandler

SECURITY = Security()
USER_SETTINGS = get_user_settings()
GLOBAL_SETTINGS = get_global_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await SECURITY.register_oauth()
    app.state.redis = redis_client

    yield

    await app.state.redis.aclose()


app = FastAPI(
    lifespan=lifespan,
    title=GLOBAL_SETTINGS.API_TITLE,
    version=GLOBAL_SETTINGS.API_VERSION,
    description=GLOBAL_SETTINGS.API_DESCRIPTION,
)

app.include_router(router.router)
app.add_middleware(
    SessionMiddleware,
    max_age=900,
    same_site="lax",
    secret_key=USER_SETTINGS.SESSION_SECRET_KEY,
    https_only=GLOBAL_SETTINGS.ENVIRONMENT == "production",
)
app.add_middleware(RequestLogMiddleware)

UserExceptionHandler(app).add_handlers()
GlobalExceptionHandler(app).add_handlers()
