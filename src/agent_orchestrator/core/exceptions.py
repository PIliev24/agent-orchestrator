"""Custom exception classes for the agent orchestrator."""

from uuid import UUID


class AgentOrchestratorError(Exception):
    """Base exception for all agent orchestrator errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(AgentOrchestratorError):
    """Base exception for resource not found errors."""

    resource_type: str = "Resource"

    def __init__(self, resource_id: UUID | str, message: str | None = None):
        self.resource_id = resource_id
        msg = message or f"{self.resource_type} with id '{resource_id}' not found"
        super().__init__(msg, {"resource_id": str(resource_id)})


class AgentNotFoundError(NotFoundError):
    """Raised when an agent is not found."""

    resource_type = "Agent"


class ToolNotFoundError(NotFoundError):
    """Raised when a tool is not found."""

    resource_type = "Tool"


class WorkflowNotFoundError(NotFoundError):
    """Raised when a workflow is not found."""

    resource_type = "Workflow"


class ExecutionNotFoundError(NotFoundError):
    """Raised when an execution is not found."""

    resource_type = "Execution"


class WorkflowNodeNotFoundError(NotFoundError):
    """Raised when a workflow node is not found."""

    resource_type = "WorkflowNode"


class WorkflowEdgeNotFoundError(NotFoundError):
    """Raised when a workflow edge is not found."""

    resource_type = "WorkflowEdge"


class ExecutionStepNotFoundError(NotFoundError):
    """Raised when an execution step is not found."""

    resource_type = "ExecutionStep"


class ValidationError(AgentOrchestratorError):
    """Raised when validation fails."""

    def __init__(self, message: str, field: str | None = None, errors: list | None = None):
        details = {}
        if field:
            details["field"] = field
        if errors:
            details["errors"] = errors
        super().__init__(message, details)


class ProviderError(AgentOrchestratorError):
    """Raised when an AI provider operation fails."""

    def __init__(self, provider: str, message: str, original_error: Exception | None = None):
        self.provider = provider
        self.original_error = original_error
        details = {"provider": provider}
        if original_error:
            details["original_error"] = str(original_error)
        super().__init__(message, details)


class WorkflowCompilationError(AgentOrchestratorError):
    """Raised when workflow compilation fails."""

    def __init__(self, workflow_id: UUID | str, message: str, node_id: str | None = None):
        self.workflow_id = workflow_id
        self.node_id = node_id
        details = {"workflow_id": str(workflow_id)}
        if node_id:
            details["node_id"] = node_id
        super().__init__(message, details)


class ExecutionError(AgentOrchestratorError):
    """Raised when workflow execution fails."""

    def __init__(
        self,
        execution_id: UUID | str,
        message: str,
        node_id: str | None = None,
        original_error: Exception | None = None,
    ):
        self.execution_id = execution_id
        self.node_id = node_id
        self.original_error = original_error
        details = {"execution_id": str(execution_id)}
        if node_id:
            details["node_id"] = node_id
        if original_error:
            details["original_error"] = str(original_error)
        super().__init__(message, details)
