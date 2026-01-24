"""Image extractor using OCR."""

from typing import TYPE_CHECKING, Any

from agent_orchestrator.files.extractors.base import BaseExtractor

if TYPE_CHECKING:
    from agent_orchestrator.files.ocr.base import BaseOCRProvider


class ImageExtractor(BaseExtractor):
    """Extract text from images using OCR."""

    def __init__(self, ocr_provider: "BaseOCRProvider") -> None:
        self._ocr_provider = ocr_provider
        self._metadata: dict[str, Any] = {}

    async def extract(self, content: bytes, filename: str) -> str:
        """Extract text from image using OCR provider."""
        mime_type = self._detect_mime_type(filename)
        text = await self._ocr_provider.extract_text(content, mime_type)

        self._metadata = {
            "ocr_provider": self._ocr_provider.provider_name,
            "mime_type": mime_type,
        }

        return text

    def get_metadata(self) -> dict[str, Any]:
        return self._metadata

    def _detect_mime_type(self, filename: str) -> str:
        """Detect MIME type from filename."""
        lower = filename.lower()
        if lower.endswith(".png"):
            return "image/png"
        elif lower.endswith((".jpg", ".jpeg")):
            return "image/jpeg"
        elif lower.endswith(".webp"):
            return "image/webp"
        elif lower.endswith(".gif"):
            return "image/gif"
        return "image/png"
