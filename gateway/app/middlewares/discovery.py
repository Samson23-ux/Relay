import re
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.middleware.base import BaseHTTPMiddleware


from gateway.app.schemas.config import Config
from shared.core.shared_config import get_global_settings

_PARAM_RE = re.compile(r"\{[^/]+\}")
GLOBAL_SETTINGS = get_global_settings()


def _path_pattern(path_template: str) -> re.Pattern:
    """Turn '/api/v1/products/{id}' into a regex matching '/api/v1/products/123' exactly."""
    escaped = re.escape(path_template).replace(r"\{", "{").replace(r"\}", "}")
    return re.compile(f"^{_PARAM_RE.sub(r'[^/]+', escaped)}$")


class DiscoveryMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

        self._upstream_mapping = {
            "auth": "user_service",
            "admin": "user_service",
            "products": "product_service",
            "orders": "order_service",
            "carts": "order_service",
        }

    async def dispatch(self, request, call_next):
        request_path = request.url.path
        request_method = request.method.lower()

        config: Config = request.app.state.config

        matched_route = None
        for route in config.routes:
            if request_path == route.path or request_path.startswith(route.path + "/"):
                matched_route = route
                break  # stop at first matching base route

        if matched_route is None:
            return JSONResponse(content="Endpoint not found", status_code=404)

        if request_method not in matched_route.methods:
            return JSONResponse(content="Method not allowed", status_code=405)

        if matched_route.path == "/docs":
            return get_swagger_ui_html(
                openapi_url="/relay/openapi.json", title=GLOBAL_SETTINGS.API_TITLE
            )

        matched_exception = None
        for exception in matched_route.exceptions:
            if exception.method != request_method:
                continue
            if _path_pattern(exception.path).match(request_path):
                matched_exception = exception
                break

        def pick(exc_val, route_val):
            return exc_val if exc_val is not None else route_val

        request.state.roles = pick(
            matched_exception.roles if matched_exception else None, matched_route.roles
        )
        request.state.revoke_token = pick(
            matched_exception.revoke_token if matched_exception else None,
            matched_route.revoke_token,
        )
        request.state.auth_required = pick(
            matched_exception.auth_required if matched_exception else None,
            matched_route.auth_required,
        )
        request.state.limit_requests = pick(
            matched_exception.limit_requests if matched_exception else None,
            matched_route.limit_requests,
        )

        rate_limit = (
            matched_exception.rate_limit
            if (matched_exception and matched_exception.rate_limit)
            else matched_route.rate_limit
        )
        request.state.window = rate_limit.window if rate_limit else None
        request.state.key_by = rate_limit.key_by if rate_limit else None
        request.state.requests = rate_limit.requests if rate_limit else None

        if matched_route.path == "/relay/openapi.json":
            request.state.request_route = matched_route.path.removeprefix("/relay")
            request.state.upstream = ""
        else:
            # upstream key is the service segment of the route path itself,
            # e.g. "/api/v1/auth" -> "auth" — same for base route and any of its exceptions
            upstream_key = matched_route.path.strip("/").split("/")[-1]

            if matched_route.strip_prefix and request_path.startswith(
                matched_route.strip_prefix
            ):
                request.state.request_route = (
                    request_path[len(matched_route.strip_prefix):] or "/"
                )
            else:
                request.state.request_route = request_path

            request.state.upstream = self._upstream_mapping.get(upstream_key)

        res = await call_next(request)
        return res
