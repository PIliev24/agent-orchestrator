"""Session lifecycle management."""

import asyncio
from datetime import datetime
from typing import Any, Optional

from agent_orchestrator.config import settings
from agent_orchestrator.sessions.store import Session, SessionStore


class SessionManager:
    """High-level session management with background cleanup."""

    def __init__(
        self,
        ttl_seconds: Optional[int] = None,
        cleanup_interval: Optional[int] = None,
    ):
        self._store = SessionStore(ttl_seconds=ttl_seconds or settings.session_ttl)
        self._cleanup_interval = cleanup_interval or settings.session_cleanup_interval
        self._cleanup_task: Optional[asyncio.Task[None]] = None
        self._start_cleanup_task()

    def _start_cleanup_task(self) -> None:
        """Start background cleanup task."""

        async def cleanup_loop() -> None:
            while True:
                try:
                    await asyncio.sleep(self._cleanup_interval)
                    await self._store.cleanup_expired()
                except asyncio.CancelledError:
                    break
                except Exception:
                    pass

        try:
            self._cleanup_task = asyncio.create_task(cleanup_loop())
        except RuntimeError:
            pass

    async def get_or_create(self, session_id: Optional[str]) -> Session:
        """Get existing session or create new one."""
        if session_id:
            session = await self._store.get(session_id)
            if session:
                return session
        return await self._store.create()

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        return await self._store.get(session_id)

    async def get_messages(self, session_id: str) -> list[dict[str, Any]]:
        """Get conversation history for a session."""
        session = await self._store.get(session_id)
        return session.messages if session else []

    async def add_message(self, session_id: str, role: str, content: str) -> bool:
        """Add message to session history."""
        return await self._store.add_message(
            session_id,
            {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def update_data(self, session_id: str, data: dict[str, Any]) -> bool:
        """Update session data."""
        return await self._store.update(session_id, data)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        return await self._store.delete(session_id)

    async def cleanup_all(self) -> None:
        """Cleanup all sessions and stop background task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        self._store._sessions.clear()
