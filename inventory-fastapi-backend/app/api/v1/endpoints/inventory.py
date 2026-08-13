from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, Pagination
from app.models.product import Product
from app.models.stock_movement import MovementType, StockMovement
from app.schemas.common import Page
from app.schemas.inventory import StockAdjust, StockMovementCreate, StockMovementRead
from app.services.pagination import paginate

router = APIRouter()


def _serialize(movement: StockMovement) -> StockMovementRead:
    data = StockMovementRead.model_validate(movement)
    if movement.product is not None:
        data.product_name = movement.product.name
        data.product_sku = movement.product.sku
    return data


def _locked_product(db, product_id: int) -> Product:
    product = db.get(Product, product_id, with_for_update=True)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.get("/movements", response_model=Page[StockMovementRead])
def list_movements(
    db: DbSession,
    _: CurrentUser,
    pagination: Pagination,
    q: str | None = Query(None, description="Search by reference, note, product name or SKU"),
    product_id: int | None = Query(None),
    movement_type: MovementType | None = Query(None),
    order: str = Query("desc", pattern="^(asc|desc)$"),
):
    stmt = select(StockMovement).options(selectinload(StockMovement.product)).join(Product)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                StockMovement.reference.ilike(like),
                StockMovement.note.ilike(like),
                Product.name.ilike(like),
                Product.sku.ilike(like),
            )
        )
    if product_id is not None:
        stmt = stmt.where(StockMovement.product_id == product_id)
    if movement_type is not None:
        stmt = stmt.where(StockMovement.movement_type == movement_type)
    stmt = stmt.order_by(
        StockMovement.id.asc() if order == "asc" else StockMovement.id.desc()
    )
    items, meta = paginate(db, stmt, pagination)
    return Page[StockMovementRead](items=[_serialize(m) for m in items], meta=meta)


@router.post("/stock-in", response_model=StockMovementRead, status_code=status.HTTP_201_CREATED)
def stock_in(payload: StockMovementCreate, db: DbSession, current_user: CurrentUser):
    """Receive stock into inventory."""
    product = _locked_product(db, payload.product_id)
    product.quantity += payload.quantity
    movement = StockMovement(
        product_id=product.id,
        movement_type=MovementType.IN,
        quantity=payload.quantity,
        quantity_after=product.quantity,
        reference=payload.reference,
        note=payload.note,
        created_by_id=current_user.id,
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return _serialize(movement)


@router.post("/stock-out", response_model=StockMovementRead, status_code=status.HTTP_201_CREATED)
def stock_out(payload: StockMovementCreate, db: DbSession, current_user: CurrentUser):
    """Issue stock out of inventory. Rejects quantities above stock on hand."""
    product = _locked_product(db, payload.product_id)
    if payload.quantity > product.quantity:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Insufficient stock: {product.quantity} unit(s) available",
        )
    product.quantity -= payload.quantity
    movement = StockMovement(
        product_id=product.id,
        movement_type=MovementType.OUT,
        quantity=payload.quantity,
        quantity_after=product.quantity,
        reference=payload.reference,
        note=payload.note,
        created_by_id=current_user.id,
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return _serialize(movement)


@router.post("/adjust", response_model=StockMovementRead, status_code=status.HTTP_201_CREATED)
def adjust_stock(payload: StockAdjust, db: DbSession, current_user: CurrentUser):
    """Set stock to an absolute counted quantity (stock take correction)."""
    product = _locked_product(db, payload.product_id)
    delta = payload.new_quantity - product.quantity
    if delta == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New quantity is the same as the current quantity",
        )
    product.quantity = payload.new_quantity
    movement = StockMovement(
        product_id=product.id,
        movement_type=MovementType.ADJUST,
        quantity=abs(delta),
        quantity_after=product.quantity,
        reference="ADJUSTMENT",
        note=payload.note,
        created_by_id=current_user.id,
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return _serialize(movement)
