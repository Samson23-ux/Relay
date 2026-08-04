from fastapi import FastAPI
from contextlib import asynccontextmanager


from shared.database.shared_session import redis_client
from shared.core.shared_config import get_global_settings

GLOBAL_SETTINGS = get_global_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis_client

    yield

    await app.state.redis.aclose()


app = FastAPI(
    title=GLOBAL_SETTINGS.API_TITLE,
    version=GLOBAL_SETTINGS.API_VERSION,
    description=GLOBAL_SETTINGS.API_DESCRIPTION,
    lifespan=lifespan,
)


@app.api_route(
    "/{path_name:path}",
    methods=["GET", "POST", "PATCH", "DELETE"],
)
async def relay_endpoint(path_name: str):
    return {"message": f"Path: {path_name} Proxied"}
