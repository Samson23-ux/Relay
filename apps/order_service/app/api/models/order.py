import uuid
import enum
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    text,
    UUID,
    Enum,
    Index,
    Numeric,
    DateTime,
    ForeignKey,
    PrimaryKeyConstraint,
)


from shared.models.base import Base


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, server_default=text("uuid_generate_v7()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", name="orders_user_id_fk", ondelete="CASCADE")
    )
    reference_id: Mapped[uuid.UUID] = mapped_column(UUID, unique=True)
    status: Mapped[enum.Enum] = mapped_column(
        Enum(OrderStatus, values_callable=lambda e: [m.value for m in e])
    )
    total_price: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        PrimaryKeyConstraint("id", name="orders_pk"),
        Index("idx_orders_created_at", created_at),
        Index("idx_orders_user_id_comp", id, user_id)
    )
