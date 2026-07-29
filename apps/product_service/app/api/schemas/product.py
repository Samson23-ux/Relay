from uuid import UUID
from decimal import Decimal
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True)

    name: str
    description: str = Field(..., min_length=15)
    serial: str = Field(..., min_length=8)
    price: Decimal = Field(..., decimal_places=2)
    quantity: int = Field(..., ge=1)


class ProductInDB(ProductBase):
    id: UUID
    created_at: datetime
    updated_at: datetime | None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = Field(None, min_length=15)
    serial: Optional[str] = Field(None, min_length=8)
    price: Optional[Decimal] = Field(None, decimal_places=2)
    quantity: Optional[int] = Field(None, ge=1)


class ProductItem(BaseModel):
    id: UUID
    name: str
    description: str
    serial: str


class ProductResponse(ProductInDB):
    pass
