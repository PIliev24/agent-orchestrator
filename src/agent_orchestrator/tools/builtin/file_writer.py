"""File writer tool for saving data to local files."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from agent_orchestrator.tools.base import BaseTool, ToolResult


class FileWriterTool(BaseTool):
    """Tool for writing content to local files.

    Supports writing text and JSON content to specified file paths.
    Can auto-generate filenames with timestamps if not provided.
    """

    name = "file_writer"
    description = (
        "Write content to a local file. Supports text and JSON formats. "
        "Can specify a full file path or just a directory (auto-generates filename). "
        "Example: {'content': 'hello world', 'file_path': '/tmp/output.txt'}"
    )

    def __init__(self, base_directory: str | None = None):
        """Initialize the file writer tool.

        Args:
            base_directory: Optional base directory for relative paths.
                If not provided, uses current working directory.
        """
        self.base_directory = Path(base_directory) if base_directory else Path.cwd()

    def get_input_schema(self) -> dict:
        """Get the JSON Schema for file writer input."""
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": ["string", "object", "array"],
                    "description": "Content to write to the file. Can be string, object, or array.",
                },
                "file_path": {
                    "type": "string",
                    "description": (
                        "Path to write the file. Can be absolute or relative. "
                        "If a directory is provided, auto-generates filename with timestamp."
                    ),
                },
                "format": {
                    "type": "string",
                    "enum": ["text", "json"],
                    "description": "Output format. 'json' for structured data, 'text' for plain text. Default: auto-detect.",
                },
                "append": {
                    "type": "boolean",
                    "description": "If true, append to existing file instead of overwriting. Default: false.",
                },
            },
            "required": ["content", "file_path"],
        }

    async def execute(
        self,
        content: Any,
        file_path: str,
        format: str | None = None,
        append: bool = False,
        **kwargs: Any,
    ) -> ToolResult:
        """Write content to a file.

        Args:
            content: Content to write (string, dict, or list).
            file_path: Path to write the file to.
            format: Output format ('text' or 'json'). Auto-detects if not provided.
            append: If True, append to existing file.

        Returns:
            ToolResult with the file path written to.
        """
        try:
            # Resolve file path
            resolved_path = self._resolve_path(file_path, content, format)

            # Ensure parent directory exists
            resolved_path.parent.mkdir(parents=True, exist_ok=True)

            # Determine format
            output_format = format or self._detect_format(content, resolved_path)

            # Format content
            if output_format == "json":
                if isinstance(content, str):
                    # Try to parse as JSON first
                    try:
                        content = json.loads(content)
                    except json.JSONDecodeError:
                        pass  # Keep as string
                formatted_content = json.dumps(content, indent=2, ensure_ascii=False)
            else:
                formatted_content = str(content)

            # Write to file
            mode = "a" if append else "w"
            with open(resolved_path, mode, encoding="utf-8") as f:
                f.write(formatted_content)
                if append and not formatted_content.endswith("\n"):
                    f.write("\n")

            return ToolResult(
                success=True,
                output={
                    "file_path": str(resolved_path),
                    "bytes_written": len(formatted_content.encode("utf-8")),
                    "format": output_format,
                    "mode": "appended" if append else "written",
                },
            )

        except PermissionError as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Permission denied writing to {file_path}: {e}",
            )
        except OSError as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"OS error writing to {file_path}: {e}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Failed to write file: {e}",
            )

    def _resolve_path(self, file_path: str, content: Any, format: str | None) -> Path:
        """Resolve the file path, generating filename if needed.

        Args:
            file_path: User-provided path.
            content: Content being written (for extension detection).
            format: Explicit format if provided.

        Returns:
            Resolved Path object.
        """
        path = Path(file_path)

        # Make absolute if relative
        if not path.is_absolute():
            path = self.base_directory / path

        # If it's a directory or ends with /, generate filename
        if path.is_dir() or str(file_path).endswith("/") or str(file_path).endswith(os.sep):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = self._get_extension(content, format)
            filename = f"output_{timestamp}{ext}"
            path = path / filename

        return path

    def _detect_format(self, content: Any, path: Path) -> str:
        """Detect the output format based on content and file extension.

        Args:
            content: Content being written.
            path: Target file path.

        Returns:
            Format string ('json' or 'text').
        """
        # Check file extension
        if path.suffix.lower() == ".json":
            return "json"

        # Check content type
        if isinstance(content, (dict, list)):
            return "json"

        # Try parsing as JSON
        if isinstance(content, str):
            try:
                json.loads(content)
                return "json"
            except json.JSONDecodeError:
                pass

        return "text"

    def _get_extension(self, content: Any, format: str | None) -> str:
        """Get file extension based on content/format.

        Args:
            content: Content being written.
            format: Explicit format if provided.

        Returns:
            File extension with leading dot.
        """
        if format == "json":
            return ".json"
        if format == "text":
            return ".txt"

        # Auto-detect
        if isinstance(content, (dict, list)):
            return ".json"

        if isinstance(content, str):
            try:
                json.loads(content)
                return ".json"
            except json.JSONDecodeError:
                pass

        return ".txt"
