from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


from gateway.app.schemas.config import Config
from shared.repo.redis import RedisRepository
from gateway.app.services.circuit_breaker import CircuitBreaker


class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    """Applies backpressure by rejecting requests to instances whose circuit
    is open or saturated before they ever reach the proxy layer, so a failing
    upstream doesn't keep burning connections and retry budget.
    """

    async def dispatch(self, request: Request, call_next):
        config: Config = request.app.state.config
        redis = RedisRepository(async_redis=request.app.state.redis)

        circuit_breaker = CircuitBreaker(redis=redis, config=config.circuit_breaker)
        request.state.circuit_breaker = circuit_breaker

        instances: str | list[str] = request.state.upstream_instance
        if isinstance(instances, str):
            instances = [instances]

        circuits: dict[str, dict] = {}
        for instance in instances:
            circuit, blocked = await circuit_breaker.check(instance)

            if blocked is not None:
                return blocked

            circuits[instance] = circuit

        request.state.circuits = circuits

        return await call_next(request)
