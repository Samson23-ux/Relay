import asyncio
import logging
from pathlib import Path
from fastapi import FastAPI
from redis.asyncio import Redis
from httpx import AsyncClient, Limits
from contextlib import asynccontextmanager


from gateway.app.schemas.config import Config
from shared.repo.redis import RedisRepository
from gateway.app.core.load_config import load_config
from shared.database.shared_session import redis_client
from shared.core.shared_config import get_global_settings
from gateway.app.middlewares.proxy import ProxyMIddleware
from gateway.app.middlewares.logging import LoggingMiddleware
from gateway.app.services.circuit_breaker import CircuitBreaker
from gateway.app.middlewares.authentication import AuthMiddleware
from gateway.app.middlewares.discovery import DiscoveryMiddleware
from gateway.app.middlewares.rate_limiting import RateLimitMiddleware
from gateway.app.middlewares.load_balancer import LoadBalancerMiddleware
from gateway.app.middlewares.circuit_breaker import CircuitBreakerMiddleware

GLOBAL_SETTINGS = get_global_settings()
GATEWAY_CONFIG_KEY = "gateway:config"
GATEWAY_CONFIG_CHANNEL = "gateway:config:reload"

logger = logging.getLogger(__name__)


async def raise_for_status(response):
    if not response.is_redirect:
        response.raise_for_status()


async def load_gateway_config(redis: Redis) -> Config:
    redis_repo = RedisRepository(async_redis=redis)
    raw = await redis_repo.get_key(GATEWAY_CONFIG_KEY)
    if raw:
        return Config.model_validate_json(raw)

    path = Path(__file__).parent / "core" / "config.yml"
    raw_config = load_config(path)
    config = Config.model_validate(raw_config)
    await redis_repo.set_key(GATEWAY_CONFIG_KEY, config.model_dump_json())
    return config


async def watch_config_reloads(app: FastAPI, redis: Redis):
    """Keep app.state.config in sync with Redis across process boundaries.

    Runs for the life of the process; resubscribes with a backoff if the
    pubsub connection drops, since a dead listener would otherwise leave
    config silently stale forever.
    """
    while True:
        try:
            pubsub = redis.pubsub()
            async with pubsub:
                await pubsub.subscribe(GATEWAY_CONFIG_CHANNEL)

                async for message in pubsub.listen():
                    if message["type"] != "message":
                        continue
                    try:
                        app.state.config = await load_gateway_config(redis)
                    except Exception:
                        logger.exception("Failed to apply reloaded gateway config")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Gateway config listener disconnected, retrying")
            await asyncio.sleep(1)


async def create_instance_circuit(app: FastAPI):
    config: Config = app.state.config
    redis = RedisRepository(async_redis=app.state.redis)
    circuit_breaker = CircuitBreaker(redis=redis, config=config.circuit_breaker)

    for upstream in config.upstreams:
        for instance in upstream.instances:
            await circuit_breaker.initialize(instance)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis_client
    app.state.config = await load_gateway_config(app.state.redis)

    limit = Limits(
        max_connections=100,
        keepalive_expiry=180,
        max_keepalive_connections=100,
    )
    app.state.client = AsyncClient(
        timeout=10,
        limits=limit,
        event_hooks={
            "response": [raise_for_status]
        },
    )

    await create_instance_circuit(app)
    config_listener = asyncio.create_task(
        watch_config_reloads(app, app.state.redis)
    )

    yield

    config_listener.cancel()
    try:
        await config_listener
    except asyncio.CancelledError:
        pass

    await app.state.redis.aclose()
    await app.state.client.aclose()


app = FastAPI(
    title=GLOBAL_SETTINGS.API_TITLE,
    version=GLOBAL_SETTINGS.API_VERSION,
    description=GLOBAL_SETTINGS.API_DESCRIPTION,
    lifespan=lifespan,
)


app.add_middleware(ProxyMIddleware)
app.add_middleware(CircuitBreakerMiddleware)
app.add_middleware(LoadBalancerMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(DiscoveryMiddleware)
app.add_middleware(LoggingMiddleware)


@app.api_route(
    "/{path_name:path}",
    methods=["GET", "POST", "PATCH", "DELETE"],
)
async def relay_endpoint(path_name: str):
    return {"message": f"Path: {path_name} Proxied"}
