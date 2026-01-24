"""In-memory session store with TTL."""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional


@dataclass
class Session:
    """In-memory session container."""

    id: str
    created_at: datetime
    last_accessed: datetime
    ttl_seconds: int
    data: dict[str, Any] = field(default_factory=dict)
    messages: list[dict[str, Any]] = field(default_factory=list)

    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.utcnow() > self.last_accessed + timedelta(seconds=self.ttl_seconds)

    def touch(self) -> None:
        """Update last accessed time."""
        self.last_accessed = datetime.utcnow()


class SessionStore:
    """In-memory session storage with TTL."""

    def __init__(self, ttl_seconds: int = 3600):
        self._sessions: dict[str, Session] = {}
        self._ttl_seconds = ttl_seconds
        self._lock = asyncio.Lock()

    async def create(self) -> Session:
        """Create a new session."""
        async with self._lock:
            session = Session(
                id=str(uuid.uuid4()),
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                ttl_seconds=self._ttl_seconds,
            )
            self._sessions[session.id] = session
            return session

    async def get(self, session_id: str) -> Optional[Session]:
        """Get a session by ID, returns None if expired or not found."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if session.is_expired():
                del self._sessions[session_id]
                return None
            session.touch()
            return session

    async def update(self, session_id: str, data: dict[str, Any]) -> bool:
        """Update session data."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.is_expired():
                return False
            session.data.update(data)
            session.touch()
            return True

    async def add_message(self, session_id: str, message: dict[str, Any]) -> bool:
        """Add a message to session history."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.is_expired():
                return False
            session.messages.append(message)
            session.touch()
            return True

    async def delete(self, session_id: str) -> bool:
        """Delete a session."""
        async with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    async def cleanup_expired(self) -> int:
        """Remove all expired sessions."""
        async with self._lock:
            expired = [sid for sid, session in self._sessions.items() if session.is_expired()]
            for sid in expired:
                del self._sessions[sid]
            return len(expired)
