"""OCR provider factory."""

from agent_orchestrator.files.ocr.base import BaseOCRProvider
from agent_orchestrator.files.ocr.mistral import MistralOCR
from agent_orchestrator.files.ocr.tesseract import TesseractOCR


class OCRFactory:
    """Factory for creating OCR provider instances."""

    _providers: dict[str, type[BaseOCRProvider]] = {
        "mistral": MistralOCR,
        "tesseract": TesseractOCR,
    }

    @classmethod
    def get_provider(cls, provider_name: str = "mistral") -> BaseOCRProvider:
        """Get OCR provider instance."""
        provider_class = cls._providers.get(provider_name)
        if not provider_class:
            raise ValueError(f"Unknown OCR provider: {provider_name}")
        return provider_class()

    @classmethod
    def list_providers(cls) -> list[str]:
        """List available OCR providers."""
        return list(cls._providers.keys())
