from uuid import UUID
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field


from apps.order_service.app.api.schemas.cart_item import CartItemInDB


class CartBase(BaseModel):
    id: UUID
    user_id: UUID
    items: int = 1


class CartInDB(CartBase):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cart_items: list[CartItemInDB] = []


class AddToCart(BaseModel):
    product_id: UUID
    quantity: int = Field(..., ge=1)


class CartResponse(CartBase):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
