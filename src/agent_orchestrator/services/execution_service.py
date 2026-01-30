"""Execution service for running workflows."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agent_orchestrator.core.exceptions import (
    ExecutionError,
    ExecutionNotFoundError,
    ExecutionStepNotFoundError,
    WorkflowNotFoundError,
)
from agent_orchestrator.core.schemas.execution import (
    ExecutionCreate,
    ExecutionEventData,
    ExecutionResponse,
    ExecutionStatusResponse,
    ExecutionStepResponse,
)
from agent_orchestrator.database.models.execution import (
    Execution,
    ExecutionStatus,
    ExecutionStep,
)
from agent_orchestrator.database.models.workflow import Workflow
from agent_orchestrator.workflows.compiler import WorkflowCompiler


def _serialize_output(data: Any) -> Any:
    """Serialize output data for JSON storage.

    Converts non-serializable objects like LangChain messages to dicts.
    """
    if data is None:
        return None
    if isinstance(data, (str, int, float, bool)):
        return data
    if isinstance(data, list):
        return [_serialize_output(item) for item in data]
    if isinstance(data, dict):
        return {k: _serialize_output(v) for k, v in data.items()}
    # Handle LangChain message objects
    if hasattr(data, "content"):
        return {"type": type(data).__name__, "content": data.content}
    # Fallback to string representation
    return str(data)


class ExecutionService:
    """Service for executing workflows."""

    def __init__(self, session: AsyncSession):
        """Initialize the service.

        Args:
            session: Database session.
        """
        self._session = session

    async def execute(self, data: ExecutionCreate) -> ExecutionResponse:
        """Execute a workflow.

        Args:
            data: Execution parameters.

        Returns:
            Execution response with results.

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist.
            ExecutionError: If execution fails.
        """
        # Validate workflow exists
        workflow = await self._session.get(Workflow, data.workflow_id)
        if not workflow:
            raise WorkflowNotFoundError(data.workflow_id)

        # Generate thread_id if not provided
        thread_id = data.thread_id or f"exec_{uuid.uuid4().hex[:12]}"

        # Create execution record
        execution = Execution(
            workflow_id=data.workflow_id,
            thread_id=thread_id,
            status=ExecutionStatus.PENDING,
            input_data=data.input,
        )
        self._session.add(execution)
        await self._session.flush()

        try:
            # Mark as running
            execution.status = ExecutionStatus.RUNNING
            execution.started_at = datetime.now(UTC)
            await self._session.flush()

            # Compile and execute workflow
            compiler = WorkflowCompiler(self._session)
            graph = await compiler.compile(data.workflow_id)

            # Prepare input state
            input_state = {
                "input": data.input,
                "messages": [],
                "intermediate": {},
                "metadata": data.config or {},
            }

            # Execute the graph
            config = {"configurable": {"thread_id": thread_id}}
            result = await graph.ainvoke(input_state, config)

            # Mark as completed
            execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = datetime.now(UTC)
            execution.output_data = {
                "output": result.get("output"),
                "intermediate": result.get("intermediate", {}),
            }
            await self._session.flush()

        except Exception as e:
            # Mark as failed
            execution.status = ExecutionStatus.FAILED
            execution.completed_at = datetime.now(UTC)
            execution.error_message = str(e)
            await self._session.flush()

            raise ExecutionError(
                execution_id=execution.id,
                message=f"Workflow execution failed: {e}",
                original_error=e,
            )

        return await self.get(execution.id)

    async def execute_stream(
        self,
        data: ExecutionCreate,
    ) -> AsyncIterator[ExecutionEventData]:
        """Execute a workflow with streaming events.

        Args:
            data: Execution parameters.

        Yields:
            ExecutionEventData for each event during execution.
        """
        # Validate workflow exists
        workflow = await self._session.get(Workflow, data.workflow_id)
        if not workflow:
            raise WorkflowNotFoundError(data.workflow_id)

        # Generate thread_id if not provided
        thread_id = data.thread_id or f"exec_{uuid.uuid4().hex[:12]}"

        # Create execution record
        execution = Execution(
            workflow_id=data.workflow_id,
            thread_id=thread_id,
            status=ExecutionStatus.PENDING,
            input_data=data.input,
        )
        self._session.add(execution)
        await self._session.flush()

        yield ExecutionEventData(
            event_type="execution_started",
            data={"execution_id": str(execution.id), "thread_id": thread_id},
        )

        try:
            # Mark as running
            execution.status = ExecutionStatus.RUNNING
            execution.started_at = datetime.now(UTC)
            await self._session.flush()

            # Compile workflow
            compiler = WorkflowCompiler(self._session)
            graph = await compiler.compile(data.workflow_id)

            # Prepare input state
            input_state = {
                "input": data.input,
                "messages": [],
                "intermediate": {},
                "metadata": data.config or {},
            }

            # Execute with streaming
            config = {"configurable": {"thread_id": thread_id}}

            async for event in graph.astream(input_state, config):
                # Extract node name from event
                if isinstance(event, dict):
                    for node_name, node_output in event.items():
                        yield ExecutionEventData(
                            event_type="node_complete",
                            node_id=node_name,
                            data={"output": node_output},
                        )

                        # Record execution step (serialize to handle non-JSON types)
                        serialized_output = _serialize_output(node_output)
                        step = ExecutionStep(
                            execution_id=execution.id,
                            node_id=node_name,
                            status=ExecutionStatus.COMPLETED,
                            output_data=serialized_output
                            if isinstance(serialized_output, dict)
                            else {"result": serialized_output},
                            started_at=datetime.now(UTC),
                            completed_at=datetime.now(UTC),
                        )
                        self._session.add(step)

            # Get final state
            final_state = await graph.aget_state(config)

            # Mark as completed
            execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = datetime.now(UTC)
            execution.output_data = {
                "output": final_state.values.get("output") if final_state else None,
            }
            await self._session.flush()

            yield ExecutionEventData(
                event_type="execution_complete",
                data={
                    "execution_id": str(execution.id),
                    "output": execution.output_data,
                },
            )

        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.completed_at = datetime.now(UTC)
            execution.error_message = str(e)
            await self._session.flush()

            yield ExecutionEventData(
                event_type="error",
                data={
                    "execution_id": str(execution.id),
                    "error": str(e),
                },
            )

    async def get(self, execution_id: UUID) -> ExecutionResponse:
        """Get an execution by ID.

        Args:
            execution_id: Execution ID.

        Returns:
            Execution response.

        Raises:
            ExecutionNotFoundError: If execution doesn't exist.
        """
        execution = await self._get_execution(execution_id)
        return self._to_response(execution)

    async def get_status(self, execution_id: UUID) -> ExecutionStatusResponse:
        """Get lightweight status for an execution.

        Args:
            execution_id: Execution ID.

        Returns:
            Execution status response.
        """
        execution = await self._get_execution(execution_id)

        # Calculate progress
        progress = None
        if execution.steps:
            completed = sum(1 for s in execution.steps if s.status == ExecutionStatus.COMPLETED)
            total = len(execution.steps)
            current = next(
                (s.node_id for s in execution.steps if s.status == ExecutionStatus.RUNNING),
                None,
            )
            progress = {
                "completed_nodes": completed,
                "total_nodes": total,
                "current_node": current,
                "percentage": int((completed / total) * 100) if total > 0 else 0,
            }

        return ExecutionStatusResponse(
            id=execution.id,
            status=execution.status,
            current_node=progress.get("current_node") if progress else None,
            progress=progress,
            error_message=execution.error_message,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
        )

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        workflow_id: UUID | None = None,
        status: ExecutionStatus | None = None,
    ) -> tuple[list[ExecutionResponse], int]:
        """List executions with pagination.

        Args:
            page: Page number (1-indexed).
            page_size: Items per page.
            workflow_id: Optional filter by workflow.
            status: Optional filter by status.

        Returns:
            Tuple of (executions list, total count).
        """
        query = select(Execution).options(selectinload(Execution.steps))

        if workflow_id:
            query = query.where(Execution.workflow_id == workflow_id)
        if status:
            query = query.where(Execution.status == status)

        # Get total count
        count_query = select(func.count()).select_from(Execution)
        if workflow_id:
            count_query = count_query.where(Execution.workflow_id == workflow_id)
        if status:
            count_query = count_query.where(Execution.status == status)
        total = await self._session.scalar(count_query)

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(Execution.created_at.desc())

        result = await self._session.execute(query)
        executions = result.scalars().all()

        return [self._to_response(e) for e in executions], total or 0

    async def cancel(self, execution_id: UUID) -> ExecutionResponse:
        """Cancel a running execution.

        Args:
            execution_id: Execution ID.

        Returns:
            Updated execution response.

        Raises:
            ExecutionNotFoundError: If execution doesn't exist.
            ExecutionError: If execution cannot be cancelled.
        """
        execution = await self._get_execution(execution_id)

        if execution.status not in (ExecutionStatus.PENDING, ExecutionStatus.RUNNING):
            raise ExecutionError(
                execution_id=execution_id,
                message=f"Cannot cancel execution with status {execution.status}",
            )

        execution.status = ExecutionStatus.CANCELLED
        execution.completed_at = datetime.now(UTC)
        await self._session.flush()

        return self._to_response(execution)

    async def delete(self, execution_id: UUID) -> None:
        """Delete an execution."""
        execution = await self._get_execution(execution_id)
        await self._session.delete(execution)

    async def resume(self, execution_id: UUID) -> ExecutionResponse:
        """Resume a cancelled or failed execution."""
        execution = await self._get_execution(execution_id)

        if execution.status not in (ExecutionStatus.CANCELLED, ExecutionStatus.FAILED):
            raise ExecutionError(
                execution_id=execution_id,
                message=f"Cannot resume execution with status {execution.status}",
            )

        # Re-execute using existing data
        data = ExecutionCreate(
            workflow_id=execution.workflow_id,
            input=execution.input_data or {},
            thread_id=execution.thread_id,
        )
        return await self.execute(data)

    async def restart(self, execution_id: UUID) -> ExecutionResponse:
        """Restart an execution from scratch with a new thread."""
        execution = await self._get_execution(execution_id)

        data = ExecutionCreate(
            workflow_id=execution.workflow_id,
            input=execution.input_data or {},
        )
        return await self.execute(data)

    async def list_steps(
        self, execution_id: UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[ExecutionStepResponse], int]:
        """List steps for an execution."""
        await self._get_execution(execution_id)

        count_query = (
            select(func.count())
            .select_from(ExecutionStep)
            .where(ExecutionStep.execution_id == execution_id)
        )
        total = await self._session.scalar(count_query)

        offset = (page - 1) * page_size
        query = (
            select(ExecutionStep)
            .where(ExecutionStep.execution_id == execution_id)
            .order_by(ExecutionStep.started_at)
            .offset(offset)
            .limit(page_size)
        )
        result = await self._session.execute(query)
        steps = result.scalars().all()

        return [self._step_to_response(s) for s in steps], total or 0

    async def get_step(self, execution_id: UUID, step_id: UUID) -> ExecutionStepResponse:
        """Get a single execution step."""
        query = select(ExecutionStep).where(
            ExecutionStep.id == step_id,
            ExecutionStep.execution_id == execution_id,
        )
        result = await self._session.execute(query)
        step = result.scalar_one_or_none()
        if not step:
            raise ExecutionStepNotFoundError(step_id)
        return self._step_to_response(step)

    def _step_to_response(self, step: ExecutionStep) -> ExecutionStepResponse:
        """Convert ExecutionStep model to response schema."""
        return ExecutionStepResponse(
            id=step.id,
            node_id=step.node_id,
            status=step.status,
            input_data=step.input_data,
            output_data=step.output_data,
            error_message=step.error_message,
            started_at=step.started_at,
            completed_at=step.completed_at,
        )

    async def _get_execution(self, execution_id: UUID) -> Execution:
        """Get an execution by ID or raise error.

        Args:
            execution_id: Execution ID.

        Returns:
            Execution model.

        Raises:
            ExecutionNotFoundError: If not found.
        """
        query = (
            select(Execution)
            .options(selectinload(Execution.steps))
            .where(Execution.id == execution_id)
        )
        result = await self._session.execute(query)
        execution = result.scalar_one_or_none()

        if not execution:
            raise ExecutionNotFoundError(execution_id)

        return execution

    def _to_response(self, execution: Execution) -> ExecutionResponse:
        """Convert Execution model to response schema.

        Args:
            execution: Execution model.

        Returns:
            ExecutionResponse schema.
        """
        return ExecutionResponse(
            id=execution.id,
            workflow_id=execution.workflow_id,
            thread_id=execution.thread_id,
            status=execution.status,
            input_data=execution.input_data,
            output_data=execution.output_data,
            error_message=execution.error_message,
            created_at=execution.created_at,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            steps=[
                ExecutionStepResponse(
                    id=s.id,
                    node_id=s.node_id,
                    status=s.status,
                    input_data=s.input_data,
                    output_data=s.output_data,
                    error_message=s.error_message,
                    started_at=s.started_at,
                    completed_at=s.completed_at,
                )
                for s in execution.steps
            ],
        )
