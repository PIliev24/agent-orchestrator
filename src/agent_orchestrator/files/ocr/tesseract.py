"""Tesseract OCR implementation."""

from io import BytesIO

import pytesseract
from PIL import Image

from agent_orchestrator.files.ocr.base import BaseOCRProvider


class TesseractOCR(BaseOCRProvider):
    """Tesseract OCR implementation - Fallback provider."""

    @property
    def provider_name(self) -> str:
        return "tesseract"

    async def extract_text(self, image_content: bytes, mime_type: str) -> str:
        """Extract text from image using Tesseract."""
        image = Image.open(BytesIO(image_content))
        text = pytesseract.image_to_string(image)
        return text.strip()
