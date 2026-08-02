from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ProductReserveBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    order_id: UUID
    product_id: UUID
    reserve: int


class ProductReserveBaseInDB(ProductReserveBase):
    created_at: datetime
