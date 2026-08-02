from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


from apps.order_service.app.api.models.order import OrderStatus


class OrderBase(BaseModel):
    id: UUID
    user_id: UUID
    reference_id: UUID


class OrderInDB(OrderBase):
    status: OrderStatus = OrderStatus.PENDING
    total_price: Decimal = Field(..., decimal_places=2)


class OrderResponse(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    status: OrderStatus
    total_price: Decimal
    created_at: datetime
