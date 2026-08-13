from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.api.deps import CurrentUser, DbSession, Pagination
from app.models.category import Category
from app.models.product import Product
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.common import Message, Page
from app.services.pagination import paginate

router = APIRouter()


def _get_or_404(db, category_id: int) -> Category:
    obj = db.get(Category, category_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return obj


@router.get("", response_model=Page[CategoryRead])
def list_categories(
    db: DbSession,
    _: CurrentUser,
    pagination: Pagination,
    q: str | None = Query(None, description="Search by name or description"),
    sort: str = Query("name", pattern="^(name|created_at|id)$"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
):
    stmt = select(Category)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Category.name.ilike(like), Category.description.ilike(like)))
    column = getattr(Category, sort)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc())
    items, meta = paginate(db, stmt, pagination)
    return Page[CategoryRead](items=items, meta=meta)


@router.get("/all", response_model=list[CategoryRead], summary="Unpaginated list for dropdowns")
def list_all_categories(db: DbSession, _: CurrentUser):
    return db.execute(select(Category).order_by(Category.name)).scalars().all()


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: int, db: DbSession, _: CurrentUser):
    return _get_or_404(db, category_id)


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: DbSession, _: CurrentUser):
    dup = db.execute(
        select(Category).where(func.lower(Category.name) == payload.name.lower())
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A category with this name already exists"
        )
    obj = Category(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{category_id}", response_model=CategoryRead)
def update_category(category_id: int, payload: CategoryUpdate, db: DbSession, _: CurrentUser):
    obj = _get_or_404(db, category_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        dup = db.execute(
            select(Category).where(
                func.lower(Category.name) == data["name"].lower(), Category.id != category_id
            )
        ).scalar_one_or_none()
        if dup:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="A category with this name already exists"
            )
    for field, value in data.items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{category_id}", response_model=Message)
def delete_category(category_id: int, db: DbSession, _: CurrentUser):
    obj = _get_or_404(db, category_id)
    in_use = db.execute(
        select(func.count()).select_from(Product).where(Product.category_id == category_id)
    ).scalar_one()
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete: {in_use} product(s) still use this category",
        )
    db.delete(obj)
    db.commit()
    return Message(detail="Category deleted")
