from app.schemas.health import HealthResponse


def get_health() -> HealthResponse:
    # Phase 3 will replace this with a check of the actual index.
    return HealthResponse(status="not_ready", index_ready=False)
