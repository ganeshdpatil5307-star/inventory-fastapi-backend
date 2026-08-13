"""Generic offset pagination for SQLAlchemy 2.x select() statements."""
from math import ceil
from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.schemas.common import PaginationMeta, PaginationParams


def paginate(db: Session, stmt, params: PaginationParams) -> tuple[Sequence[Any], PaginationMeta]:
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = db.execute(count_stmt).scalar_one()
    offset = (params.page - 1) * params.size
    items = db.execute(stmt.offset(offset).limit(params.size)).scalars().unique().all()
    pages = ceil(total / params.size) if total else 0
    meta = PaginationMeta(
        page=params.page,
        size=params.size,
        total=total,
        pages=pages,
        has_next=params.page < pages,
        has_prev=params.page > 1,
    )
    return items, meta
