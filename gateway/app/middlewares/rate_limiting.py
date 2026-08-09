import time
from uuid import uuid4
from fastapi import Request
from redis.asyncio import Redis
from fastapi.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    def _limit_script(self) -> str:
        # KEYS -> [set key]
        # ARGV -> [cutoff, current_time]
        return """
        redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, ARGV[1])
        return redis.call('ZCOUNT', KEYS[1], ARGV[1], ARGV[2])
        """

    def _add_script(self) -> str:
        # KEYS -> [set key]
        # ARGV -> [score(now), value(unique_request_id)]
        return """
        redis.call('ZADD', KEYS[1], ARGV[1], ARGV[2])
        """

    def normalize_request_path(self, request: Request) -> str:
        path_params = request.path_params
        path = request.url.path.split("?")[0]

        for _, v in path_params.items():
            path = path.replace(f"/{v}", "")

        return path

    async def dispatch(self, request, call_next):
        """
        Lua Script is used to execute all commands as a single
        operation. It blocks all other server activities,
        preventing race conditions.
        """

        redis: Redis = request.app.state.redis

        add_script = redis.register_script(self._add_script())
        limit_script = redis.register_script(self._limit_script())

        key_by: str = request.state.limit.key_by
        normalized_path: str = self.normalize_request_path(request)

        now: int = int(time.time() * 1000)

        window_ms: int = request.state.limit.window.removesuffix("s") * 1000
        cutoff: int = now - window_ms

        set_key: str = f"rate_limit:{normalized_path}:{key_by}"

        request_count = limit_script(keys=[set_key], args=[cutoff, now])

        if request_count > request.state.limit.requests:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        add_script(keys=[set_key], args=[now, str(uuid4())])

        res = call_next(request)
        return res
