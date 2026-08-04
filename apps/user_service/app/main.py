from fastapi import FastAPI
from contextlib import asynccontextmanager


from apps.user_service.app.api.routers import router
from shared.database.shared_session import redis_client
from shared.middlewares.log import RequestLogMiddleware
from apps.user_service.app.core.security import Security
from shared.core.shared_config import get_global_settings
from shared.core.exception_handlers import GlobalExceptionHandler
from apps.user_service.app.core.exception_handlers import UserExceptionHandler

SECURITY = Security()
SETTINGS = get_global_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await SECURITY.register_oauth()
    app.state.redis = redis_client

    yield

    await app.state.redis.aclose()


app = FastAPI(
    lifespan=lifespan,
    title=SETTINGS.API_TITLE,
    version=SETTINGS.API_VERSION,
    description=SETTINGS.API_DESCRIPTION,
)

app.include_router(router.router)
app.add_middleware(RequestLogMiddleware)

UserExceptionHandler(app).add_handlers()
GlobalExceptionHandler(app).add_handlers()
