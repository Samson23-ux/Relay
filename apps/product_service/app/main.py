from fastapi import FastAPI
from contextlib import asynccontextmanager


from apps.product_service.app.api.routers import router
from shared.database.shared_session import redis_client
from shared.middlewares.log import RequestLogMiddleware
from shared.core.shared_config import get_global_settings
from shared.core.exception_handlers import GlobalExceptionHandler
from apps.product_service.app.core.exception_handlers import ProductExceptionHandler

GlOBAL_SETTINGS = get_global_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis_client

    yield

    await app.state.redis.aclose()


app = FastAPI(
    lifespan=lifespan,
    title=GlOBAL_SETTINGS.API_TITLE,
    description=GlOBAL_SETTINGS.API_DESCRIPTION,
    version=GlOBAL_SETTINGS.API_VERSION,
)

app.include_router(router.router)
app.add_middleware(RequestLogMiddleware)

GlobalExceptionHandler(app).add_handlers()
ProductExceptionHandler(app).add_handlers()
