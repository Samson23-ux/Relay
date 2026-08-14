import time
from uuid import uuid4
from starlette.middleware.base import BaseHTTPMiddleware


from shared.utils import update_db_log


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        span_id = str(uuid4())
        request.state.span_id = span_id
        request.state.parent_span_id = request.headers.get("x-span-id")

        start_time = time.perf_counter()
        res = await call_next(request)
        elapsed = (time.perf_counter() - start_time) * 1000

        latency = f"{elapsed:.2f}ms"

        update_log: dict = {"latency_ms": latency, "status_code": res.status_code}
        update_db_log(request.headers.get("x-trace-id"), span_id, update_log)

        return res
