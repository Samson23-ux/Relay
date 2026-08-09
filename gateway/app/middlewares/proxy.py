import time
from enum import Enum
from json import JSONDecodeError
from fastapi import HTTPException, Request
from httpx import HTTPStatusError, Response
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
    def __init__(self):
        self._redis = None

    async def make_request(
        self, url: str, headers: dict, request: Request, http_request: CustomRequest
    ) -> tuple[Response, int]:
        form: dict = request.form()
        cookies: dict = request.cookies
        params: dict = request.query_params

        data: dict | None = dict(form) if form else None

        try:
            json: dict = request.json()
        except JSONDecodeError:
            json = None

        if request.method == "GET":
            res: Response = await http_request.get(url, params, headers, cookies)
            retries = http_request.get.retry.statistics["attempt_number"] - 1
        elif request.method == "POST":
            res: Response = await http_request.post(
                url, params, data, json, headers, cookies
            )
            retries = http_request.post.retry.statistics["attempt_number"] - 1
        elif request.method == "PATCH":
            res: Response = await http_request.patch(
                url, params, data, json, headers, cookies
            )
            retries = http_request.patch.retry.statistics["attempt_number"] - 1
        elif request.method == "DELETE":
            res: Response = await http_request.delete(url, params, headers, cookies)
            retries = http_request.delete.retry.statistics["attempt_number"] - 1

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
                "retry_at": None,
                "half_open_requests": 0,
            }
            await self._redis.create_hset(breaker_key, circuit)

        request_meta: dict = {
            "trace_id": request.state.trace_id,
            "span_id": request.state.user_email,
            "parent_span_id": request.state.span_id,
            "client_ip": request.client.host,
            "upstream": request.state.upstream,
            "method": request.method,
            "path": request.url.path,
            "latency_ms": int(total),
        }

        try:
            if circuit["state"] == CircuitState.OPEN:
                raise HTTPException(status_code=503, detail="Service Unavailable")
            elif (
                circuit["state"] == CircuitState.HALFOPEN
                and circuit["half_open_requests"]
                >= config.circuit_breaker.half_open_requests
            ):
                raise HTTPException(status_code=503, detail="Service Unavailable")

            url: str = f"{request.state.upstream_instance}/{request.url.path}"

            headers: dict = {
                "x-trace-id": request.state.trace_id,
                "x-span-id": request.state.span_id,
                "x-user-email": request.state.user_email,
                "x-user-type": request.state.user_type,
                "x-upstream": request.state.upstream,
                "x-upstream-instance": request.state.upstream_instance,
            }

            start_time = time.perf_counter()
            res, retries = await self.make_request(url, headers, request, http_request)

            elapsed = (time.perf_counter() - start_time) * 1000
            total_str = str(int(elapsed))[:2]
            total = int(total_str)

            message = "Response received"
            request_meta["retries"] = retries
            request_meta["status_code"] = res.status_code

            log_info(message, request_meta)
            return res
        except HTTPStatusError as exc:
            status_code = exc.response.status_code

            if status_code >= 500:
                circuit["failures"] += 1

                if circuit["failures"] >= config.circuit_breaker.failure_threshold:
                    recovery_timeout = int(
                        config.circuit_breaker.recovery_timeout.removesuffix("s")
                    )

                    circuit["half_open_requests"] = 0
                    circuit["state"] = CircuitState.OPEN
                    circuit["retry_at"] = datetime.now(timezone.utc) + timedelta(
                        seconds=recovery_timeout
                    )

                    message = "Service Unavailable"
                    request_meta["status_code"] = 503

                    log_info(message, request_meta)
                    raise HTTPException(status_code=503, detail="Service Unavailable")

                message = "Error occured while processing request"

                request_meta["status_code"] = status_code
                log_info(message, request_meta)

                raise HTTPException(
                    status_code=status_code, detail="Internal Server Error"
                )

            message = exc.response.reason_phrase
            request_meta["status_code"] = status_code

            log_info(message, request_meta)

            raise HTTPException(
                status_code=status_code, detail=exc.response.reason_phrase
            )
        except Exception as exc:
            message = str(exc)
            request_meta["status_code"] = status_code

            log_info(message, request_meta)

            raise HTTPException(status_code=500, detail="Internal Server Error")
