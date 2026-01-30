"""Mistral OCR tool for processing documents with AI-powered OCR."""

import base64
import os
from pathlib import Path
from typing import Any

from agent_orchestrator.tools.base import BaseTool, ToolResult


class MistralOCRTool(BaseTool):
    """Tool for processing documents using Mistral AI's OCR capabilities.

    Supports PDF, DOCX, and image files. Extracts text content and
    returns it as markdown along with any extracted images.
    """

    name = "mistral_ocr"
    description = (
        "Process a document (PDF, DOCX, or image) using Mistral AI's OCR. "
        "Returns extracted text as markdown and base64-encoded images. "
        "Supports: PDF, DOCX, PNG, JPG, JPEG, WEBP."
    )

    # Supported file extensions and their MIME types
    _mime_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }

    def __init__(self, api_key: str | None = None):
        """Initialize the Mistral OCR tool.

        Args:
            api_key: Mistral API key. If not provided, uses settings or env var.
        """
        self.api_key = self._resolve_api_key(api_key)

    @staticmethod
    def _resolve_api_key(api_key: str | None) -> str | None:
        """Resolve API key from argument, environment, or settings."""
        if api_key:
            return api_key
        if os.environ.get("MISTRAL_API_KEY"):
            return os.environ["MISTRAL_API_KEY"]
        try:
            from agent_orchestrator.config import settings

            return getattr(settings, "mistral_api_key", None)
        except Exception:
            return None

    def get_input_schema(self) -> dict:
        """Get the JSON Schema for Mistral OCR input."""
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the document file (PDF, DOCX, PNG, JPG, JPEG, WEBP)",
                },
                "include_images": {
                    "type": "boolean",
                    "description": "Whether to extract and return images (default: true)",
                    "default": True,
                },
                "pages": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Specific page numbers to process (1-indexed). "
                    "If not provided, all pages are processed.",
                },
            },
            "required": ["file_path"],
        }

    async def execute(
        self,
        file_path: str,
        include_images: bool = True,
        pages: list[int] | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Process a document using Mistral AI's OCR.

        Args:
            file_path: Path to the document file.
            include_images: Whether to extract and return images.
            pages: Specific page numbers to process (1-indexed).

        Returns:
            ToolResult with markdown text and extracted images.
        """
        if not self.api_key:
            return ToolResult(
                success=False,
                output=None,
                error="MISTRAL_API_KEY not configured",
            )

        try:
            from mistralai import Mistral
        except ImportError:
            return ToolResult(
                success=False,
                output=None,
                error="mistralai package not installed. Run: pip install mistralai",
            )

        # Validate file exists and has supported extension
        path = Path(file_path)
        if not path.exists():
            return ToolResult(
                success=False,
                output=None,
                error=f"File not found: {file_path}",
            )

        ext = path.suffix.lower()
        if ext not in self._mime_types:
            supported = ", ".join(self._mime_types.keys())
            return ToolResult(
                success=False,
                output=None,
                error=f"Unsupported file type: {ext}. Supported: {supported}",
            )

        try:
            client = Mistral(api_key=self.api_key)

            # Upload file and get signed URL
            with open(file_path, "rb") as f:
                file_content = f.read()

            if ext in (".pdf", ".docx"):
                uploaded_file = client.files.upload(
                    file={
                        "file_name": path.name,
                        "content": file_content,
                    },
                    purpose="ocr",
                )

                # Get signed URL for processing
                signed_url = client.files.get_signed_url(file_id=uploaded_file.id)

                # Process OCR
                ocr_response = client.ocr.process(
                    model="mistral-ocr-latest",
                    document={
                        "type": "document_url",
                        "document_url": signed_url.url,
                    },
                    include_image_base64=include_images,
                )
            else:
                # For images, use base64 directly
                base64_content = base64.b64encode(file_content).decode("utf-8")
                mime_type = self._mime_types[ext]

                ocr_response = client.ocr.process(
                    model="mistral-ocr-latest",
                    document={
                        "type": "image_url",
                        "image_url": f"data:{mime_type};base64,{base64_content}",
                    },
                    include_image_base64=include_images,
                )

            # Extract text from all pages or specific pages
            all_pages = ocr_response.pages
            if pages:
                # Filter to requested pages (convert 1-indexed to 0-indexed)
                page_indices = [p - 1 for p in pages if 0 <= p - 1 < len(all_pages)]
                selected_pages = [all_pages[i] for i in page_indices]
            else:
                selected_pages = all_pages

            # Combine markdown content from pages
            markdown_parts = []
            images = []

            for i, page in enumerate(selected_pages):
                page_num = pages[i] if pages else i + 1
                markdown_parts.append(f"## Page {page_num}\n\n{page.markdown}")

                # Extract images if requested
                if include_images and hasattr(page, "images") and page.images:
                    for img_idx, img in enumerate(page.images):
                        images.append(
                            {
                                "page": page_num,
                                "index": img_idx,
                                "id": img.id if hasattr(img, "id") else f"img_{page_num}_{img_idx}",
                                "base64": img.image_base64
                                if hasattr(img, "image_base64")
                                else None,
                            }
                        )

            combined_markdown = "\n\n".join(markdown_parts)

            return ToolResult(
                success=True,
                output={
                    "markdown": combined_markdown,
                    "total_pages": len(all_pages),
                    "processed_pages": len(selected_pages),
                    "images": images if include_images else [],
                    "file_name": path.name,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"OCR processing failed: {str(e)}",
            )
