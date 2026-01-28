"""API routes."""

from fastapi import APIRouter

from agent_orchestrator.api.routes.health import router as health_router
from agent_orchestrator.api.routes.agents import router as agents_router
from agent_orchestrator.api.routes.tools import router as tools_router
from agent_orchestrator.api.routes.workflows import router as workflows_router
from agent_orchestrator.api.routes.executions import router as executions_router

# Main API router
api_router = APIRouter()

# Include route modules
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(agents_router, prefix="/agents", tags=["Agents"])
api_router.include_router(tools_router, prefix="/tools", tags=["Tools"])
api_router.include_router(workflows_router, prefix="/workflows", tags=["Workflows"])
api_router.include_router(executions_router, prefix="/executions", tags=["Executions"])

__all__ = ["api_router"]
