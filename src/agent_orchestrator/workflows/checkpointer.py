"""LangGraph checkpointer configuration."""

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from agent_orchestrator.config import settings

# Global checkpointer instance and context manager
_checkpointer: Optional[AsyncPostgresSaver] = None
_context_manager: Optional[Any] = None


async def get_checkpointer() -> AsyncPostgresSaver:
    """Get or create the PostgreSQL checkpointer.

    Returns:
        AsyncPostgresSaver instance for workflow state persistence.
    """
    global _checkpointer, _context_manager

    if _checkpointer is None:
        # Create the async context manager
        _context_manager = AsyncPostgresSaver.from_conn_string(
            settings.checkpoint_db_uri
        )
        # Enter the context manager to get the checkpointer
        _checkpointer = await _context_manager.__aenter__()

        # Setup the checkpointer tables
        await _checkpointer.setup()

    return _checkpointer


async def close_checkpointer() -> None:
    """Close the checkpointer connection."""
    global _checkpointer, _context_manager

    if _context_manager is not None:
        await _context_manager.__aexit__(None, None, None)
        _context_manager = None
        _checkpointer = None
