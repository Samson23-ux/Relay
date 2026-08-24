import time
import json
import httpx
from uuid import uuid4
from json import JSONDecodeError
from fastapi import Request, Response
from fastapi.responses import JSONResponse


from shared.utils import log_info, log_error
from gateway.app.schemas.config import Config
from shared.repo.redis import RedisRepository
from gateway.app.core.config import get_relay_settings
from shared.services.request import Request as CustomRequest
from gateway.app.services.circuit_breaker import CircuitBreaker

RELAY_SETTINGS = get_relay_settings()


class ProxyService:
    def __init__(
        self,
        config: Config,
        redis: RedisRepository,
        http_request: CustomRequest,
    ):
        self._config = config
        self._redis = redis
        self._http_request = http_request

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
    ) -> httpx.Response | JSONResponse:
        retries = 0
        start_time = 0

        circuit_breaker: CircuitBreaker = request.state.circuit_breaker
        circuit: dict = request.state.circuits[upstream_instance]

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

            await circuit_breaker.record_success(upstream_instance, circuit)
            return res
        except httpx.HTTPStatusError as exc:
            if total_requests > 0:
                await self._redis.decrement_counter(instance_key)

            elapsed = (time.perf_counter() - start_time) * 1000
            latency = f"{elapsed:.2f}ms"

            status_code = exc.response.status_code

            if status_code >= 500:
                blocked = await circuit_breaker.record_failure(
                    upstream_instance, circuit
                )

                if blocked is not None:
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
                    return blocked

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
    ) -> Response | JSONResponse:
        retries = 0
        start_time = 0

        merged_doc = {}
        res_headers = {}

        circuit_breaker: CircuitBreaker = request.state.circuit_breaker

        try:
            for i in range(len(instances)):
                span_id = str(uuid4())
                request_meta["span_id"] = span_id

                upstream_instance = instances[i]
                upstream = request.state.upstream[i]

                circuit: dict = request.state.circuits[upstream_instance]
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
                await circuit_breaker.record_success(upstream_instance, circuit)

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
                blocked = await circuit_breaker.record_failure(
                    upstream_instance, circuit
                )

                if blocked is not None:
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
                    return blocked

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
