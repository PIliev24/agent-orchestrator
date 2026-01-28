"""FastAPI dependencies."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent_orchestrator.config import settings
from agent_orchestrator.database.session import get_db_session as _get_db_session


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency.

    Yields:
        AsyncSession: Database session.
    """
    async for session in _get_db_session():
        yield session


async def verify_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> str:
    """Verify API key from header.

    Args:
        x_api_key: API key from X-API-Key header.

    Returns:
        Validated API key.

    Raises:
        HTTPException: If API key is missing or invalid.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return x_api_key


# Type aliases for dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
ApiKey = Annotated[str, Depends(verify_api_key)]
