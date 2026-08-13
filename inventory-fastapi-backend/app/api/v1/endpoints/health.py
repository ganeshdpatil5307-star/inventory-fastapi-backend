from datetime import datetime, timezone

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.api.deps import DbSession
from app.core.config import settings

router = APIRouter()


@router.get("", summary="Liveness + database readiness probe")
def health(db: DbSession, response: Response) -> dict:
    """Health check for App Platform.

    Returns 200 when the process is up and the database answers `SELECT 1`,
    503 otherwise so the platform can restart / hold the deployment.
    """
    db_ok, db_error = True, None
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - report any driver error
        db_ok, db_error = False, str(exc)[:300]

    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if db_ok else "degraded",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": {"connected": db_ok, "error": db_error},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/live", summary="Liveness only (no database)")
def liveness() -> dict:
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
