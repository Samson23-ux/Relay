from enum import Enum
from typing import Optional
from pydantic import BaseModel


from shared.models.log import UpstreamType


class MethodEnum(str, Enum):
    GET = "get"
    POST = "post"
    PATCH = "patch"
    DELETE = "delete"


class Upstream(BaseModel):
    name: UpstreamType
    instances: list[str]


class RateLimit(BaseModel):
    requests: int
    window: str
    key_by: str


class RouteException(BaseModel):
    path: str
    method: MethodEnum
    auth_required: Optional[bool] = None
    limit_requests: Optional[bool] = None
    roles: Optional[list[str]] = None
    revoke_token: Optional[bool] = None
    rate_limit: Optional[RateLimit] = None


class Route(BaseModel):
    path: str
    methods: list[MethodEnum]
    strip_prefix: Optional[str] = None
    auth_required: bool
    limit_requests: bool
    revoke_token: bool
    roles: list[str]
    rate_limit: Optional[RateLimit] = None
    exceptions: Optional[list[RouteException]] = []


class CircuitBreaker(BaseModel):
    failure_threshold: int
    recovery_timeout: str
    half_open_requests: int


class Config(BaseModel):
    upstreams: list[Upstream]
    routes: list[Route]
    circuit_breaker: CircuitBreaker
