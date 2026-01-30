"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_orchestrator.api.exception_handlers import register_exception_handlers
from agent_orchestrator.api.routes import api_router
from agent_orchestrator.config import settings
from agent_orchestrator.tools.registry import register_builtin_tools
from agent_orchestrator.workflows.checkpointer import close_checkpointer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    register_builtin_tools()

    yield

    # Shutdown
    await close_checkpointer()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance.
    """
    app = FastAPI(
        title="Agent Orchestrator API",
        description="LangGraph-based AI Agent Orchestrator with multi-provider support",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register exception handlers
    register_exception_handlers(app)

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")

    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "agent_orchestrator.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
