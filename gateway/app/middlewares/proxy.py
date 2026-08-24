import json
import httpx
from fastapi import Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


from shared.repo.redis import RedisRepository
from gateway.app.services.proxy import ProxyService
from gateway.app.core.config import get_relay_settings
from shared.services.request import Request as CustomRequest

RELAY_SETTINGS = get_relay_settings()


class ProxyMIddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    def _build_service(self, request) -> ProxyService:
        return ProxyService(
            config=request.app.state.config,
            redis=RedisRepository(async_redis=request.app.state.redis),
            http_request=CustomRequest(async_client=request.app.state.client),
        )

    async def dispatch(self, request, call_next):
        service = self._build_service(request)
        request_path: str = request.state.request_route

        request_meta: dict = {
            "trace_id": request.state.trace_id,
            "parent_span_id": request.state.span_id,
            "client_ip": request.client.host,
            "upstream": "proxy",
            "method": request.method,
            "path": request_path,
        }

        headers: dict = {
            "x-trace-id": request.state.trace_id,
            "x-route-roles": json.dumps(request.state.roles),
        }

        if request.state.auth_required:
            headers["x-user-type"] = request.state.user_type
            headers["x-user-email"] = request.state.user_email

        upstream_instance: str | list[str] = request.state.upstream_instance

        if request_path == "/openapi.json":
            res: Response | JSONResponse = await service.merge_docs(
                request,
                upstream_instance,
                request_path,
                headers,
                request_meta,
            )
        else:
            res: httpx.Response | JSONResponse = await service.make_request(
                request,
                request_path,
                upstream_instance,
                headers,
                request_meta,
            )

        response_headers = {
            k: v
            for k, v in res.headers.items()
            if k.lower() not in RELAY_SETTINGS.HOP_BY_HOP_HEADERS
        }

        return Response(
            content=res.content if isinstance(res, httpx.Response) else res.body,
            status_code=res.status_code,
            headers=response_headers,
            media_type=response_headers.get("content-type"),
        )
