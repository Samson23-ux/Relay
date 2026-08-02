import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    text,
    UUID,
    Index,
    Integer,
    DateTime,
    ForeignKey,
    CheckConstraint,
    PrimaryKeyConstraint,
)


from shared.models.base import Base


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, server_default=text("uuid_generate_v7()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", name="cart_user_id_fk", ondelete="CASCADE")
    )
    items: Mapped[int] = mapped_column(
        Integer, CheckConstraint("items > 0", name="carts_items_ck")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        PrimaryKeyConstraint("id", name="carts_pk"),
        Index("idx_cart_user_id_comp", id, user_id),
    )
