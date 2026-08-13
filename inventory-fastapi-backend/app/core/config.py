"""Application settings, loaded from environment variables."""
from functools import lru_cache
from typing import List
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # Application
    PROJECT_NAME: str = "Inventory Management API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Security
    SECRET_KEY: str = "insecure-dev-key-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str = "sqlite:///./inventory.db"
    DB_SSL_REQUIRE: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 1800

    # CORS - stored as a raw string so a plain comma-separated env var works.
    # (pydantic-settings would try to JSON-decode a List[str] env var and fail.)
    BACKEND_CORS_ORIGINS: str = ""

    # Bootstrap
    AUTO_CREATE_TABLES: bool = True
    SEED_ADMIN: bool = True
    FIRST_ADMIN_EMAIL: str = "admin@example.com"
    FIRST_ADMIN_PASSWORD: str = "ChangeMe123!"
    FIRST_ADMIN_NAME: str = "Administrator"

    @property
    def cors_origins(self) -> List[str]:
        """Allowed browser origins, parsed from the comma-separated env var."""
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]

    @property
    def sqlalchemy_database_uri(self) -> str:
        """Normalise the platform-provided DATABASE_URL for SQLAlchemy 2.x.

        Managed Postgres services hand out `postgres://...`, which SQLAlchemy no
        longer understands, and usually require TLS. We never build a URL from
        individual credentials - the platform owns the connection string.
        """
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = "postgresql+psycopg2://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg2://" + url[len("postgresql://"):]

        if self.DB_SSL_REQUIRE and url.startswith("postgresql"):
            parts = urlsplit(url)
            query = dict(parse_qsl(parts.query))
            query.setdefault("sslmode", "require")
            url = urlunsplit(
                (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
            )
        return url

    @property
    def is_sqlite(self) -> bool:
        return self.sqlalchemy_database_uri.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
