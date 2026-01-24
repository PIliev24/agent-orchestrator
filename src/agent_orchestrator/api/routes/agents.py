"""Agent execution endpoints."""

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from agent_orchestrator.agents.executor import AgentExecutor
from agent_orchestrator.api.dependencies import get_session_manager, verify_api_key
from agent_orchestrator.core.schemas.agent import AgentExecutionRequest, AgentExecutionResponse
from agent_orchestrator.sessions.manager import SessionManager

router = APIRouter()


@router.post("/execute", response_model=AgentExecutionResponse)
async def execute_agent(
    request: AgentExecutionRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    _: str = Depends(verify_api_key),
) -> AgentExecutionResponse:
    """Execute an agent with the given configuration."""
    executor = AgentExecutor(session_manager)
    result = await executor.execute(
        agent_config=request.agent,
        user_input=request.input,
        session_id=request.session_id,
    )

    return AgentExecutionResponse(
        agent_name=request.agent.name,
        output=result.output,
        session_id=result.session_id,
        metadata=result.metadata,
    )


@router.post("/execute/stream")
async def execute_agent_stream(
    request: AgentExecutionRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    _: str = Depends(verify_api_key),
) -> EventSourceResponse:
    """Execute an agent with SSE streaming response."""
    executor = AgentExecutor(session_manager)

    async def generate():
        async for chunk in executor.execute_stream(
            agent_config=request.agent,
            user_input=request.input,
            session_id=request.session_id,
        ):
            yield {"event": "token", "data": chunk}
        yield {"event": "done", "data": ""}

    return EventSourceResponse(generate())
