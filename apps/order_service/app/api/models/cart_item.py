import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    UUID,
    Index,
    Numeric,
    Integer,
    DateTime,
    ForeignKey,
    CheckConstraint,
    PrimaryKeyConstraint,
)


from shared.models.base import Base


class CartItem(Base):
    __tablename__ = "cart_items"

    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("carts.id", name="cart_items_cart_id_fk", ondelete="CASCADE"),
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("products.id", name="cart_items_product_id_fk", ondelete="CASCADE"),
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
        PrimaryKeyConstraint("cart_id", "product_id", name="cart_items_pk"),
        Index("idx_cart_items_created_at", created_at),
    )
