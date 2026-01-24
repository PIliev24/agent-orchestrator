"""FastAPI dependencies."""

from fastapi import Header, HTTPException, Request

from agent_orchestrator.config import settings
from agent_orchestrator.sessions.manager import SessionManager


def get_session_manager(request: Request) -> SessionManager:
    """Get session manager from app state."""
    return request.app.state.session_manager


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Verify API key from header."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key
