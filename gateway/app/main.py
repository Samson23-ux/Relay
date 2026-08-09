from fastapi import FastAPI
from httpx import AsyncClient, Limits
from contextlib import asynccontextmanager


from gateway.app.schemas.config import Config
from gateway.core.load_config import load_config
from shared.database.shared_session import redis_client
from shared.core.shared_config import get_global_settings
from gateway.app.middlewares.logging import LoggingMiddleware

GLOBAL_SETTINGS = get_global_settings()


async def raise_for_status(response):
    response.raise_for_status()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis_client

    raw_config = load_config("config.yml")
    app.state.config = Config.model_validate(raw_config)

    limit = Limits(
        max_connections=100, max_keepalive_connections=100, keepalive_expiry=180
    )
    app.state.client = AsyncClient(
        timeout=10, limits=limit, event_hooks={"response": [raise_for_status]}
    )

    yield

    await app.state.redis.aclose()
    await app.state.client.aclose()


app = FastAPI(
    title=GLOBAL_SETTINGS.API_TITLE,
    version=GLOBAL_SETTINGS.API_VERSION,
    description=GLOBAL_SETTINGS.API_DESCRIPTION,
    lifespan=lifespan,
)


app.add_middleware(LoggingMiddleware)


@app.api_route(
    "/{path_name:path}",
    methods=["GET", "POST", "PATCH", "DELETE"],
)
async def relay_endpoint(path_name: str):
    return {"message": f"Path: {path_name} Proxied"}
