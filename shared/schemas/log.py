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
    client_ip: str
    upstream: UpstreamType
    upstream_url: str
    message: str
    log_level: LogLevel = LogLevel.INFO
    method: str
    path: str
    circuit_open: bool = False
    rate_limited: bool = False


class LogUpdate(LogBase):
    retries: Optional[int] = None
    latency_ms: Optional[int] = None
    status_code: Optional[int] = None
    rate_limited: Optional[bool] = None
