import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    UUID,
    Integer,
    DateTime,
    ForeignKey,
    CheckConstraint,
    PrimaryKeyConstraint,
)


from shared.models.base import Base


class ProductReserve(Base):
    __tablename__ = "product_reserves"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("orders.id", name="product_reserves_order_id_fk", ondelete="CASCADE"),
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("products.id", name="product_reserves_product_id_fk", ondelete="CASCADE"),
    )
    reserve: Mapped[int | None] = mapped_column(
        Integer, CheckConstraint("reserve > 0", name="product_reserves_ck"), default=0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        PrimaryKeyConstraint("order_id", "product_id", name="product_reserves_pk"),
    )
