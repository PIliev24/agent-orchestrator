"""Health check endpoint."""

from fastapi import APIRouter

from agent_orchestrator.core.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check API health status.

    Returns:
        HealthResponse with status and version.
    """
    return HealthResponse()
