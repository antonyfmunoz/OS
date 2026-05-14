"""Deployment Observability Pipeline v1.

9 event types for deployment observability.
Dynamic EVENT_FILE_MAP from DeploymentEventType enum.
JSONL persistence per event type.

UMH substrate subsystem. Phase 96.8CE.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.deployment.platform_deployment_contracts_v1 import (
    DeploymentEventType,
    _now_iso,
)

EVENT_FILE_MAP: dict[str, str] = {
    e.value: f"{e.value}.jsonl" for e in DeploymentEventType
}


class DeploymentObservabilityPipeline:
    """Emits and persists deployment observability events."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/deployments/observability",
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

    def emit_deployment_created(
        self, deployment_id: str, app_id: str,
    ) -> dict[str, Any]:
        return self._emit("deployment_created", {
            "deployment_id": deployment_id, "app_id": app_id,
        })

    def emit_deployment_validated(
        self, deployment_id: str,
    ) -> dict[str, Any]:
        return self._emit("deployment_validated", {
            "deployment_id": deployment_id,
        })

    def emit_deployment_denied(
        self, deployment_id: str, reason: str,
    ) -> dict[str, Any]:
        return self._emit("deployment_denied", {
            "deployment_id": deployment_id, "reason": reason,
        })

    def emit_rollout_started(
        self, rollout_id: str, deployment_id: str,
    ) -> dict[str, Any]:
        return self._emit("rollout_started", {
            "rollout_id": rollout_id, "deployment_id": deployment_id,
        })

    def emit_rollout_completed(
        self, rollout_id: str, deployment_id: str,
    ) -> dict[str, Any]:
        return self._emit("rollout_completed", {
            "rollout_id": rollout_id, "deployment_id": deployment_id,
        })

    def emit_rollback_started(
        self, rollback_id: str, deployment_id: str,
    ) -> dict[str, Any]:
        return self._emit("rollback_started", {
            "rollback_id": rollback_id, "deployment_id": deployment_id,
        })

    def emit_rollback_completed(
        self, rollback_id: str, deployment_id: str,
    ) -> dict[str, Any]:
        return self._emit("rollback_completed", {
            "rollback_id": rollback_id, "deployment_id": deployment_id,
        })

    def emit_topology_validated(
        self, topology_id: str,
    ) -> dict[str, Any]:
        return self._emit("topology_validated", {
            "topology_id": topology_id,
        })

    def emit_deployment_replay_validated(
        self, deployment_id: str, check_name: str, deterministic: bool,
    ) -> dict[str, Any]:
        return self._emit("deployment_replay_validated", {
            "deployment_id": deployment_id,
            "check_name": check_name,
            "deterministic": deterministic,
        })

    def get_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._events[-limit:]

    def get_stats(self) -> dict[str, object]:
        return {
            "total_events": len(self._events),
            "event_types": len(EVENT_FILE_MAP),
        }
