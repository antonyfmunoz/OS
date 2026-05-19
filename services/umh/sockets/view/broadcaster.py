"""Broadcaster — sync→async bridge for ViewFrame delivery.

The ExecutionPipeline runs synchronously on a background thread.
The WebSocket connection manager is async on the FastAPI event loop.
This module bridges the two using asyncio.run_coroutine_threadsafe().

Usage during app startup:
    broadcaster = ViewFrameBroadcaster(loop=asyncio.get_running_loop())
    view_socket.subscribe(broadcaster)
    pipeline.on_event(make_pipeline_listener(view_socket))
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from services.umh.sockets.envelopes import ViewFrame

logger = logging.getLogger(__name__)

FrameCallback = Callable[[dict[str, Any]], Any]


class ViewFrameBroadcaster:
    """ViewSubscriber that bridges sync on_frame() calls to an async callback.

    Satisfies the ViewSubscriber protocol structurally:
      - subscriber_id: str (property)
      - on_frame(ViewFrame) -> None
      - accepts_events() -> list[str]
    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        async_callback: FrameCallback | None = None,
    ) -> None:
        self._loop = loop
        self._async_callback = async_callback
        self._frame_count = 0

    @property
    def subscriber_id(self) -> str:
        return "ws_broadcaster"

    def accepts_events(self) -> list[str]:
        return []

    def set_callback(self, callback: FrameCallback) -> None:
        self._async_callback = callback

    def on_frame(self, frame: ViewFrame) -> None:
        """Called synchronously from the pipeline thread.

        Serializes the ViewFrame and submits broadcast to the event loop.
        Fire-and-forget — pipeline never blocks on WebSocket delivery.
        """
        if self._async_callback is None:
            return

        serialized = _serialize_frame(frame)
        self._frame_count += 1

        try:
            asyncio.run_coroutine_threadsafe(
                self._async_callback(serialized),
                self._loop,
            )
        except RuntimeError:
            logger.debug("event loop closed, dropping frame %s", frame.frame_id)

    @property
    def frame_count(self) -> int:
        return self._frame_count


def _serialize_frame(frame: ViewFrame) -> dict[str, Any]:
    """Convert a frozen ViewFrame dataclass to a JSON-safe dict."""
    data = asdict(frame)
    for key, val in data.items():
        if isinstance(val, datetime):
            data[key] = val.isoformat()
        elif hasattr(val, "hex"):
            data[key] = str(val)
    return data


STAGE_NAMES: dict[int, str] = {
    1: "signal",
    2: "governance",
    3: "work_packet",
    4: "execution",
    5: "proof",
    6: "outcome",
    7: "trace",
    8: "memory_candidate",
    9: "memory_promotion",
    10: "resume_state",
}

STAGE_FROM_EVENT: dict[str, int] = {v: k for k, v in STAGE_NAMES.items()}


def make_pipeline_listener(
    view_socket: Any,
) -> Callable[[str, dict[str, Any]], None]:
    """Create a pipeline on_event() listener that emits ViewFrames.

    The returned function has the signature (event_type: str, data: dict) -> None,
    matching ExecutionPipeline.EventListener.
    """

    def _listener(event_type: str, data: dict[str, Any]) -> None:
        stage = STAGE_FROM_EVENT.get(event_type, 0)
        frame = ViewFrame(
            frame_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            stage=stage,
            data=data,
            trace_id=_extract_uuid(data, "trace_id"),
            signal_id=_extract_uuid(data, "signal_id"),
        )
        view_socket.broadcast(frame)

    return _listener


def _extract_uuid(data: dict[str, Any], key: str) -> Any:
    """Pull a UUID-like value from event data, return None if absent."""
    val = data.get(key)
    if val is None:
        return None
    from uuid import UUID

    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except (ValueError, AttributeError):
        return None
