from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


from apps.product_service.app.api.schemas.product import ProductItem


class OrderItemBase(BaseModel):
    quantity: int
    price: Decimal = Field(..., decimal_places=2)
    total_price: Decimal = Field(..., decimal_places=2)
    created_at: datetime


class OrderItemInDB(OrderItemBase):
    order_id: UUID
    product_id: UUID


class OrderItemResponse(OrderItemBase):
    model_config = ConfigDict(from_attributes=True)

    product: ProductItem
