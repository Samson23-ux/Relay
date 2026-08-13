import time
from uuid import uuid4
from starlette.middleware.base import BaseHTTPMiddleware


from shared.utils import log_info, update_db_log


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request.state.trace_id = str(uuid4())
        request.state.span_id = str(uuid4())
        request.state.parent_span_id = None

        start_time = time.perf_counter()
        res = await call_next(request)

        elapsed = (time.perf_counter() - start_time) * 1000
        total_str = str(elapsed)[:2]
        total = int(total_str.removesuffix("."))

        message = "Gateway response received"
        request_meta: dict = {
            "trace_id": request.state.trace_id,
            "span_id": request.state.span_id,
            "parent_span_id": request.state.parent_span_id,
            "client_ip": request.client.host,
            "upstream": "relay",
            "method": request.method,
            "path": request.url.path,
            "status_code": res.status_code,
            "latency_ms": int(total)
        }

        if res.status_code == 429:
            request_meta["rate_limited"] = True

        log_info(message, request_meta)

        return res
