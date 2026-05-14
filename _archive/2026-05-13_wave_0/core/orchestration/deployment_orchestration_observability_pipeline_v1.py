"""Deployment Orchestration Observability Pipeline v1.

8 event types for live operational deployment orchestration.
Dynamic EVENT_FILE_MAP from enum. JSONL persistence.

UMH substrate subsystem. Phase 96.8CF.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.orchestration.live_operational_deployment_contracts_v1 import (
    OrchestrationEventType,
    _now_iso,
)

EVENT_FILE_MAP: dict[str, str] = {
    e.value: f"{e.value}.jsonl" for e in OrchestrationEventType
}


class DeploymentOrchestrationObservabilityPipeline:
    """Emits and persists deployment orchestration events."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/orchestration/observability",
    ) -> None:
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
        path = self._state_dir / filename
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")

        return event

    def emit_operation_started(
        self, operation_id: str, **kwargs: Any,
    ) -> dict[str, Any]:
        return self._emit(
            OrchestrationEventType.DEPLOYMENT_OPERATION_STARTED.value,
            {"operation_id": operation_id, **kwargs},
        )

    def emit_operation_completed(
        self, operation_id: str, **kwargs: Any,
    ) -> dict[str, Any]:
        return self._emit(
            OrchestrationEventType.DEPLOYMENT_OPERATION_COMPLETED.value,
            {"operation_id": operation_id, **kwargs},
        )

    def emit_checkpoint_created(
        self, operation_id: str, checkpoint_id: str, **kwargs: Any,
    ) -> dict[str, Any]:
        return self._emit(
            OrchestrationEventType.DEPLOYMENT_CHECKPOINT_CREATED.value,
            {"operation_id": operation_id, "checkpoint_id": checkpoint_id, **kwargs},
        )

    def emit_restore_started(
        self, operation_id: str, **kwargs: Any,
    ) -> dict[str, Any]:
        return self._emit(
            OrchestrationEventType.DEPLOYMENT_RESTORE_STARTED.value,
            {"operation_id": operation_id, **kwargs},
        )

    def emit_restore_completed(
        self, operation_id: str, **kwargs: Any,
    ) -> dict[str, Any]:
        return self._emit(
            OrchestrationEventType.DEPLOYMENT_RESTORE_COMPLETED.value,
            {"operation_id": operation_id, **kwargs},
        )

    def emit_recovery_recommended(
        self, operation_id: str, action: str, **kwargs: Any,
    ) -> dict[str, Any]:
        return self._emit(
            OrchestrationEventType.DEPLOYMENT_RECOVERY_RECOMMENDED.value,
            {"operation_id": operation_id, "action": action, **kwargs},
        )

    def emit_boundary_denied(
        self, operation_id: str, reason: str, **kwargs: Any,
    ) -> dict[str, Any]:
        return self._emit(
            OrchestrationEventType.DEPLOYMENT_BOUNDARY_DENIED.value,
            {"operation_id": operation_id, "reason": reason, **kwargs},
        )

    def emit_replay_validated(
        self, operation_id: str, **kwargs: Any,
    ) -> dict[str, Any]:
        return self._emit(
            OrchestrationEventType.DEPLOYMENT_REPLAY_VALIDATED.value,
            {"operation_id": operation_id, **kwargs},
        )

    def get_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._events[-limit:]

    def get_stats(self) -> dict[str, object]:
        return {
            "total_events": len(self._events),
        }
