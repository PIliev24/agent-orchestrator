"""Session management endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from agent_orchestrator.api.dependencies import get_session_manager, verify_api_key
from agent_orchestrator.core.exceptions import SessionNotFoundError
from agent_orchestrator.core.schemas.session import SessionInfo
from agent_orchestrator.sessions.manager import SessionManager

router = APIRouter()


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
    _: str = Depends(verify_api_key),
) -> SessionInfo:
    """Get session information."""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return SessionInfo(
        id=session.id,
        created_at=session.created_at,
        last_accessed=session.last_accessed,
        message_count=len(session.messages),
        data=session.data,
    )


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Delete a session."""
    deleted = await session_manager.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return {"status": "deleted", "session_id": session_id}


@router.get("/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Get session messages."""
    messages = await session_manager.get_messages(session_id)
    return {"session_id": session_id, "messages": messages}
