"""Base OCR provider interface."""

from abc import ABC, abstractmethod


class BaseOCRProvider(ABC):
    """Abstract base class for OCR providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier."""
        pass

    @abstractmethod
    async def extract_text(self, image_content: bytes, mime_type: str) -> str:
        """Extract text from image."""
        pass
