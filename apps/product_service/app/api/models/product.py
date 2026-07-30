import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    text,
    UUID,
    Index,
    String,
    Numeric,
    Integer,
    DateTime,
    CheckConstraint,
    PrimaryKeyConstraint,
)


from shared.models.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, server_default=text("uuid_generate_v7()")
    )
    name: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[str] = mapped_column(String)
    serial: Mapped[str] = mapped_column(String)
    price: Mapped[Decimal] = mapped_column(Numeric(precision=2))
    quantity: Mapped[int] = mapped_column(
        Integer, CheckConstraint("quantity >= 0", name="products_quantity_ck")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        PrimaryKeyConstraint("id", name="products_pk"),
        Index("idx_products_price", price),
        Index("idx_products_quantity", quantity),
        Index("idx_products_created_at", created_at),
    )
