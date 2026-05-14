"""Stabilization Observability Pipeline v1.

7 event types for operational fabric stabilization observability.
JSONL persistence per event type.

UMH substrate subsystem. Phase 96.8CH.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.stabilization.constitutional_operational_fabric_contracts_v1 import (
    StabilizationEventType,
    _now_iso,
)


EVENT_FILE_MAP: dict[str, str] = {
    e.value: f"{e.value}.jsonl" for e in StabilizationEventType
}


class StabilizationObservabilityPipeline:
    """Emits and persists stabilization observability events."""

    def __init__(self, state_dir: str | Path = "data/runtime/stabilization_observability") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._events: list[dict[str, Any]] = []

    def _emit(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        event = {
            "event_type": event_type,
            "timestamp": _now_iso(),
            **payload,
        }
        self._events.append(event)

        filename = EVENT_FILE_MAP.get(event_type, "unknown.jsonl")
        filepath = self._state_dir / filename
        with open(filepath, "a") as f:
            f.write(json.dumps(event) + "\n")

        return event

    def emit_stabilization_run_started(
        self, run_id: str = "",
    ) -> dict[str, Any]:
        return self._emit(
            StabilizationEventType.STABILIZATION_RUN_STARTED,
            {"run_id": run_id},
        )

    def emit_stabilization_run_completed(
        self, run_id: str = "", outcome: str = "stable",
    ) -> dict[str, Any]:
        return self._emit(
            StabilizationEventType.STABILIZATION_RUN_COMPLETED,
            {"run_id": run_id, "outcome": outcome},
        )

    def emit_concurrency_validated(
        self, concurrent_operations: int = 0,
    ) -> dict[str, Any]:
        return self._emit(
            StabilizationEventType.CONCURRENCY_VALIDATED,
            {"concurrent_operations": concurrent_operations},
        )

    def emit_replay_durability_validated(
        self, layers_validated: int = 0,
    ) -> dict[str, Any]:
        return self._emit(
            StabilizationEventType.REPLAY_DURABILITY_VALIDATED,
            {"layers_validated": layers_validated},
        )

    def emit_continuity_durability_validated(
        self, layers_validated: int = 0,
    ) -> dict[str, Any]:
        return self._emit(
            StabilizationEventType.CONTINUITY_DURABILITY_VALIDATED,
            {"layers_validated": layers_validated},
        )

    def emit_topology_durability_validated(
        self, domains_validated: int = 0,
    ) -> dict[str, Any]:
        return self._emit(
            StabilizationEventType.TOPOLOGY_DURABILITY_VALIDATED,
            {"domains_validated": domains_validated},
        )

    def emit_stabilization_boundary_denied(
        self, limit_name: str = "", current_value: int = 0, max_value: int = 0,
    ) -> dict[str, Any]:
        return self._emit(
            StabilizationEventType.STABILIZATION_BOUNDARY_DENIED,
            {
                "limit_name": limit_name,
                "current_value": current_value,
                "max_value": max_value,
            },
        )

    def get_events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_events": len(self._events),
            "event_types": len(EVENT_FILE_MAP),
        }
