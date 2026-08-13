from decimal import Decimal

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.category import Category
from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.dashboard import CategoryBreakdown, DashboardCounts, DashboardSummary
from app.schemas.inventory import StockMovementRead
from app.schemas.product import ProductRead

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    db: DbSession,
    _: CurrentUser,
    low_stock_limit: int = Query(5, ge=1, le=50),
    movement_limit: int = Query(10, ge=1, le=50),
):
    counts = DashboardCounts(
        products=db.execute(select(func.count()).select_from(Product)).scalar_one(),
        categories=db.execute(select(func.count()).select_from(Category)).scalar_one(),
        suppliers=db.execute(select(func.count()).select_from(Supplier)).scalar_one(),
        users=db.execute(select(func.count()).select_from(User)).scalar_one(),
        low_stock=db.execute(
            select(func.count())
            .select_from(Product)
            .where(Product.quantity <= Product.reorder_level)
        ).scalar_one(),
        out_of_stock=db.execute(
            select(func.count()).select_from(Product).where(Product.quantity <= 0)
        ).scalar_one(),
        total_units=db.execute(select(func.coalesce(func.sum(Product.quantity), 0))).scalar_one(),
        inventory_value=db.execute(
            select(func.coalesce(func.sum(Product.unit_price * Product.quantity), 0))
        ).scalar_one()
        or Decimal(0),
    )

    low_stock_products = (
        db.execute(
            select(Product)
            .options(selectinload(Product.category), selectinload(Product.supplier))
            .where(Product.quantity <= Product.reorder_level)
            .order_by(Product.quantity.asc())
            .limit(low_stock_limit)
        )
        .scalars()
        .all()
    )

    movements = (
        db.execute(
            select(StockMovement)
            .options(selectinload(StockMovement.product))
            .order_by(StockMovement.id.desc())
            .limit(movement_limit)
        )
        .scalars()
        .all()
    )

    recent = []
    for m in movements:
        item = StockMovementRead.model_validate(m)
        if m.product is not None:
            item.product_name = m.product.name
            item.product_sku = m.product.sku
        recent.append(item)

    breakdown_rows = db.execute(
        select(
            Product.category_id,
            func.coalesce(Category.name, "Uncategorised"),
            func.count(Product.id),
            func.coalesce(func.sum(Product.quantity), 0),
        )
        .select_from(Product)
        .outerjoin(Category, Product.category_id == Category.id)
        .group_by(Product.category_id, Category.name)
        .order_by(func.count(Product.id).desc())
    ).all()

    breakdown = [
        CategoryBreakdown(
            category_id=row[0], category_name=row[1], product_count=row[2], total_quantity=row[3]
        )
        for row in breakdown_rows
    ]

    return DashboardSummary(
        counts=counts,
        low_stock_products=[ProductRead.model_validate(p) for p in low_stock_products],
        recent_movements=recent,
        category_breakdown=breakdown,
    )
