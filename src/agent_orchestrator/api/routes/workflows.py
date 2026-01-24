"""Workflow execution endpoints."""

import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sse_starlette.sse import EventSourceResponse

from agent_orchestrator.api.dependencies import get_session_manager, verify_api_key
from agent_orchestrator.core.schemas.workflow import (
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
)
from agent_orchestrator.sessions.manager import SessionManager
from agent_orchestrator.streaming.websocket import WorkflowWebSocketHandler
from agent_orchestrator.workflows.builder import WorkflowBuilder

router = APIRouter()


@router.post("/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    request: WorkflowExecutionRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    _: str = Depends(verify_api_key),
) -> WorkflowExecutionResponse:
    """Execute a workflow with the given configuration."""
    builder = WorkflowBuilder(session_manager)
    graph = builder.build(request.workflow)

    result = await graph.ainvoke(request.input)

    return WorkflowExecutionResponse(
        workflow_name=request.workflow.name,
        output=result,
        session_id=request.session_id,
    )


@router.post("/execute/stream")
async def execute_workflow_stream(
    request: WorkflowExecutionRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    _: str = Depends(verify_api_key),
) -> EventSourceResponse:
    """Execute workflow with SSE streaming for progress updates."""
    builder = WorkflowBuilder(session_manager)
    graph = builder.build(request.workflow)

    async def generate():
        async for event in graph.astream(request.input, stream_mode="updates"):
            yield {"event": "update", "data": json.dumps(event, default=str)}
        yield {"event": "done", "data": ""}

    return EventSourceResponse(generate())


@router.websocket("/ws")
async def workflow_websocket(
    websocket: WebSocket,
    session_manager: SessionManager = Depends(get_session_manager),
) -> None:
    """WebSocket endpoint for bidirectional workflow interaction."""
    handler = WorkflowWebSocketHandler(session_manager)
    await handler.handle(websocket)
