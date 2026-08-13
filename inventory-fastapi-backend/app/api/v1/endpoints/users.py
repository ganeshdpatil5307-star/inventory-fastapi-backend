from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select

from app.api.deps import CurrentAdmin, DbSession, Pagination
from app.models.user import User
from app.schemas.common import Message, Page
from app.schemas.user import UserRead
from app.services.pagination import paginate

router = APIRouter()


@router.get("", response_model=Page[UserRead])
def list_users(
    db: DbSession,
    _: CurrentAdmin,
    pagination: Pagination,
    q: str | None = Query(None, description="Search by email or name"),
):
    stmt = select(User)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.email.ilike(like), User.full_name.ilike(like)))
    stmt = stmt.order_by(User.id.asc())
    items, meta = paginate(db, stmt, pagination)
    return Page[UserRead](items=items, meta=meta)


@router.patch("/{user_id}/status", response_model=UserRead)
def set_user_status(user_id: int, is_active: bool, db: DbSession, admin: CurrentAdmin):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot change your own status"
        )
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", response_model=Message)
def delete_user(user_id: int, db: DbSession, admin: CurrentAdmin):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account"
        )
    db.delete(user)
    db.commit()
    return Message(detail="User deleted")
