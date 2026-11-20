import logging
import sqlite3

from chromadb.errors import ChromaError

from app.schemas.health import HealthResponse
from app.services.index_store import active_build, index_root, verify_build

logger = logging.getLogger(__name__)


def get_health() -> HealthResponse:
    root = index_root()
    if not (root / "current.json").is_file():
        return HealthResponse(status="not_ready", index_ready=False)
    try:
        path, manifest = active_build(root)
        verify_build(path, manifest)
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error, ChromaError) as exc:
        logger.warning("Index readiness check failed: %s", exc)
        return HealthResponse(status="not_ready", index_ready=False)
    return HealthResponse(status="ok", index_ready=True)
