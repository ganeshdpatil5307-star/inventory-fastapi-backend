from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, Pagination
from app.models.category import Category
from app.models.product import Product
from app.models.stock_movement import MovementType, StockMovement
from app.models.supplier import Supplier
from app.schemas.common import Message, Page
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.pagination import paginate

router = APIRouter()


def _get_or_404(db, product_id: int) -> Product:
    obj = db.get(Product, product_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return obj


def _validate_relations(db, category_id: int | None, supplier_id: int | None) -> None:
    if category_id is not None and db.get(Category, category_id) is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid category_id")
    if supplier_id is not None and db.get(Supplier, supplier_id) is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid supplier_id")


@router.get("", response_model=Page[ProductRead])
def list_products(
    db: DbSession,
    _: CurrentUser,
    pagination: Pagination,
    q: str | None = Query(None, description="Search by SKU, name or description"),
    category_id: int | None = Query(None),
    supplier_id: int | None = Query(None),
    low_stock: bool | None = Query(None, description="Only items at or below reorder level"),
    min_price: Decimal | None = Query(None, ge=0),
    max_price: Decimal | None = Query(None, ge=0),
    sort: str = Query("name", pattern="^(name|sku|unit_price|quantity|created_at|id)$"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
):
    stmt = select(Product).options(
        selectinload(Product.category), selectinload(Product.supplier)
    )
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(Product.sku.ilike(like), Product.name.ilike(like), Product.description.ilike(like))
        )
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    if supplier_id is not None:
        stmt = stmt.where(Product.supplier_id == supplier_id)
    if low_stock:
        stmt = stmt.where(Product.quantity <= Product.reorder_level)
    if min_price is not None:
        stmt = stmt.where(Product.unit_price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Product.unit_price <= max_price)

    column = getattr(Product, sort)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc())
    items, meta = paginate(db, stmt, pagination)
    return Page[ProductRead](items=items, meta=meta)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: DbSession, _: CurrentUser):
    return _get_or_404(db, product_id)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: DbSession, current_user: CurrentUser):
    dup = db.execute(
        select(Product).where(func.lower(Product.sku) == payload.sku.lower())
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A product with this SKU already exists"
        )
    _validate_relations(db, payload.category_id, payload.supplier_id)

    obj = Product(**payload.model_dump())
    db.add(obj)
    db.flush()

    if obj.quantity:
        db.add(
            StockMovement(
                product_id=obj.id,
                movement_type=MovementType.IN,
                quantity=obj.quantity,
                quantity_after=obj.quantity,
                reference="OPENING",
                note="Opening stock recorded at product creation",
                created_by_id=current_user.id,
            )
        )
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{product_id}", response_model=ProductRead)
def update_product(product_id: int, payload: ProductUpdate, db: DbSession, _: CurrentUser):
    obj = _get_or_404(db, product_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("sku"):
        dup = db.execute(
            select(Product).where(
                func.lower(Product.sku) == data["sku"].lower(), Product.id != product_id
            )
        ).scalar_one_or_none()
        if dup:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="A product with this SKU already exists"
            )
    _validate_relations(db, data.get("category_id"), data.get("supplier_id"))
    for field, value in data.items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{product_id}", response_model=Message)
def delete_product(product_id: int, db: DbSession, _: CurrentUser):
    obj = _get_or_404(db, product_id)
    db.delete(obj)
    db.commit()
    return Message(detail="Product deleted")
