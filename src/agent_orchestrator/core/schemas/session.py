"""Session schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SessionMessage(BaseModel):
    """A message in a session."""

    role: str = Field(..., description="Message role (system, user, assistant, tool)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")


class SessionInfo(BaseModel):
    """Session information."""

    id: str = Field(..., description="Session ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_accessed: datetime = Field(..., description="Last access timestamp")
    message_count: int = Field(..., description="Number of messages in session")
    data: dict[str, Any] = Field(default_factory=dict, description="Session data")
