"""PDF extractor using pypdf."""

from io import BytesIO
from typing import Any

from pypdf import PdfReader

from agent_orchestrator.files.extractors.base import BaseExtractor


class PDFExtractor(BaseExtractor):
    """Extract text from PDF files."""

    def __init__(self) -> None:
        self._metadata: dict[str, Any] = {}

    async def extract(self, content: bytes, filename: str) -> str:
        """Extract text from PDF content."""
        pdf_file = BytesIO(content)
        reader = PdfReader(pdf_file)

        self._metadata = {
            "page_count": len(reader.pages),
        }

        extracted_text = []
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                extracted_text.append(f"[Page {page_num + 1}]\n{page_text}")

        return "\n\n".join(extracted_text)

    def get_metadata(self) -> dict[str, Any]:
        return self._metadata
