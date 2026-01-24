"""Plain text extractor."""

from typing import Any

from agent_orchestrator.files.extractors.base import BaseExtractor


class TextExtractor(BaseExtractor):
    """Extract text from plain text files."""

    def __init__(self) -> None:
        self._metadata: dict[str, Any] = {}

    async def extract(self, content: bytes, filename: str) -> str:
        """Extract text from bytes, trying utf-8 then latin-1."""
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        self._metadata = {
            "character_count": len(text),
            "line_count": text.count("\n") + 1,
        }
        return text

    def get_metadata(self) -> dict[str, Any]:
        return self._metadata
