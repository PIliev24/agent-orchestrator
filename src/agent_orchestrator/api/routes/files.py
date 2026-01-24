"""File processing endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile

from agent_orchestrator.api.dependencies import verify_api_key
from agent_orchestrator.core.schemas.file import FileInput, ProcessedFile
from agent_orchestrator.files.processor import FileProcessor

router = APIRouter()


@router.post("/process", response_model=ProcessedFile)
async def process_file(
    file: UploadFile = File(...),
    ocr_provider: Optional[str] = Form(default="mistral"),
    _: str = Depends(verify_api_key),
) -> ProcessedFile:
    """Process a file and extract text content."""
    content = await file.read()
    processor = FileProcessor(ocr_provider=ocr_provider or "mistral")

    result = await processor.process(
        FileInput(
            filename=file.filename or "unknown",
            content=content,
            content_type=file.content_type,
        )
    )

    return result


@router.post("/process/batch", response_model=list[ProcessedFile])
async def process_files_batch(
    files: list[UploadFile] = File(...),
    ocr_provider: Optional[str] = Form(default="mistral"),
    _: str = Depends(verify_api_key),
) -> list[ProcessedFile]:
    """Process multiple files in batch."""
    processor = FileProcessor(ocr_provider=ocr_provider or "mistral")
    results = []

    for file in files:
        content = await file.read()
        result = await processor.process(
            FileInput(
                filename=file.filename or "unknown",
                content=content,
                content_type=file.content_type,
            )
        )
        results.append(result)

    return results
