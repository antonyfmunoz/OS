"""Outcome protocols — contracts for feedback and learning signals."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from umh.signal.event_bus import EventLogger

__all__ = ["EventLogger", "OutcomeRecorder"]


@runtime_checkable
class OutcomeRecorder(Protocol):
    """Contract for recording execution outcomes for learning."""

    def record(
        self,
        operation: str,
        outcome: str,
        capability_name: str,
        latency_ms: int,
        outputs: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None: ...
