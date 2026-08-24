import time
from uuid import uuid4
from fastapi import Request
from redis.asyncio import Redis
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    def _limit_script(self) -> str:
        # KEYS -> [set key]
        # ARGV -> [cutoff, current_time(now), route_requests, value(unique_request_id)]
        return """
        redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, ARGV[1])
        local requests = redis.call('ZCOUNT', KEYS[1], ARGV[1], ARGV[2])

        if requests >= tonumber(ARGV[3]) then
            return nil
        end

        return redis.call('ZADD', KEYS[1], ARGV[2], ARGV[4])
        """

    def normalize_request_path(self, request: Request) -> str:
        path_params = request.path_params
        path = request.url.path.split("?")[0]

        for _, v in path_params.items():
            path = path.replace(f"/{v}", "")

        return path

    async def dispatch(self, request, call_next):
        if request.state.limit_requests:
            """
            Lua Script is used to execute all commands as a single
            operation. It blocks all other server activities,
            preventing race conditions.
            """

            redis: Redis = request.app.state.redis
            limit_script = redis.register_script(self._limit_script())

            key_by: str = request.state.key_by
            normalized_path: str = self.normalize_request_path(request)

            if key_by == "ip":
                key_by = request.client.host
            elif key_by == "user_email":
                key_by = request.state.user_email

            now: int = int(time.time() * 1000)

            window_ms: int = int(request.state.window.removesuffix("s")) * 1000
            cutoff: int = now - window_ms

            set_key: str = f"rate_limit:{normalized_path}:{key_by}"

            route_requests = request.state.requests

            res = await limit_script(
                keys=[set_key], args=[cutoff, now, route_requests, str(uuid4())]
            )

            if res is None:
                return JSONResponse(content="Rate limit exceeded", status_code=429)

        res = await call_next(request)
        return res
