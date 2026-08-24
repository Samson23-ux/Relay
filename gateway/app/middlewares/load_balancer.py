from starlette.middleware.base import BaseHTTPMiddleware


from gateway.app.schemas.config import Config
from shared.repo.redis import RedisRepository
from gateway.app.core.config import get_relay_settings

RELAY_SETTINGS = get_relay_settings()


class LoadBalancerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

        self._redis = None

    async def select_request_instance(self, request):
        """
        The instance with the least amount of request
        being processed is selected
        """
        config: Config = request.app.state.config

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

    async def select_doc_instances(self, request):
        config: Config = request.app.state.config

        upstreams = []
        upstream_instances = []
        selected_instances = []

        for upstream in config.upstreams:
            upstreams.append(upstream.name)
            upstream_instances.append([*upstream.instances])

        request.state.upstream = upstreams

        for upstream_instance in upstream_instances:
            curr_instance = None
            last_seen_value = float("+inf")

            for instance in upstream_instance:
                key: str = f"upstream:instance:{instance}"
                curr_value = await self._redis.get_key(key)

                if curr_value is None:
                    curr_value = "0"
                    await self._redis.set_key(key, curr_value)

                if last_seen_value > int(curr_value):
                    curr_instance = instance

                last_seen_value = min(last_seen_value, int(curr_value))
            selected_instances.append(curr_instance)

        request.state.upstream_instance = selected_instances

    async def dispatch(self, request, call_next):
        self._redis = RedisRepository(async_redis=request.app.state.redis)

        if request.state.request_route == "/openapi.json":
            await self.select_doc_instances(request)
        else:
            await self.select_request_instance(request)

        res = await call_next(request)
        return res
