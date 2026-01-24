"""Word document extractor using python-docx."""

from io import BytesIO
from typing import Any

from docx import Document

from agent_orchestrator.files.extractors.base import BaseExtractor


class WordExtractor(BaseExtractor):
    """Extract text from Word documents."""

    def __init__(self) -> None:
        self._metadata: dict[str, Any] = {}

    async def extract(self, content: bytes, filename: str) -> str:
        """Extract text from Word document content."""
        doc_file = BytesIO(content)
        doc = Document(doc_file)

        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

        self._metadata = {
            "paragraph_count": len(paragraphs),
        }

        return "\n\n".join(paragraphs)

    def get_metadata(self) -> dict[str, Any]:
        return self._metadata
