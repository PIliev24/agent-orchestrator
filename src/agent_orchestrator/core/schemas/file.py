"""File processing schemas."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class FileType(str, Enum):
    """Supported file types."""

    TEXT = "text"
    MARKDOWN = "markdown"
    PDF = "pdf"
    IMAGE = "image"
    WORD = "word"


class FileInput(BaseModel):
    """Input file for processing."""

    filename: str = Field(..., description="Original filename")
    content: bytes = Field(..., description="File content as bytes")
    content_type: Optional[str] = Field(default=None, description="MIME type")


class ProcessedFile(BaseModel):
    """Result of file processing."""

    original_filename: str = Field(..., description="Original filename")
    file_type: FileType = Field(..., description="Detected file type")
    extracted_text: str = Field(..., description="Extracted text content")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Processing metadata")


class FileProcessRequest(BaseModel):
    """Request for file processing."""

    ocr_provider: Optional[str] = Field(default="mistral", description="OCR provider to use")
