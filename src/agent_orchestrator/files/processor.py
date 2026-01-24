"""Main file processing coordinator."""

import mimetypes
from typing import Optional

from agent_orchestrator.core.exceptions import FileProcessingError, UnsupportedFileTypeError
from agent_orchestrator.core.schemas.file import FileInput, FileType, ProcessedFile
from agent_orchestrator.files.extractors.base import BaseExtractor
from agent_orchestrator.files.extractors.image import ImageExtractor
from agent_orchestrator.files.extractors.pdf import PDFExtractor
from agent_orchestrator.files.extractors.text import TextExtractor
from agent_orchestrator.files.extractors.word import WordExtractor
from agent_orchestrator.files.ocr.factory import OCRFactory


class FileProcessor:
    """Coordinates file processing across different file types."""

    MIME_TYPE_MAP = {
        "text/plain": FileType.TEXT,
        "text/markdown": FileType.MARKDOWN,
        "application/pdf": FileType.PDF,
        "image/png": FileType.IMAGE,
        "image/jpeg": FileType.IMAGE,
        "image/jpg": FileType.IMAGE,
        "image/webp": FileType.IMAGE,
        "image/gif": FileType.IMAGE,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileType.WORD,
        "application/msword": FileType.WORD,
    }

    EXTENSION_MAP = {
        ".txt": FileType.TEXT,
        ".md": FileType.MARKDOWN,
        ".markdown": FileType.MARKDOWN,
        ".pdf": FileType.PDF,
        ".png": FileType.IMAGE,
        ".jpg": FileType.IMAGE,
        ".jpeg": FileType.IMAGE,
        ".webp": FileType.IMAGE,
        ".gif": FileType.IMAGE,
        ".docx": FileType.WORD,
        ".doc": FileType.WORD,
    }

    def __init__(self, ocr_provider: str = "mistral"):
        self._ocr_provider = OCRFactory.get_provider(ocr_provider)
        self._extractors: dict[FileType, BaseExtractor] = {
            FileType.TEXT: TextExtractor(),
            FileType.MARKDOWN: TextExtractor(),
            FileType.PDF: PDFExtractor(),
            FileType.WORD: WordExtractor(),
            FileType.IMAGE: ImageExtractor(self._ocr_provider),
        }

    async def process(self, file_input: FileInput) -> ProcessedFile:
        """Process a file and extract text content."""
        try:
            file_type = self._detect_file_type(file_input)
            extractor = self._extractors.get(file_type)

            if not extractor:
                raise UnsupportedFileTypeError(file_input.filename, file_type.value)

            extracted_text = await extractor.extract(file_input.content, file_input.filename)

            return ProcessedFile(
                original_filename=file_input.filename,
                file_type=file_type,
                extracted_text=extracted_text,
                metadata=extractor.get_metadata(),
            )
        except UnsupportedFileTypeError:
            raise
        except Exception as e:
            raise FileProcessingError(file_input.filename, str(e))

    def _detect_file_type(self, file_input: FileInput) -> FileType:
        """Detect file type from filename or content type."""
        if file_input.content_type:
            file_type = self.MIME_TYPE_MAP.get(file_input.content_type)
            if file_type:
                return file_type

        filename = file_input.filename.lower()
        for ext, file_type in self.EXTENSION_MAP.items():
            if filename.endswith(ext):
                return file_type

        mime_type, _ = mimetypes.guess_type(file_input.filename)
        if mime_type:
            file_type = self.MIME_TYPE_MAP.get(mime_type)
            if file_type:
                return file_type

        return FileType.TEXT
