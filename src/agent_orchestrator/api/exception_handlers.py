"""Exception handlers for FastAPI."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from agent_orchestrator.core.exceptions import (
    AgentNotFoundError,
    AgentOrchestratorError,
    ExecutionError,
    ExecutionNotFoundError,
    ExecutionStepNotFoundError,
    NotFoundError,
    ProviderError,
    ToolNotFoundError,
    ValidationError,
    WorkflowCompilationError,
    WorkflowEdgeNotFoundError,
    WorkflowNodeNotFoundError,
    WorkflowNotFoundError,
)


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    """Handle not found errors."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "not_found",
            "message": exc.message,
            "details": exc.details,
        },
    )


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle validation errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "validation_error",
            "message": exc.message,
            "details": exc.details,
        },
    )


async def provider_error_handler(request: Request, exc: ProviderError) -> JSONResponse:
    """Handle AI provider errors."""
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "error": "provider_error",
            "message": exc.message,
            "details": exc.details,
        },
    )


async def workflow_compilation_error_handler(
    request: Request, exc: WorkflowCompilationError
) -> JSONResponse:
    """Handle workflow compilation errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "workflow_compilation_error",
            "message": exc.message,
            "details": exc.details,
        },
    )


async def execution_error_handler(request: Request, exc: ExecutionError) -> JSONResponse:
    """Handle execution errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "execution_error",
            "message": exc.message,
            "details": exc.details,
        },
    )


async def generic_error_handler(request: Request, exc: AgentOrchestratorError) -> JSONResponse:
    """Handle generic orchestrator errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "message": exc.message,
            "details": exc.details,
        },
    )


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app.

    Args:
        app: FastAPI application instance.
    """
    app.add_exception_handler(AgentNotFoundError, not_found_handler)
    app.add_exception_handler(ToolNotFoundError, not_found_handler)
    app.add_exception_handler(WorkflowNotFoundError, not_found_handler)
    app.add_exception_handler(ExecutionNotFoundError, not_found_handler)
    app.add_exception_handler(WorkflowNodeNotFoundError, not_found_handler)
    app.add_exception_handler(WorkflowEdgeNotFoundError, not_found_handler)
    app.add_exception_handler(ExecutionStepNotFoundError, not_found_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(ProviderError, provider_error_handler)
    app.add_exception_handler(WorkflowCompilationError, workflow_compilation_error_handler)
    app.add_exception_handler(ExecutionError, execution_error_handler)
    app.add_exception_handler(AgentOrchestratorError, generic_error_handler)
