from uuid import uuid4
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        span_id = request.headers.get("span_id")
        parent_span_id = span_id

        span_id = uuid4()
        request.state.span_id = span_id
        request.state.parent_span_id = parent_span_id

        res = await call_next(request)

        return res
