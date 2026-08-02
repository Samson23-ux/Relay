from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CartBase(BaseModel):
    id: UUID
    user_id: UUID
    items: int = 1


class CartInDB(CartBase):
    pass


class AddToCart(BaseModel):
    product_id: UUID
    quantity: int = Field(..., ge=1)


class CartResponse(CartBase):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
