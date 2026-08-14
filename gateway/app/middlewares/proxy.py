import time
import json
import httpx
from enum import Enum
from uuid import uuid4
from json import JSONDecodeError
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta, timezone
from starlette.middleware.base import BaseHTTPMiddleware


from shared.utils import log_info, log_error
from gateway.app.schemas.config import Config
from shared.repo.redis import RedisRepository
from gateway.app.core.config import get_relay_settings
from shared.services.request import Request as CustomRequest

RELAY_SETTINGS = get_relay_settings()


class CircuitState(str, Enum):
    OPEN = "open"
    HALFOPEN = "half_open"
    CLOSED = "closed"


class ProxyMIddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

        self._redis = None
        self._config = None
        self._http_request = None

    def _set_attr(self, request):
        self._config: Config = request.app.state.config
        self._redis = RedisRepository(async_redis=request.app.state.redis)
        self._http_request = CustomRequest(async_client=request.app.state.client)

    def _log_request(
        self,
        level: str,
        request_meta: dict,
        message: str,
        retries: int,
        status_code: int,
        latency: int,
        circuit: dict,
    ):
        request_meta["retries"] = retries
        request_meta["latency_ms"] = latency
        request_meta["status_code"] = status_code

        if level == "info":
            log_info(message, request_meta, circuit)
        else:
            log_error(message, request_meta, circuit)

    async def make_request(
        self,
        request: Request,
        request_path: str,
        upstream_instance: str,
        headers: dict,
        request_meta: dict,
        breaker_key: str,
        circuit: dict,
    ) -> httpx.Response:
        retries = 0
        start_time = 0

        cookies: dict = request.cookies
        form: dict = await request.form()
        params: dict = request.query_params

        data: dict | None = dict(form) if form else None

        try:
            json: dict = await request.json()
        except JSONDecodeError:
            json = None

        url: str = f"{upstream_instance}{request_path}"
        upstream: str | list[str] = request.state.upstream

        span_id = str(uuid4())
        request_meta["span_id"] = span_id

        headers["x-span-id"] = span_id
        headers["x-upstream"] = upstream
        headers["x-upstream-instance"] = upstream_instance

        try:
            instance_key: str = f"upstream:instance:{upstream_instance}"
            total_requests = await self._redis.increment_counter(instance_key)

            if request.method == "GET":
                start_time = time.perf_counter()
                res: httpx.Response = await self._http_request.get(
                    url, params, headers, cookies
                )
                elapsed = (time.perf_counter() - start_time) * 1000

                retries = self._http_request.get.statistics["attempt_number"] - 1
            elif request.method == "POST":
                start_time = time.perf_counter()
                res: httpx.Response = await self._http_request.post(
                    url, params, data, json, headers, cookies
                )
                elapsed = (time.perf_counter() - start_time) * 1000
            elif request.method == "PATCH":
                start_time = time.perf_counter()
                res: httpx.Response = await self._http_request.patch(
                    url, params, data, json, headers, cookies
                )
                elapsed = (time.perf_counter() - start_time) * 1000
            elif request.method == "DELETE":
                start_time = time.perf_counter()
                res: httpx.Response = await self._http_request.delete(
                    url, params, headers, cookies
                )
                elapsed = (time.perf_counter() - start_time) * 1000

            latency = f"{elapsed:.2f}ms"
            message = "Response received successfully"

            self._log_request(
                "info",
                request_meta,
                message,
                retries,
                res.status_code,
                latency,
                circuit,
            )

            if total_requests > 0:
                await self._redis.decrement_counter(instance_key)
            await self._redis.create_hset(breaker_key, {"failures": 0})

            return res
        except httpx.HTTPStatusError as exc:
            if total_requests > 0:
                await self._redis.decrement_counter(instance_key)

            elapsed = (time.perf_counter() - start_time) * 1000
            latency = f"{elapsed:.2f}ms"

            status_code = exc.response.status_code

            if status_code >= 500:
                circuit["failures"] += 1

                if (
                    circuit["failures"]
                    >= self._config.circuit_breaker.failure_threshold
                ):
                    recovery_timeout = int(
                        self._config.circuit_breaker.recovery_timeout.removesuffix("s")
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

                    self._log_request(
                        "error",
                        request_meta,
                        message,
                        retries,
                        503,
                        latency,
                        circuit,
                    )
                    return JSONResponse(
                        content="Service Unavailable",
                        status_code=503,
                        headers={"retry_after": retry_at},
                    )

                await self._redis.create_hset(
                    breaker_key, {"failures": circuit["failures"]}
                )
                message = "Error occured while processing request"

                self._log_request(
                    "error",
                    request_meta,
                    message,
                    retries,
                    status_code,
                    latency,
                    circuit,
                )
                return JSONResponse(
                    content="Internal Server Error", status_code=status_code
                )

            if status_code == 429:
                request_meta["rate_limited"] = True

            message = exc.response.reason_phrase
            self._log_request(
                "error",
                request_meta,
                message,
                retries,
                status_code,
                latency,
                circuit,
            )
            return JSONResponse(
                content=exc.response.reason_phrase, status_code=status_code
            )
        except Exception as exc:
            if total_requests > 0:
                await self._redis.decrement_counter(instance_key)

            elapsed = (time.perf_counter() - start_time) * 1000
            latency = f"{elapsed:.2f}ms"

            message = str(exc)

            self._log_request(
                "error",
                request_meta,
                message,
                retries,
                500,
                latency,
                circuit,
            )
            return JSONResponse(content="Internal Server Error", status_code=500)

    async def merge_docs(
        self,
        request: Request,
        instances: list[str],
        request_path: str,
        headers: dict,
        request_meta: dict,
        breaker_key: str,
        circuit: dict,
    ) -> Response:
        retries = 0
        start_time = 0

        merged_doc = {}
        res_headers = {}

        try:
            for i in range(len(instances)):
                span_id = str(uuid4())
                request_meta["span_id"] = span_id

                upstream_instance = instances[i]
                upstream = request.state.upstream[i]

                url: str = f"{upstream_instance}{request_path}"

                headers["x-span-id"] = span_id
                headers["x-upstream"] = upstream
                headers["x-upstream-instance"] = upstream_instance

                instance_key: str = f"upstream:instance:{upstream_instance}"
                total_requests = await self._redis.increment_counter(instance_key)

                start_time = time.perf_counter()
                res: httpx.Response = await self._http_request.get(url, headers=headers)
                elapsed = (time.perf_counter() - start_time) * 1000

                retries = self._http_request.get.statistics["attempt_number"] - 1

                try:
                    json_res = res.json()
                except json.JSONDecodeError:
                    return JSONResponse(
                        content="Internal server error", status_code=500
                    )

                res_headers.update(**res.headers)

                if not merged_doc:
                    merged_doc.update(**json_res)
                else:
                    merged_doc["paths"].update(**json_res["paths"])
                    merged_doc["components"]["schemas"].update(
                        **json_res["components"]["schemas"]
                    )

                message = "Response received successfully"
                latency = f"{elapsed:.2f}ms"

                self._log_request(
                    "info",
                    request_meta,
                    message,
                    retries,
                    res.status_code,
                    latency,
                    circuit,
                )

                if total_requests > 0:
                    await self._redis.decrement_counter(instance_key)
                await self._redis.create_hset(breaker_key, {"failures": 0})

            response_headers = {
                k: v
                for k, v in res_headers.items()
                if k.lower() not in RELAY_SETTINGS.HOP_BY_HOP_HEADERS
            }

            content = json.dumps(merged_doc).encode()
            return Response(
                content=content,
                status_code=res.status_code,
                headers=response_headers,
                media_type=res.headers.get("content-type"),
            )
        except httpx.HTTPStatusError as exc:
            if total_requests > 0:
                await self._redis.decrement_counter(instance_key)

            elapsed = (time.perf_counter() - start_time) * 1000
            latency = f"{elapsed:.2f}ms"

            status_code = exc.response.status_code

            if status_code >= 500:
                circuit["failures"] += 1

                if (
                    circuit["failures"]
                    >= self._config.circuit_breaker.failure_threshold
                ):
                    recovery_timeout = int(
                        self._config.circuit_breaker.recovery_timeout.removesuffix("s")
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

                    self._log_request(
                        "error",
                        request_meta,
                        message,
                        retries,
                        503,
                        latency,
                        circuit,
                    )
                    return JSONResponse(
                        content="Service Unavailable",
                        status_code=503,
                        headers={"retry_after": retry_at},
                    )

                await self._redis.create_hset(
                    breaker_key, {"failures": circuit["failures"]}
                )
                message = "Error occured while processing request"

                self._log_request(
                    "error",
                    request_meta,
                    message,
                    retries,
                    status_code,
                    latency,
                    circuit,
                )
                return JSONResponse(
                    content="Internal Server Error", status_code=status_code
                )

            if status_code == 429:
                request_meta["rate_limited"] = True

            message = exc.response.reason_phrase
            self._log_request(
                "error",
                request_meta,
                message,
                retries,
                status_code,
                latency,
                circuit,
            )

            return JSONResponse(
                content=exc.response.reason_phrase, status_code=status_code
            )
        except Exception as exc:
            if total_requests > 0:
                await self._redis.decrement_counter(instance_key)

            elapsed = (time.perf_counter() - start_time) * 1000
            latency = f"{elapsed:.2f}ms"

            message = str(exc)

            self._log_request(
                "error",
                request_meta,
                message,
                retries,
                500,
                latency,
                circuit,
            )
            return JSONResponse(content="Internal Server Error", status_code=500)

    async def dispatch(self, request, call_next):
        self._set_attr(request)

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

        request_path: str = request.state.request_route

        request_meta: dict = {
            "trace_id": request.state.trace_id,
            "parent_span_id": request.state.span_id,
            "client_ip": request.client.host,
            "upstream": "proxy",
            "method": request.method,
            "path": request_path,
        }

        if circuit["state"] == CircuitState.OPEN:
            return JSONResponse(
                content="Service Unavailable",
                status_code=503,
                headers={"retry_after": circuit["retry_at"]},
            )
        elif (
            circuit["state"] == CircuitState.HALFOPEN
            and circuit["half_open_requests"]
            >= self._config.circuit_breaker.half_open_requests
        ):
            return JSONResponse(
                content="Service Unavailable",
                status_code=503,
                headers={"retry_after": circuit["retry_at"]},
            )

        headers: dict = {"x-trace-id": request.state.trace_id}

        if request.state.auth_required:
            headers["x-user-type"] = request.state.user_type
            headers["x-user-email"] = request.state.user_email

        upstream_instance: str | list[str] = request.state.upstream_instance

        if request_path == "/openapi.json":
            res: Response | JSONResponse = await self.merge_docs(
                request,
                upstream_instance,
                request_path,
                headers,
                request_meta,
                breaker_key,
                circuit,
            )
        else:
            res: httpx.Response | JSONResponse = await self.make_request(
                request,
                request_path,
                upstream_instance,
                headers,
                request_meta,
                breaker_key,
                circuit,
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
