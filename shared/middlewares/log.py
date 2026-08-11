from uuid import uuid4
from starlette.middleware.base import BaseHTTPMiddleware


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        span_id = request.headers.get("x-span-id")
        parent_span_id = span_id

        span_id = str(uuid4())
        request.state.span_id = span_id
        request.state.parent_span_id = parent_span_id

        res = await call_next(request)
        res.headers["parent_span_id"] = parent_span_id

        return res
