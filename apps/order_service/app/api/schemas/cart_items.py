from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


from apps.product_service.app.api.schemas.product import ProductItem


class CartItemBase(BaseModel):
    quantity: int
    price: Decimal = Field(..., decimal_places=2)
    total_price: Decimal = Field(..., decimal_places=2)
    created_at: datetime


class CartItemInDB(CartItemBase):
    cart_id: UUID
    product_id: UUID


class CartItemResponse(CartItemBase):
    model_config = ConfigDict(from_attributes=True)

    product: ProductItem
