"""WebSocket endpoint for broadcasting ViewFrames to cockpit clients.

Provides:
  - ConnectionManager: tracks connected WebSocket clients, broadcasts dicts
  - ws_endpoint: FastAPI WebSocket route handler at /ws
  - broadcast_frame: async function passed to ViewFrameBroadcaster as callback

Wire into FastAPI app:
    app.add_api_websocket_route("/ws", ws_endpoint)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts to all."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def accept(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        logger.info("ws client connected (%d total)", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)
        logger.info("ws client disconnected (%d remaining)", len(self._connections))

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send a JSON message to all connected clients.

        Formats as {type: event_type, data: frame_dict} to match
        the CockpitSocket's expected message shape.
        """
        payload = json.dumps(message)
        stale: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


async def broadcast_frame(frame_dict: dict[str, Any]) -> None:
    """Async callback for ViewFrameBroadcaster.

    Wraps the serialized ViewFrame in the {type, data} envelope
    that CockpitSocket expects.
    """
    message = {
        "type": frame_dict.get("event_type", "frame"),
        "data": frame_dict,
    }
    await manager.broadcast(message)


async def ws_endpoint(websocket: WebSocket) -> None:
    """FastAPI WebSocket handler at /ws.

    Accepts connections, keeps them alive by reading (handles pings),
    and cleans up on disconnect.
    """
    await manager.accept(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except (json.JSONDecodeError, TypeError):
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
