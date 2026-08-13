from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.api.deps import CurrentUser, DbSession, Pagination
from app.models.product import Product
from app.models.supplier import Supplier
from app.schemas.common import Message, Page
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierUpdate
from app.services.pagination import paginate

router = APIRouter()


def _get_or_404(db, supplier_id: int) -> Supplier:
    obj = db.get(Supplier, supplier_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return obj


@router.get("", response_model=Page[SupplierRead])
def list_suppliers(
    db: DbSession,
    _: CurrentUser,
    pagination: Pagination,
    q: str | None = Query(None, description="Search by name, contact, email or phone"),
    sort: str = Query("name", pattern="^(name|created_at|id)$"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
):
    stmt = select(Supplier)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Supplier.name.ilike(like),
                Supplier.contact_name.ilike(like),
                Supplier.email.ilike(like),
                Supplier.phone.ilike(like),
            )
        )
    column = getattr(Supplier, sort)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc())
    items, meta = paginate(db, stmt, pagination)
    return Page[SupplierRead](items=items, meta=meta)


@router.get("/all", response_model=list[SupplierRead], summary="Unpaginated list for dropdowns")
def list_all_suppliers(db: DbSession, _: CurrentUser):
    return db.execute(select(Supplier).order_by(Supplier.name)).scalars().all()


@router.get("/{supplier_id}", response_model=SupplierRead)
def get_supplier(supplier_id: int, db: DbSession, _: CurrentUser):
    return _get_or_404(db, supplier_id)


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(payload: SupplierCreate, db: DbSession, _: CurrentUser):
    dup = db.execute(
        select(Supplier).where(func.lower(Supplier.name) == payload.name.lower())
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A supplier with this name already exists"
        )
    obj = Supplier(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{supplier_id}", response_model=SupplierRead)
def update_supplier(supplier_id: int, payload: SupplierUpdate, db: DbSession, _: CurrentUser):
    obj = _get_or_404(db, supplier_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("name"):
        dup = db.execute(
            select(Supplier).where(
                func.lower(Supplier.name) == data["name"].lower(), Supplier.id != supplier_id
            )
        ).scalar_one_or_none()
        if dup:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A supplier with this name already exists",
            )
    for field, value in data.items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{supplier_id}", response_model=Message)
def delete_supplier(supplier_id: int, db: DbSession, _: CurrentUser):
    obj = _get_or_404(db, supplier_id)
    in_use = db.execute(
        select(func.count()).select_from(Product).where(Product.supplier_id == supplier_id)
    ).scalar_one()
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete: {in_use} product(s) are linked to this supplier",
        )
    db.delete(obj)
    db.commit()
    return Message(detail="Supplier deleted")
