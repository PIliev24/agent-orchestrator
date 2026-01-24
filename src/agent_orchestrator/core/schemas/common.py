"""Shared response schemas."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Error detail information."""

    type: str = Field(..., description="Error type name")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional error details")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: ErrorDetail


class SuccessResponse(BaseModel):
    """Standard success response."""

    success: bool = True
    message: str = Field(default="Operation completed successfully")
    data: Optional[dict[str, Any]] = None


class BaseResponse(BaseModel):
    """Base response with status, message, and optional data."""

    status: str = Field(..., description="Response status (success, error)")
    message: str = Field(..., description="Response message")
    data: Optional[Any] = Field(default=None, description="Response data payload")
