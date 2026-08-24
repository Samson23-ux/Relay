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
    status: OrderStatus = OrderStatus.PROCESSING
    total_price: Decimal = Field(..., decimal_places=2)


class OrderResponse(OrderInDB):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
