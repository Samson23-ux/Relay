from fastapi import FastAPI
from httpx import AsyncClient, Limits
from contextlib import asynccontextmanager


from apps.order_service.app.api.routers import router
from shared.database.shared_session import redis_client
from shared.core.shared_config import get_global_settings
from shared.core.exception_handlers import GlobalExceptionHandler
from apps.order_service.app.core.exception_handlers import OrderExceptionHandler

GlOBAL_SETTINGS = get_global_settings()


async def raise_for_status(response):
    response.raise_for_status()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis_client

    limit = Limits(
        max_connections=100, max_keepalive_connections=100, keepalive_expiry=300
    )
    app.state.client = AsyncClient(
        timeout=10, event_hooks={"response": [raise_for_status]}, limits=limit
    )

    yield

    await app.state.redis.aclose()
    await app.state.client.aclose()


app = FastAPI(
    title=GlOBAL_SETTINGS.API_TITLE,
    description=GlOBAL_SETTINGS.API_DESCRIPTION,
    version=GlOBAL_SETTINGS.API_VERSION,
)

app.include_router(router.router)


OrderExceptionHandler(app).add_handlers()
GlobalExceptionHandler(app).add_handlers()
