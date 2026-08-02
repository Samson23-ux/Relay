import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    UUID,
    Numeric,
    Integer,
    DateTime,
    ForeignKey,
    CheckConstraint,
    PrimaryKeyConstraint,
)


from shared.models.base import Base


class OrderItem(Base):
    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("orders.id", name="order_items_order_id_fk", ondelete="CASCADE"),
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("products.id", name="order_items_product_id_fk", ondelete="CASCADE"),
    )
    quantity: Mapped[int] = mapped_column(
        Integer, CheckConstraint("quantity > 0", name="products_quantity_ck")
    )
    price: Mapped[Decimal] = mapped_column(Numeric(precision=4))
    total_price: Mapped[Decimal] = mapped_column(Numeric(precision=4))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        PrimaryKeyConstraint("order_id", "product_id", name="order_items_pk"),
    )
