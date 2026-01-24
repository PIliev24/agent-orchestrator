"""Custom exception classes for the agent orchestrator."""

from typing import Any, Optional


class AgentOrchestratorError(Exception):
    """Base exception for all orchestrator errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ProviderError(AgentOrchestratorError):
    """Error from AI provider (OpenAI, Anthropic, Google)."""

    def __init__(
        self,
        provider: str,
        message: str,
        status_code: Optional[int] = None,
    ):
        super().__init__(f"Provider '{provider}' error: {message}")
        self.provider = provider
        self.status_code = status_code


class ProviderNotConfiguredError(AgentOrchestratorError):
    """Provider API key not configured."""

    def __init__(self, provider: str):
        super().__init__(f"Provider '{provider}' API key not configured")
        self.provider = provider


class AgentConfigError(AgentOrchestratorError):
    """Invalid agent configuration."""

    pass


class WorkflowConfigError(AgentOrchestratorError):
    """Invalid workflow configuration."""

    pass


class ToolExecutionError(AgentOrchestratorError):
    """Error during tool execution."""

    def __init__(self, tool_name: str, message: str):
        super().__init__(f"Tool '{tool_name}' execution failed: {message}")
        self.tool_name = tool_name


class ToolNotFoundError(AgentOrchestratorError):
    """Tool not found in registry."""

    def __init__(self, tool_name: str):
        super().__init__(f"Tool '{tool_name}' not found")
        self.tool_name = tool_name


class FileProcessingError(AgentOrchestratorError):
    """Error during file processing."""

    def __init__(self, filename: str, message: str):
        super().__init__(f"Failed to process file '{filename}': {message}")
        self.filename = filename


class UnsupportedFileTypeError(AgentOrchestratorError):
    """Unsupported file type."""

    def __init__(self, filename: str, file_type: str):
        super().__init__(f"Unsupported file type '{file_type}' for file '{filename}'")
        self.filename = filename
        self.file_type = file_type


class SessionNotFoundError(AgentOrchestratorError):
    """Session not found or expired."""

    def __init__(self, session_id: str):
        super().__init__(f"Session '{session_id}' not found or expired")
        self.session_id = session_id


class AuthenticationError(AgentOrchestratorError):
    """Authentication failure."""

    pass


class SchemaValidationError(AgentOrchestratorError):
    """Output schema validation failure."""

    def __init__(self, message: str, schema: Optional[dict[str, Any]] = None):
        super().__init__(f"Schema validation failed: {message}")
        self.schema = schema
