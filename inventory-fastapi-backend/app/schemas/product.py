from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.category import CategoryRead
from app.schemas.supplier import SupplierRead


class ProductBase(BaseModel):
    sku: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=4000)
    unit_price: Decimal = Field(0, ge=0, max_digits=12, decimal_places=2)
    reorder_level: int = Field(0, ge=0)
    category_id: int | None = None
    supplier_id: int | None = None


class ProductCreate(ProductBase):
    quantity: int = Field(0, ge=0, description="Opening stock quantity")


class ProductUpdate(BaseModel):
    sku: str | None = Field(None, min_length=1, max_length=64)
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=4000)
    unit_price: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    reorder_level: int | None = Field(None, ge=0)
    category_id: int | None = None
    supplier_id: int | None = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quantity: int
    is_low_stock: bool
    created_at: datetime
    updated_at: datetime
    category: CategoryRead | None = None
    supplier: SupplierRead | None = None
