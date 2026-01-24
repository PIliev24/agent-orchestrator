"""Mistral OCR (Pixtral) implementation."""

import base64

import httpx

from agent_orchestrator.config import settings
from agent_orchestrator.files.ocr.base import BaseOCRProvider


class MistralOCR(BaseOCRProvider):
    """Mistral OCR (Pixtral) implementation - Primary OCR provider."""

    def __init__(self) -> None:
        self._api_key = settings.mistral_api_key
        self._base_url = "https://api.mistral.ai/v1"

    @property
    def provider_name(self) -> str:
        return "mistral"

    async def extract_text(self, image_content: bytes, mime_type: str) -> str:
        """Extract text from image using Mistral Pixtral."""
        if not self._api_key:
            raise ValueError("Mistral API key not configured")

        base64_image = base64.b64encode(image_content).decode("utf-8")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "pixtral-12b-2409",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Extract all text from this image. Return only the extracted text, preserving the original layout and formatting as much as possible.",
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime_type};base64,{base64_image}"
                                    },
                                },
                            ],
                        }
                    ],
                    "max_tokens": 4096,
                },
                timeout=60.0,
            )

            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
