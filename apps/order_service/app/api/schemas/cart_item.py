from uuid import UUID
from decimal import Decimal
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


from apps.product_service.app.api.schemas.product import ProductItem


class CartItemBase(BaseModel):
    quantity: int
    price: Decimal = Field(..., decimal_places=2)
    total_price: Decimal = Field(..., decimal_places=2)


class CartItemInDB(CartItemBase):
    product_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CartItemResponse(CartItemBase):
    model_config = ConfigDict(from_attributes=True)

    cart_id: UUID
    product: ProductItem
    created_at: datetime
