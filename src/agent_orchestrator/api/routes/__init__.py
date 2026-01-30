"""API routes."""

from fastapi import APIRouter

from agent_orchestrator.api.routes.agent_tools import router as agent_tools_router
from agent_orchestrator.api.routes.agents import router as agents_router
from agent_orchestrator.api.routes.execution_steps import router as execution_steps_router
from agent_orchestrator.api.routes.executions import router as executions_router
from agent_orchestrator.api.routes.health import router as health_router
from agent_orchestrator.api.routes.tools import router as tools_router
from agent_orchestrator.api.routes.workflow_edges import router as workflow_edges_router
from agent_orchestrator.api.routes.workflow_nodes import router as workflow_nodes_router
from agent_orchestrator.api.routes.workflows import router as workflows_router

# Main API router
api_router = APIRouter()

# Include route modules
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(agents_router, prefix="/agents", tags=["Agents"])
api_router.include_router(
    agent_tools_router,
    prefix="/agents/{agent_id}/tools",
    tags=["Agent Tools"],
)
api_router.include_router(tools_router, prefix="/tools", tags=["Tools"])
api_router.include_router(workflows_router, prefix="/workflows", tags=["Workflows"])
api_router.include_router(
    workflow_nodes_router,
    prefix="/workflows/{workflow_id}/nodes",
    tags=["Workflow Nodes"],
)
api_router.include_router(
    workflow_edges_router,
    prefix="/workflows/{workflow_id}/edges",
    tags=["Workflow Edges"],
)
api_router.include_router(executions_router, prefix="/executions", tags=["Executions"])
api_router.include_router(
    execution_steps_router,
    prefix="/executions/{execution_id}/steps",
    tags=["Execution Steps"],
)

__all__ = ["api_router"]
