"""Action executor — handles mid-session commands within an active lifecycle.

Follows the same contract as ritual executors in ritual_execution_driver:
returns (mutations, events, result) tuple. Pure function, no side effects.

Actions are lightweight — no full ritual plan. They record the intent,
emit events, and produce an ActionExecutionResult for the caller to apply.

Public API:
    ActionRequest           — frozen request for a mid-session action
    ActionExecutionResult   — frozen execution summary
    execute_action          — produce mutations + events for an action
"""

from __future__ import annotations

import hashlib
import json
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from umh.substrate.event_scheduler import SchedulerEvent

_LOG_PREFIX = "[runtime.action_executor]"
_EVENT_SOURCE = "action_executor"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── State key helpers ────────────────────────────────────────────────────

_ACTION_EXECUTION_KEY_PREFIX = "action_execution."
_ACTION_COUNT_KEY = "action_count"


def _action_execution_key(action_id: str) -> str:
    return f"{_ACTION_EXECUTION_KEY_PREFIX}{action_id}"


# ── Request / Result dataclasses ─────────────────────────────────────────


@dataclass(frozen=True)
class ActionRequest:
    """Immutable request for a mid-session action.

    Attributes:
        request_id:          Unique request identifier.
        runtime_session_id:  Owning session.
        intent_text:         What the user wants to do.
        transport:           Origin channel.
        requested_at:        ISO-8601 UTC timestamp.
        correlation_id:      Links all events in this chain.
    """

    request_id: str
    runtime_session_id: str
    intent_text: str
    transport: str
    requested_at: str
    correlation_id: str


@dataclass(frozen=True)
class ActionExecutionResult:
    """Immutable summary of an action execution.

    Attributes:
        runtime_session_id: Owning session.
        action_id:          Unique ID for this action execution.
        intent_text:        The processed intent.
        transport:          Origin channel.
        correlation_id:     Links to upstream event chain.
    """

    runtime_session_id: str
    action_id: str
    intent_text: str
    transport: str
    correlation_id: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict — deterministic key order."""
        return {
            "action_id": self.action_id,
            "correlation_id": self.correlation_id,
            "intent_text": self.intent_text,
            "runtime_session_id": self.runtime_session_id,
            "transport": self.transport,
        }


# ── Event builders ───────────────────────────────────────────────────────


def _build_action_received_event(
    request: ActionRequest,
    session_name: str,
) -> SchedulerEvent:
    """Build event: action request received."""
    return SchedulerEvent(
        event_type="action_received",
        session_name=session_name,
        source=_EVENT_SOURCE,
        payload={
            "request_id": request.request_id,
            "intent_text": request.intent_text,
            "transport": request.transport,
        },
        metadata={
            "correlation_id": request.correlation_id,
        },
    )


def _build_action_completed_event(
    result: ActionExecutionResult,
    session_name: str,
) -> SchedulerEvent:
    """Build event: action execution completed."""
    return SchedulerEvent(
        event_type="action_completed",
        session_name=session_name,
        source=_EVENT_SOURCE,
        payload={"result": result.to_dict()},
        metadata={
            "action_id": result.action_id,
            "correlation_id": result.correlation_id,
        },
    )


# ── Executor ─────────────────────────────────────────────────────────────


def execute_action(
    state: dict[str, Any],
    request: ActionRequest,
    timestamp: str = "",
) -> tuple[list[dict[str, Any]], list[SchedulerEvent], ActionExecutionResult]:
    """Execute a mid-session action: emit mutations + events.

    Returns:
        (mutations, events, result)

    Follows the same contract as execute_open_day / execute_close_day.
    Pure function — reads state but never writes to it.
    """
    ts = timestamp or _utcnow()
    session_id = request.runtime_session_id
    correlation_id = request.correlation_id
    action_id = f"act_{uuid.uuid4().hex[:12]}"

    mutations: list[dict[str, Any]] = []
    events: list[SchedulerEvent] = []

    # Event 1: action received
    events.append(_build_action_received_event(request, session_id))

    # Mutation 1: increment action counter
    mutations.append(
        {
            "op": "INCREMENT",
            "key": _ACTION_COUNT_KEY,
            "value": 1,
        }
    )

    # Mutation 2: record this action execution
    mutations.append(
        {
            "op": "SET",
            "key": _action_execution_key(action_id),
            "value": {
                "action_id": action_id,
                "intent_text": request.intent_text,
                "transport": request.transport,
                "runtime_session_id": session_id,
                "correlation_id": correlation_id,
                "executed_at": ts,
            },
        }
    )

    # Build result
    result = ActionExecutionResult(
        runtime_session_id=session_id,
        action_id=action_id,
        intent_text=request.intent_text,
        transport=request.transport,
        correlation_id=correlation_id,
    )

    # Event 2: action completed
    events.append(_build_action_completed_event(result, session_id))

    return mutations, events, result
