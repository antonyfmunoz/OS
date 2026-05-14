"""Application Observability Pipeline v1.

8 event types for application projection observability.
Dynamic EVENT_FILE_MAP from ApplicationEventType enum.
JSONL persistence per event type.

UMH substrate subsystem. Phase 96.8CD.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.applications.application_projection_contracts_v1 import (
    ApplicationEventType,
    _now_iso,
)

EVENT_FILE_MAP: dict[str, str] = {
    e.value: f"{e.value}.jsonl" for e in ApplicationEventType
}


class ApplicationObservabilityPipeline:
    """Emits and persists application observability events."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/applications/observability",
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

    def emit_application_registered(
        self,
        app_id: str,
        trust_tier: str,
    ) -> dict[str, Any]:
        return self._emit("application_registered", {
            "app_id": app_id,
            "trust_tier": trust_tier,
        })

    def emit_capability_bound(
        self,
        app_id: str,
        capability: str,
    ) -> dict[str, Any]:
        return self._emit("capability_bound", {
            "app_id": app_id,
            "capability": capability,
        })

    def emit_projection_created(
        self,
        app_id: str,
        projection_id: str,
    ) -> dict[str, Any]:
        return self._emit("projection_created", {
            "app_id": app_id,
            "projection_id": projection_id,
        })

    def emit_projection_denied(
        self,
        app_id: str,
        reason: str,
    ) -> dict[str, Any]:
        return self._emit("projection_denied", {
            "app_id": app_id,
            "reason": reason,
        })

    def emit_application_context_started(
        self,
        app_id: str,
        domain_context: str,
    ) -> dict[str, Any]:
        return self._emit("application_context_started", {
            "app_id": app_id,
            "domain_context": domain_context,
        })

    def emit_application_context_restored(
        self,
        app_id: str,
        context_id: str,
    ) -> dict[str, Any]:
        return self._emit("application_context_restored", {
            "app_id": app_id,
            "context_id": context_id,
        })

    def emit_application_boundary_denied(
        self,
        app_id: str,
        action: str,
        reason: str,
    ) -> dict[str, Any]:
        return self._emit("application_boundary_denied", {
            "app_id": app_id,
            "action": action,
            "reason": reason,
        })

    def emit_application_replay_validated(
        self,
        app_id: str,
        check_name: str,
        deterministic: bool,
    ) -> dict[str, Any]:
        return self._emit("application_replay_validated", {
            "app_id": app_id,
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
