from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str
    description: str = Field(..., min_length=15)
    serial: str = Field(..., min_length=8)
    price: Decimal = Field(..., decimal_places=2)
    quantity: int = Field(..., ge=1)


class ProductCreate(ProductBase):
    pass


class ProductResponse(BaseModel):
    id: UUID
    name: str
    description: str
    serial: str
    price: Decimal
    quantity: int
    created_at: datetime
    updated_at: datetime | None
