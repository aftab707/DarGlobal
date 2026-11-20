from fastapi import APIRouter, Response, status

from app.schemas.health import HealthResponse
from app.services.health import get_health

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(response: Response) -> HealthResponse:
    result = get_health()
    if not result.index_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
