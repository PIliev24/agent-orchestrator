"""Main FastAPI application for the Agent Orchestrator."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_orchestrator.api.exception_handlers import register_exception_handlers
from agent_orchestrator.api.middleware import APIKeyAuthMiddleware
from agent_orchestrator.api.routes import agents, files, health, sessions, workflows
from agent_orchestrator.config import settings
from agent_orchestrator.sessions.manager import SessionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown."""
    logger.info("Starting Agent Orchestrator...")

    session_manager = SessionManager()
    app.state.session_manager = session_manager

    logger.info("Session manager initialized")

    yield

    logger.info("Shutting down Agent Orchestrator...")
    await app.state.session_manager.cleanup_all()
    logger.info("All sessions cleaned up")


app = FastAPI(
    title="Agent Orchestrator",
    description="AI Agent orchestration with LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(APIKeyAuthMiddleware)

app.include_router(health.router, tags=["Health"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["Workflows"])
app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["Sessions"])

register_exception_handlers(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "agent_orchestrator.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
