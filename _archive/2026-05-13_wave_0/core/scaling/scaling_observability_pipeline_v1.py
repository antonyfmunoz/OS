"""Scaling Observability Pipeline v1.

Emits and persists scaling coordination events:
  pressure_increase, pressure_relief, queue_throttle,
  execution_delayed, degraded_mode_entered, degraded_mode_recovered,
  concurrency_limited, resource_budget_exceeded,
  priority_arbitrated, scaling_boundary_denied.

UMH substrate subsystem. Phase 96.8BY.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.scaling.operational_scaling_contracts_v1 import (
    ScalingEventType,
    _new_id,
    _now_iso,
)


EVENT_FILE_MAP: dict[str, str] = {
    et.value: f"{et.value}.jsonl" for et in ScalingEventType
}


class ScalingObservabilityPipeline:
    """Observability for scaling coordination."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/scaling/observability",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._events: list[dict[str, Any]] = []
        self._total_events: int = 0

    def emit(
        self,
        event_type: ScalingEventType,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": _new_id("sobs"),
            "event_type": event_type.value,
            "data": data or {},
            "timestamp": _now_iso(),
        }
        self._events.append(event)
        self._total_events += 1

        filename = EVENT_FILE_MAP.get(event_type.value, "unknown_events.jsonl")
        path = self._state_dir / filename
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")

        return event

    def emit_pressure_increase(self, **kw: Any) -> dict[str, Any]:
        return self.emit(ScalingEventType.PRESSURE_INCREASE, kw)

    def emit_pressure_relief(self, **kw: Any) -> dict[str, Any]:
        return self.emit(ScalingEventType.PRESSURE_RELIEF, kw)

    def emit_queue_throttle(self, **kw: Any) -> dict[str, Any]:
        return self.emit(ScalingEventType.QUEUE_THROTTLE, kw)

    def emit_execution_delayed(self, **kw: Any) -> dict[str, Any]:
        return self.emit(ScalingEventType.EXECUTION_DELAYED, kw)

    def emit_degraded_mode_entered(self, **kw: Any) -> dict[str, Any]:
        return self.emit(ScalingEventType.DEGRADED_MODE_ENTERED, kw)

    def emit_degraded_mode_recovered(self, **kw: Any) -> dict[str, Any]:
        return self.emit(ScalingEventType.DEGRADED_MODE_RECOVERED, kw)

    def emit_concurrency_limited(self, **kw: Any) -> dict[str, Any]:
        return self.emit(ScalingEventType.CONCURRENCY_LIMITED, kw)

    def emit_resource_budget_exceeded(self, **kw: Any) -> dict[str, Any]:
        return self.emit(ScalingEventType.RESOURCE_BUDGET_EXCEEDED, kw)

    def emit_priority_arbitrated(self, **kw: Any) -> dict[str, Any]:
        return self.emit(ScalingEventType.PRIORITY_ARBITRATED, kw)

    def emit_scaling_boundary_denied(self, **kw: Any) -> dict[str, Any]:
        return self.emit(ScalingEventType.SCALING_BOUNDARY_DENIED, kw)

    def get_events(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._events[-limit:]

    def read_events(self, event_type: ScalingEventType) -> list[dict[str, Any]]:
        filename = EVENT_FILE_MAP.get(event_type.value, "")
        if not filename:
            return []
        path = self._state_dir / filename
        if not path.exists():
            return []
        events = []
        for line in path.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                events.append(json.loads(line))
        return events

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_events": self._total_events,
            "event_types": len(EVENT_FILE_MAP),
        }
