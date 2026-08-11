from starlette.middleware.base import BaseHTTPMiddleware


from gateway.app.schemas.config import Config
from shared.repo.redis import RedisRepository


class LoadBalancerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

        self._redis = None

    async def dispatch(self, request, call_next):
        config: Config = request.app.state.config
        self._redis = RedisRepository(async_redis=request.app.state.redis)

        instances = []
        upstream = request.state.upstream

        for u in config.upstreams:
            if u.name == upstream:
                instances = u.instances
                break

        instance = None
        last_seen_value = float("+inf")

        for i in instances:
            key: str = f"upstream:instance:{i}"

            curr_value = await self._redis.get_key(key)

            if curr_value is None:
                curr_value = "0"
                await self._redis.set_key(key, curr_value)

            if last_seen_value > int(curr_value):
                instance = i

            last_seen_value = min(last_seen_value, int(curr_value))

        request.state.upstream_instance = instance

        res = await call_next(request)
        return res
