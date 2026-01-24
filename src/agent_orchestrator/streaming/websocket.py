"""WebSocket utilities for real-time communication."""

import logging
from typing import TYPE_CHECKING, Any

from fastapi import WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from agent_orchestrator.sessions.manager import SessionManager

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for broadcasting and direct messaging."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from active connections."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_json(self, websocket: WebSocket, data: dict) -> None:
        """Send JSON data to a specific WebSocket connection."""
        await websocket.send_json(data)

    async def broadcast(self, data: dict) -> None:
        """Broadcast JSON data to all active connections."""
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)


class WorkflowWebSocketHandler:
    """Handles WebSocket connections for workflow execution."""

    def __init__(self, session_manager: "SessionManager") -> None:
        self.session_manager = session_manager
        self.manager = WebSocketManager()

    async def handle(self, websocket: WebSocket) -> None:
        """Handle a WebSocket connection for workflow execution."""
        await self.manager.connect(websocket)

        try:
            while True:
                data = await websocket.receive_json()
                await self._process_request(websocket, data)

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            try:
                await self.manager.send_json(websocket, {"type": "error", "error": str(e)})
            except Exception:
                pass
        finally:
            self.manager.disconnect(websocket)

    async def _process_request(
        self,
        websocket: WebSocket,
        data: dict[str, Any],
    ) -> None:
        """Process a workflow execution request."""
        request_type = data.get("type", "execute")
        session_id = data.get("session_id")
        workflow_input = data.get("input", {})

        await self.manager.send_json(
            websocket,
            {"type": "ack", "session_id": session_id, "message": "Request received"},
        )

        try:
            if request_type == "execute":
                await self._execute_workflow(websocket, session_id, workflow_input, data)
            elif request_type == "cancel":
                await self._cancel_workflow(websocket, session_id)
            else:
                await self.manager.send_json(
                    websocket,
                    {"type": "error", "error": f"Unknown request type: {request_type}"},
                )
        except Exception as e:
            logger.error(f"Error processing workflow request: {e}")
            await self.manager.send_json(
                websocket,
                {"type": "error", "session_id": session_id, "error": str(e)},
            )

    async def _execute_workflow(
        self,
        websocket: WebSocket,
        session_id: str | None,
        workflow_input: dict[str, Any],
        data: dict[str, Any],
    ) -> None:
        """Execute a workflow and stream updates."""
        await self.manager.send_json(
            websocket,
            {"type": "status", "session_id": session_id, "status": "running"},
        )

        # Workflow execution would happen here
        # For now, send completion
        await self.manager.send_json(
            websocket,
            {"type": "complete", "session_id": session_id, "result": workflow_input},
        )

    async def _cancel_workflow(
        self,
        websocket: WebSocket,
        session_id: str | None,
    ) -> None:
        """Cancel a running workflow."""
        await self.manager.send_json(
            websocket,
            {"type": "cancelled", "session_id": session_id, "message": "Workflow cancelled"},
        )
