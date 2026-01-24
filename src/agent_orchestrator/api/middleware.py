"""Middleware for API key authentication."""

from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from agent_orchestrator.config import settings


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for X-API-Key header authentication."""

    EXEMPT_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/"}

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """Process request and validate API key."""
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        if request.url.path.startswith("/ws"):
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "type": "AuthenticationError",
                        "message": "Missing X-API-Key header",
                        "details": {},
                    }
                },
            )

        if api_key != settings.api_key:
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "type": "AuthenticationError",
                        "message": "Invalid API key",
                        "details": {},
                    }
                },
            )

        return await call_next(request)
