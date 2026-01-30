"""HTTP tool for making web requests."""

from typing import Any

import httpx

from agent_orchestrator.tools.base import BaseTool, ToolResult


class HttpTool(BaseTool):
    """Tool for making HTTP requests.

    Supports GET and POST methods with optional headers and body.
    """

    name = "http_request"
    description = (
        "Make an HTTP request to a URL. Supports GET and POST methods. "
        "Returns the response body as text."
    )

    def __init__(self, timeout: float = 30.0, max_response_size: int = 100_000):
        """Initialize the HTTP tool.

        Args:
            timeout: Request timeout in seconds.
            max_response_size: Maximum response size in bytes.
        """
        self.timeout = timeout
        self.max_response_size = max_response_size

    def get_input_schema(self) -> dict:
        """Get the JSON Schema for HTTP tool input."""
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to request",
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST"],
                    "description": "HTTP method (default: GET)",
                    "default": "GET",
                },
                "headers": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "description": "Optional request headers",
                },
                "body": {
                    "type": "string",
                    "description": "Optional request body (for POST)",
                },
            },
            "required": ["url"],
        }

    async def execute(
        self,
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Make an HTTP request.

        Args:
            url: URL to request.
            method: HTTP method (GET or POST).
            headers: Optional request headers.
            body: Optional request body.

        Returns:
            ToolResult with response body or error.
        """
        method = method.upper()
        if method not in ("GET", "POST"):
            return ToolResult(
                success=False,
                output=None,
                error=f"Unsupported HTTP method: {method}",
            )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                else:  # POST
                    response = await client.post(
                        url,
                        headers=headers,
                        content=body,
                    )

                # Check response size
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > self.max_response_size:
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"Response too large: {content_length} bytes",
                    )

                # Read response
                text = response.text[: self.max_response_size]

                return ToolResult(
                    success=True,
                    output={
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "body": text,
                    },
                )

        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                output=None,
                error=f"Request timed out after {self.timeout} seconds",
            )
        except httpx.RequestError as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Request failed: {e}",
            )
