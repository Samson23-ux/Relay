from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class CartBase(BaseModel):
    id: UUID
    user_id: UUID
    items: int
    created_at: datetime


class CartInDB(CartBase):
    pass


class CartResponse(CartBase):
    pass
