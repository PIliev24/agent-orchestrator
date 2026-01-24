"""Base extractor interface."""

from abc import ABC, abstractmethod
from typing import Any


class BaseExtractor(ABC):
    """Abstract base class for file extractors."""

    @abstractmethod
    async def extract(self, content: bytes, filename: str) -> str:
        """Extract text from file content."""
        pass

    def get_metadata(self) -> dict[str, Any]:
        """Get extraction metadata."""
        return {}
