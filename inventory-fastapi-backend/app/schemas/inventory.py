from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.stock_movement import MovementType


class StockMovementCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0, description="Always a positive number")
    reference: str | None = Field(None, max_length=120)
    note: str | None = Field(None, max_length=2000)


class StockAdjust(BaseModel):
    product_id: int = Field(..., gt=0)
    new_quantity: int = Field(..., ge=0)
    note: str | None = Field(None, max_length=2000)


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    movement_type: MovementType
    quantity: int
    quantity_after: int
    reference: str | None
    note: str | None
    created_by_id: int | None
    created_at: datetime
    product_name: str | None = None
    product_sku: str | None = None
