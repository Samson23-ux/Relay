from typing import Optional
from pydantic import BaseModel


class ServiceInstance(BaseModel):
    url: str


class Service(BaseModel):
    user_service: list[ServiceInstance]
    order_service: list[ServiceInstance]
    product_service: list[ServiceInstance]


class Upstream(BaseModel):
    services: list[Service]


class RateLimit(BaseModel):
    requests: int
    window: str
    key_by: str


class RouteException(BaseModel):
    paths: list[str]
    auth_required: Optional[bool] = None
    check_role: Optional[bool] = None
    rate_limit: Optional[RateLimit] = None


class Route(BaseModel):
    path: str
    methods: list[str]
    strip_prefix: str
    auth_required: bool
    check_role: bool
    rate_limit: RateLimit
    exceptions: RouteException


class Config(BaseModel):
    upstreams: list[Upstream]
    routes: list[Route]
