"""Exception handlers for the FastAPI application."""

import logging
from typing import Type

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agent_orchestrator.core.exceptions import (
    AgentConfigError,
    AgentOrchestratorError,
    AuthenticationError,
    FileProcessingError,
    ProviderError,
    ProviderNotConfiguredError,
    SchemaValidationError,
    SessionNotFoundError,
    ToolExecutionError,
    ToolNotFoundError,
    UnsupportedFileTypeError,
    WorkflowConfigError,
)

logger = logging.getLogger(__name__)

EXCEPTION_STATUS_CODES: dict[Type[AgentOrchestratorError], int] = {
    AuthenticationError: 401,
    SessionNotFoundError: 404,
    ToolNotFoundError: 404,
    AgentConfigError: 400,
    WorkflowConfigError: 400,
    SchemaValidationError: 400,
    UnsupportedFileTypeError: 400,
    ProviderNotConfiguredError: 400,
    ProviderError: 502,
    ToolExecutionError: 422,
    FileProcessingError: 422,
}


async def orchestrator_exception_handler(
    request: Request,
    exc: AgentOrchestratorError,
) -> JSONResponse:
    """Handle AgentOrchestratorError and subclasses."""
    status_code = 500
    for exc_type, code in EXCEPTION_STATUS_CODES.items():
        if isinstance(exc, exc_type):
            status_code = code
            break

    logger.error(
        f"Request to {request.url.path} failed with {exc.__class__.__name__}: {exc.message}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": exc.__class__.__name__,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI application."""
    app.add_exception_handler(AgentOrchestratorError, orchestrator_exception_handler)

    for exc_type in EXCEPTION_STATUS_CODES.keys():
        app.add_exception_handler(exc_type, orchestrator_exception_handler)
