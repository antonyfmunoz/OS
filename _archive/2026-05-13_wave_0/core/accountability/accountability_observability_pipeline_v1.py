"""Accountability Observability Pipeline v1.

8 event types for accountability observability.
JSONL persistence per event type.

UMH substrate subsystem. Phase 96.8CL.
"""

from __future__ import annotations

import json
import os
from typing import Any

from core.accountability.sovereign_operational_accountability_contracts_v1 import (
    AccountabilityEventType,
    _now_iso,
)

EVENT_FILE_MAP: dict[str, str] = {e.value: f"{e.value}.jsonl" for e in AccountabilityEventType}


class AccountabilityObservabilityPipeline:
    def __init__(self, output_dir: str = "") -> None:
        self._output_dir = output_dir
        self._events: list[dict[str, Any]] = []

    def _persist(self, event: dict[str, Any]) -> None:
        if not self._output_dir:
            return
        event_type = event.get("event_type", "unknown")
        filename = EVENT_FILE_MAP.get(event_type, "unknown.jsonl")
        path = os.path.join(self._output_dir, filename)
        os.makedirs(self._output_dir, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(event) + "\n")

    def _emit(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        event = {"event_type": event_type, "timestamp": _now_iso(), "payload": payload or {}}
        self._events.append(event)
        self._persist(event)
        return event

    def emit_accountability_started(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._emit(AccountabilityEventType.ACCOUNTABILITY_STARTED, payload)

    def emit_chronology_reconstructed(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._emit(AccountabilityEventType.CHRONOLOGY_RECONSTRUCTED, payload)

    def emit_governance_history_reconstructed(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._emit(AccountabilityEventType.GOVERNANCE_HISTORY_RECONSTRUCTED, payload)

    def emit_replay_history_reconstructed(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._emit(AccountabilityEventType.REPLAY_HISTORY_RECONSTRUCTED, payload)

    def emit_continuity_history_reconstructed(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._emit(AccountabilityEventType.CONTINUITY_HISTORY_RECONSTRUCTED, payload)

    def emit_provenance_history_generated(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._emit(AccountabilityEventType.PROVENANCE_HISTORY_GENERATED, payload)

    def emit_constitutional_audit_generated(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._emit(AccountabilityEventType.CONSTITUTIONAL_AUDIT_GENERATED, payload)

    def emit_accountability_completed(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._emit(AccountabilityEventType.ACCOUNTABILITY_COMPLETED, payload)

    def get_events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def get_events_by_type(self, event_type: str) -> list[dict[str, Any]]:
        return [e for e in self._events if e["event_type"] == event_type]

    def get_stats(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        for e in self._events:
            t = e["event_type"]
            by_type[t] = by_type.get(t, 0) + 1
        return {"total_events": len(self._events), "by_type": by_type, "all_persisted": True}
