"""Explainability Observability Pipeline v1.

8 event types for explainability observability.
JSONL persistence per event type.

UMH substrate subsystem. Phase 96.8CK.
"""

from __future__ import annotations

import json
import os
from typing import Any

from core.explainability.constitutional_explainability_contracts_v1 import (
    ExplainabilityEventType,
    _now_iso,
)

EVENT_FILE_MAP: dict[str, str] = {e.value: f"{e.value}.jsonl" for e in ExplainabilityEventType}


class ExplainabilityObservabilityPipeline:
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

    def emit_explanation_requested(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._emit(ExplainabilityEventType.EXPLANATION_REQUESTED, payload)

    def emit_lineage_reconstructed(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._emit(ExplainabilityEventType.LINEAGE_RECONSTRUCTED, payload)

    def emit_governance_reasoning_reconstructed(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._emit(ExplainabilityEventType.GOVERNANCE_REASONING_RECONSTRUCTED, payload)

    def emit_replay_explanation_generated(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._emit(ExplainabilityEventType.REPLAY_EXPLANATION_GENERATED, payload)

    def emit_continuity_explanation_generated(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._emit(ExplainabilityEventType.CONTINUITY_EXPLANATION_GENERATED, payload)

    def emit_provenance_graph_generated(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._emit(ExplainabilityEventType.PROVENANCE_GRAPH_GENERATED, payload)

    def emit_constitutional_reasoning_generated(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._emit(ExplainabilityEventType.CONSTITUTIONAL_REASONING_GENERATED, payload)

    def emit_explanation_completed(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._emit(ExplainabilityEventType.EXPLANATION_COMPLETED, payload)

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
