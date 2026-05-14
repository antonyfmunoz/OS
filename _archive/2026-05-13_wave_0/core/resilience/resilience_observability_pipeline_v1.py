"""Resilience Observability Pipeline v1.

Emits structured resilience events to JSONL files.
10 event types from ResilienceEventType enum.

UMH substrate subsystem. Phase 96.8BZ.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.resilience.adaptive_resilience_contracts_v1 import (
    ResilienceEventType,
    _new_id,
    _now_iso,
)


EVENT_FILE_MAP: dict[str, str] = {
    et.value: f"resilience_{et.value}.jsonl"
    for et in ResilienceEventType
}


class ResilienceObservabilityPipeline:
    """Emits structured resilience observability events."""

    def __init__(
        self, state_dir: str | Path = "data/runtime/resilience/observability",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._total_events: int = 0
        self._event_counts: dict[str, int] = {
            et.value: 0 for et in ResilienceEventType
        }

    def _emit(self, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        record = {
            "event_id": _new_id("revt"),
            "event_type": event_type,
            "data": data,
            "timestamp": _now_iso(),
        }

        filename = EVENT_FILE_MAP.get(event_type, f"resilience_{event_type}.jsonl")
        path = self._state_dir / filename
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

        self._total_events += 1
        if event_type in self._event_counts:
            self._event_counts[event_type] += 1

        return record

    def emit_instability_detected(
        self, source: str = "", severity: float = 0.0, **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("instability_detected", {
            "source": source, "severity": severity, **kw,
        })

    def emit_fault_contained(
        self, source: str = "", boundary: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("fault_contained", {
            "source": source, "boundary": boundary, **kw,
        })

    def emit_cascade_interrupted(
        self, origin: str = "", depth: int = 0, **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("cascade_interrupted", {
            "origin": origin, "depth": depth, **kw,
        })

    def emit_checkpoint_created(
        self, subsystem: str = "", checkpoint_id: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("checkpoint_created", {
            "subsystem": subsystem, "checkpoint_id": checkpoint_id, **kw,
        })

    def emit_checkpoint_validated(
        self, subsystem: str = "", valid: bool = True, **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("checkpoint_validated", {
            "subsystem": subsystem, "valid": valid, **kw,
        })

    def emit_isolation_applied(
        self, target: str = "", scope: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("isolation_applied", {
            "target": target, "scope": scope, **kw,
        })

    def emit_recovery_recommended(
        self, target: str = "", action: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("recovery_recommended", {
            "target": target, "action": action, **kw,
        })

    def emit_recovery_validated(
        self, target: str = "", success: bool = True, **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("recovery_validated", {
            "target": target, "success": success, **kw,
        })

    def emit_survivability_assessed(
        self, score: float = 0.0, can_continue: bool = True, **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("survivability_assessed", {
            "score": score, "can_continue": can_continue, **kw,
        })

    def emit_resilience_restored(
        self, from_state: str = "", to_state: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("resilience_restored", {
            "from_state": from_state, "to_state": to_state, **kw,
        })

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_events": self._total_events,
            "event_counts": dict(self._event_counts),
        }
