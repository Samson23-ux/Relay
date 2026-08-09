from fastapi.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


from gateway.app.schemas.config import Config


class DiscoveryMiddleware(BaseHTTPMiddleware):
    def __init__(self):
        self._upstream_mapping = {
            "auth": "user_service",
            "products": "product_service",
            "orders": "order_service",
        }

    async def dispatch(self, request, call_next):
        endpoint_found = False
        config: Config = request.app.state.config

        request_path = request.url.path
        for route in config.routes:
            if request_path.startswith(route.path):
                exceptions = route.exceptions

                if exceptions:
                    for exception in exceptions:
                        exception_path = exception.path.format(**request.path_params)
                        if (
                            request_path.startswith(exception_path)
                            and exception.method == request.method
                        ):
                            endpoint_found = True

                            upstream = exception_path.split("/")[3]

                            request.state.roles = exception.roles or route.roles
                            request.state.check_role = (
                                exception.check_role or route.check_role
                            )
                            request.state.revoke_token = (
                                exception.revoke_token or route.revoke_token
                            )
                            request.state.auth_required = (
                                exception.auth_required or route.auth_required
                            )
                            request.state.limit.window = (
                                exception.rate_limit.window or route.rate_limit.window
                            )
                            request.state.limit.key_by = (
                                exception.rate_limit.key_by or route.rate_limit.key_by
                            )
                            request.state.upstream = self._upstream_mapping.get(
                                upstream
                            )
                            request.state.limit.requests = (
                                exception.rate_limit.requests
                                or route.rate_limit.requests
                            )
                            break
                else:
                    endpoint_found = True
                    upstream = exception_path.split("/")[3]

                    request.state.roles = route.roles
                    request.state.check_role = route.check_role
                    request.state.revoke_token = route.revoke_token
                    request.state.auth_required = route.auth_required
                    request.state.limit.window = route.rate_limit.window
                    request.state.limit.key_by = route.rate_limit.key_by
                    request.state.limit.requests = route.rate_limit.requests
                    request.state.upstream = self._upstream_mapping.get(upstream)

        if not endpoint_found:
            raise HTTPException(status_code=404, detail="Endpoint not found")

        res = await call_next(request)
        return res
