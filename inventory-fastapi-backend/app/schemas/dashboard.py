from decimal import Decimal
from typing import List

from pydantic import BaseModel

from app.schemas.inventory import StockMovementRead
from app.schemas.product import ProductRead


class DashboardCounts(BaseModel):
    products: int
    categories: int
    suppliers: int
    users: int
    low_stock: int
    out_of_stock: int
    total_units: int
    inventory_value: Decimal


class CategoryBreakdown(BaseModel):
    category_id: int | None
    category_name: str
    product_count: int
    total_quantity: int


class DashboardSummary(BaseModel):
    counts: DashboardCounts
    low_stock_products: List[ProductRead]
    recent_movements: List[StockMovementRead]
    category_breakdown: List[CategoryBreakdown]
