import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql.types import INET
from sqlalchemy import (
    text,
    Enum,
    UUID,
    String,
    Integer,
    Index,
    DateTime,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    PrimaryKeyConstraint,
)


from shared.models.base import Base


class UpstreamType(str, enum.Enum):
    RELAY = "relay"
    USER_SERVICE = "user_service"
    ORDER_SERVICE = "order_service"
    PRODUCT_SERVICE = "product_service"


class LogLevel(str, enum.Enum):
    INFO = "info"
    DEBUG = "debug"
    ERROR = "error"


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, server_default=text("uuid_generate_v7()")
    )
    trace_id: Mapped[uuid.UUID] = mapped_column(UUID)
    span_id: Mapped[uuid.UUID] = mapped_column(UUID)
    parent_span_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID, ForeignKey("users.id", name="logs_user_id_fk", ondelete="CASCADE")
    )
    client_ip: Mapped[str] = mapped_column(INET)
    upstream: Mapped[enum.Enum] = mapped_column(
        Enum(UpstreamType, values_callable=lambda e: [m.value for m in e])
    )
    upstream_url: Mapped[str | None] = mapped_column(String)
    message: Mapped[str] = mapped_column(String)
    log_level: Mapped[enum.Enum] = mapped_column(
        Enum(LogLevel, values_callable=lambda e: [m.value for m in e]),
        default=LogLevel.INFO
    )
    method: Mapped[str] = mapped_column(String)
    path: Mapped[str] = mapped_column(String)
    status_code: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    circuit_open: Mapped[bool] = mapped_column(Boolean)
    rate_limited: Mapped[bool] = mapped_column(Boolean, default=False)
    retries: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        PrimaryKeyConstraint("id", name="logs_pk"),
        Index("idx_logs_trace_span", trace_id, span_id),
        Index("idx_logs_trace_upstream", trace_id, upstream),
        UniqueConstraint(
            "trace_id", "span_id", "parent_span_id", name="logs_unique_key"
        ),
    )
