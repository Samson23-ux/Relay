from uuid import UUID
from typing import Optional
from pydantic import BaseModel


from shared.models.log import UpstreamType, LogLevel


class LogBase(BaseModel):
    pass


class LogCreate(LogBase):
    trace_id: UUID
    span_id: UUID
    parent_span_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    client_ip: Optional[str] = None
    upstream: UpstreamType
    upstream_instance: Optional[str] = None
    upstream_url: Optional[str] = None
    message: str
    log_level: LogLevel = LogLevel.INFO
    method: Optional[str] = None
    path: Optional[str] = None
    circuit_open: Optional[bool] = None
    rate_limited: Optional[bool] = None
    retries: Optional[int] = None
    latency_ms: Optional[int] = None
    status_code: Optional[int] = None
    rate_limited: Optional[bool] = None


class LogUpdate(LogBase):
    retries: Optional[int] = None
    latency_ms: Optional[int] = None
    status_code: Optional[int] = None
    rate_limited: Optional[bool] = None
