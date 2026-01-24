"""Server-Sent Events (SSE) utilities for streaming responses."""

from dataclasses import dataclass
from typing import AsyncIterator, Optional


@dataclass
class SSEMessage:
    """Represents a Server-Sent Events message."""

    event: str
    data: str
    id: Optional[str] = None
    retry: Optional[int] = None


def format_sse_message(msg: SSEMessage) -> str:
    """Format an SSE message as a string suitable for HTTP streaming."""
    lines = []

    if msg.id is not None:
        lines.append(f"id: {msg.id}")

    if msg.retry is not None:
        lines.append(f"retry: {msg.retry}")

    lines.append(f"event: {msg.event}")

    for line in msg.data.split("\n"):
        lines.append(f"data: {line}")

    return "\n".join(lines) + "\n\n"


async def create_sse_generator(
    async_iter: AsyncIterator[str],
) -> AsyncIterator[dict]:
    """Create an SSE generator from an async iterator of string chunks."""
    async for chunk in async_iter:
        yield {"event": "token", "data": chunk}

    yield {"event": "done", "data": ""}
