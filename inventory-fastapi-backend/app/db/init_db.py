"""Startup bootstrap: create tables (optional) and seed the first admin user."""
import logging

from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base  # noqa: F401 - ensures all models are registered
from app.db.session import SessionLocal, engine
from app.models.user import User

logger = logging.getLogger(__name__)


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created")


def seed_admin() -> None:
    with SessionLocal() as db:
        user_count = db.execute(select(func.count()).select_from(User)).scalar_one()
        if user_count:
            logger.info("Users already present (%s) - skipping admin seed", user_count)
            return
        admin = User(
            email=settings.FIRST_ADMIN_EMAIL.lower(),
            full_name=settings.FIRST_ADMIN_NAME,
            hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
            is_active=True,
            is_admin=True,
        )
        db.add(admin)
        db.commit()
        logger.warning(
            "Seeded first admin user %s - change this password immediately",
            settings.FIRST_ADMIN_EMAIL,
        )


def init_db() -> None:
    if settings.AUTO_CREATE_TABLES:
        create_tables()
    if settings.SEED_ADMIN:
        seed_admin()
