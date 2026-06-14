"""Phase 15B: Execution Telemetry route handlers.

Provides live and historical telemetry for executor lifecycle events.
Includes SSE streaming for real-time observation.

Routes:
  GET /executor/telemetry/latest — recent telemetry events
  GET /executor/telemetry/{execution_id} — events for one execution
  GET /executor/telemetry/{execution_id}/stream — SSE live stream
"""

from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import Request
from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)


def _get_emitter():
    from substrate.organism.executors.execution_telemetry import (
        get_telemetry_emitter,
    )
    return get_telemetry_emitter()


# ── GET handlers ────────────────────────────────────────────────


async def telemetry_latest(request: Request) -> dict:
    """GET /executor/telemetry/latest — recent telemetry events."""
    try:
        emitter = _get_emitter()
        limit = int(request.query_params.get("limit", "50"))
        limit = min(limit, 500)
        events = emitter.get_latest(limit)
        return {
            "success": True,
            "events": [e.to_dict() for e in events],
            "count": len(events),
            "sequence": emitter.store.sequence,
        }
    except Exception as exc:
        logger.error("telemetry latest failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def telemetry_for_execution(request: Request) -> dict:
    """GET /executor/telemetry/{execution_id} — events for one execution."""
    try:
        execution_id = request.path_params.get("execution_id", "")
        after_seq = int(request.query_params.get("after_sequence", "0"))
        emitter = _get_emitter()

        if after_seq > 0:
            events = emitter.get_events_after(execution_id, after_seq)
        else:
            events = emitter.get_events(execution_id)

        return {
            "success": True,
            "execution_id": execution_id,
            "events": [e.to_dict() for e in events],
            "count": len(events),
            "sequence": emitter.store.sequence,
        }
    except Exception as exc:
        logger.error("telemetry for execution failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def telemetry_stream(request: Request) -> StreamingResponse:
    """GET /executor/telemetry/{execution_id}/stream — SSE live stream.

    Streams telemetry events as Server-Sent Events. The connection stays
    open until the execution reaches a terminal state or the client
    disconnects. Falls back to polling internally (100ms intervals).
    """
    execution_id = request.path_params.get("execution_id", "")
    emitter = _get_emitter()

    _TERMINAL_EVENTS = {
        "execution_completed",
        "execution_failed",
        "execution_cancelled",
    }

    async def event_generator():
        last_seq = 0
        idle_count = 0
        max_idle = 600  # 60 seconds at 100ms intervals

        yield "retry: 1000\n\n"

        while True:
            if await request.is_disconnected():
                break

            events = emitter.get_events_after(execution_id, last_seq)
            if events:
                idle_count = 0
                for event in events:
                    last_seq = event.sequence_number
                    yield event.to_sse()

                    if event.event_type in _TERMINAL_EVENTS:
                        yield f"event: done\ndata: {json.dumps({'execution_id': execution_id, 'final_event': event.event_type})}\n\n"
                        return
            else:
                idle_count += 1
                if idle_count >= max_idle:
                    yield f"event: timeout\ndata: {json.dumps({'execution_id': execution_id, 'reason': 'idle_timeout'})}\n\n"
                    return

                if idle_count % 50 == 0:
                    yield f": keepalive {time.time()}\n\n"

            await asyncio.sleep(0.1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
