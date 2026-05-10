"""Feedback loop — outcome capture and learning signal emission.

After every execution, the feedback loop:
  1. Records the outcome (success/failure/partial)
  2. Updates capability performance stats
  3. Updates world model with observations
  4. Emits a learning event for strategy adaptation

No LLM calls. No domain-specific logic.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from umh.capability.registry import get_registry


class OutcomeType:
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    REJECTED = "rejected"


@dataclass(frozen=True)
class FeedbackEvent:
    """Immutable record of an execution outcome and its learning signal."""

    event_id: str
    timestamp: str
    operation: str
    outcome: str
    capability_used: str
    latency_ms: int
    confidence: float
    learning_signal: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "operation": self.operation,
            "outcome": self.outcome,
            "capability_used": self.capability_used,
            "latency_ms": self.latency_ms,
            "confidence": round(self.confidence, 4),
            "learning_signal": self.learning_signal,
        }


_feedback_log: list[FeedbackEvent] = []
_MAX_LOG_SIZE = 200


def record_outcome(
    operation: str,
    outcome: str,
    capability_name: str,
    latency_ms: int = 0,
    outputs: dict[str, Any] | None = None,
    error: str | None = None,
) -> FeedbackEvent:
    """Record an execution outcome and emit a feedback event.

    Updates the capability's performance stats and appends to the
    in-memory feedback log.
    """
    success = outcome == OutcomeType.SUCCESS

    registry = get_registry()
    cap = registry.get(capability_name)
    if cap is not None:
        cap.performance.record(success=success, latency_ms=latency_ms)

    learning_signal: dict[str, Any] = {
        "outcome": outcome,
        "success": success,
        "capability": capability_name,
    }
    if error:
        learning_signal["error"] = error[:200]

    event = FeedbackEvent(
        event_id=f"fb_{uuid.uuid4().hex[:12]}",
        timestamp=datetime.now(timezone.utc).isoformat(),
        operation=operation,
        outcome=outcome,
        capability_used=capability_name,
        latency_ms=latency_ms,
        confidence=0.8 if success else 0.3,
        learning_signal=learning_signal,
        metadata={"outputs_keys": list((outputs or {}).keys())},
    )

    _feedback_log.append(event)
    if len(_feedback_log) > _MAX_LOG_SIZE:
        _feedback_log.pop(0)

    return event


def get_recent_feedback(n: int = 10) -> list[FeedbackEvent]:
    """Return the n most recent feedback events."""
    return list(_feedback_log[-n:])


def clear_feedback_log() -> None:
    """Clear the feedback log (for testing)."""
    _feedback_log.clear()
