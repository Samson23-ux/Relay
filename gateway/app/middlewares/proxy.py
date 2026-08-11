import time
import httpx
from enum import Enum
from json import JSONDecodeError
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta, timezone
from starlette.middleware.base import BaseHTTPMiddleware


from shared.utils import log_info
from gateway.app.schemas.config import Config
from shared.repo.redis import RedisRepository
from shared.services.request import Request as CustomRequest


class CircuitState(str, Enum):
    OPEN = "open"
    HALFOPEN = "half_open"
    CLOSED = "closed"


class ProxyMIddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

        self._redis = None

    async def make_request(
        self, url: str, headers: dict, request: Request, http_request: CustomRequest
    ) -> tuple[httpx.Response, int]:
        retries = 0
        form: dict = await request.form()
        cookies: dict = request.cookies
        params: dict = request.query_params

        data: dict | None = dict(form) if form else None

        try:
            json: dict = await request.json()
        except JSONDecodeError:
            json = None

        if request.method == "GET":
            res: httpx.Response = await http_request.get(url, params, headers, cookies)
            retries = http_request.get.retry.statistics["attempt_number"] - 1
        elif request.method == "POST":
            res: httpx.Response = await http_request.post(
                url, params, data, json, headers, cookies
            )
        elif request.method == "PATCH":
            res: httpx.Response = await http_request.patch(
                url, params, data, json, headers, cookies
            )
        elif request.method == "DELETE":
            res: httpx.Response = await http_request.delete(
                url, params, headers, cookies
            )

        return res, retries

    async def dispatch(self, request, call_next):
        config: Config = request.app.state.config
        self._redis = RedisRepository(async_redis=request.app.state.redis)
        http_request = CustomRequest(async_client=request.app.state.client)

        breaker_key: str = f"circuit:{request.state.upstream_instance}"

        circuit = await self._redis.get_hset(breaker_key)

        if not circuit:
            circuit = {
                "failures": 0,
                "state": CircuitState.CLOSED,
                "retry_at": "None",
                "half_open_requests": 0,
            }
            await self._redis.create_hset(breaker_key, circuit)

        circuit["failures"] = int(circuit["failures"])
        circuit["half_open_requests"] = int(circuit["half_open_requests"])

        request_meta: dict = {
            "trace_id": request.state.trace_id,
            "span_id": request.state.span_id,
            "parent_span_id": request.state.parent_span_id,
            "client_ip": request.client.host,
            "upstream": request.state.upstream,
            "method": request.method,
            "path": request.url.path,
        }

        try:
            if circuit["state"] == CircuitState.OPEN:
                return JSONResponse(
                    content="Service Unavailable",
                    status_code=503,
                    headers={"retry_after": circuit["retry_at"]},
                )
            elif (
                circuit["state"] == CircuitState.HALFOPEN
                and circuit["half_open_requests"]
                >= config.circuit_breaker.half_open_requests
            ):
                return JSONResponse(
                    content="Service Unavailable",
                    status_code=503,
                    headers={"retry_after": circuit["retry_at"]},
                )

            upstream_instance: str = request.state.upstream_instance

            url: str = f"{upstream_instance}{request.url.path}"

            headers: dict = {
                "x-trace-id": request.state.trace_id,
                "x-span-id": request.state.span_id,
                "x-upstream": request.state.upstream,
                "x-upstream-instance": upstream_instance,
            }

            if request.state.auth_required:
                headers["x-user-type"] = request.state.user_type
                headers["x-user-email"] = request.state.user_email

            instance_key: str = f"upstream:instance:{upstream_instance}"
            total_requests = await self._redis.increment_counter(instance_key)

            start_time = time.perf_counter()
            res, retries = await self.make_request(url, headers, request, http_request)
            elapsed = (time.perf_counter() - start_time) * 1000

            total_str = str(elapsed)[:2]
            total = int(total_str.removesuffix("."))

            message = "Response received"
            request_meta["retries"] = retries
            request_meta["status_code"] = res.status_code
            request_meta["latency_ms"] = int(total)

            log_info(message, request_meta)

            if total_requests > 0:
                await self._redis.decrement_counter(instance_key)
            await self._redis.create_hset(breaker_key, {"failures": 0})

            HOP_BY_HOP_HEADERS = {
                "connection",
                "keep-alive",
                "proxy-authenticate",
                "proxy-authorization",
                "te",
                "trailers",
                "transfer-encoding",
                "upgrade",
                "content-length",
            }

            response_headers = {
                k: v
                for k, v in res.headers.items()
                if k.lower() not in HOP_BY_HOP_HEADERS
            }

            return Response(
                content=res.content,
                status_code=res.status_code,
                headers=response_headers,
                media_type=res.headers.get("content-type"),
            )
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code

            if status_code >= 500:
                circuit["failures"] += 1

                if circuit["failures"] >= config.circuit_breaker.failure_threshold:
                    recovery_timeout = int(
                        config.circuit_breaker.recovery_timeout.removesuffix("s")
                    )

                    retry_at = datetime.now(timezone.utc) + timedelta(
                        seconds=recovery_timeout
                    )

                    await self._redis.create_hset(
                        breaker_key,
                        {
                            "failures": circuit["failures"],
                            "half_open_requests": 0,
                            "state": CircuitState.OPEN,
                            "retry_at": retry_at,
                        },
                    )

                    message = "Service Unavailable"
                    request_meta["status_code"] = 503

                    log_info(message, request_meta)
                    return JSONResponse(
                        content="Service Unavailable",
                        status_code=503,
                        headers={"retry_after": retry_at},
                    )

                await self._redis.create_hset(
                    breaker_key, {"failures": circuit["failures"]}
                )
                message = "Error occured while processing request"

                request_meta["status_code"] = status_code
                log_info(message, request_meta)

                return JSONResponse(
                    content="Internal Server Error", status_code=status_code
                )

            message = exc.response.reason_phrase
            request_meta["status_code"] = status_code

            log_info(message, request_meta)

            return JSONResponse(
                content=exc.response.reason_phrase, status_code=status_code
            )
        except Exception as exc:
            message = str(exc)
            request_meta["status_code"] = 500

            log_info(message, request_meta)
            return JSONResponse(content="Internal Server Error", status_code=500)
