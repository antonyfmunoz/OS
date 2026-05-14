"""Intelligence Observability Pipeline v1.

Emits structured intelligence events to JSONL files.
10 event types from IntelligenceEventType enum.

UMH substrate subsystem. Phase 96.8CA.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.intelligence.operational_intelligence_contracts_v1 import (
    IntelligenceEventType,
    _new_id,
    _now_iso,
)


EVENT_FILE_MAP: dict[str, str] = {
    et.value: f"intelligence_{et.value}.jsonl"
    for et in IntelligenceEventType
}


class IntelligenceObservabilityPipeline:
    """Emits structured intelligence observability events."""

    def __init__(
        self, state_dir: str | Path = "data/runtime/intelligence/observability",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._total_events: int = 0
        self._event_counts: dict[str, int] = {
            et.value: 0 for et in IntelligenceEventType
        }

    def _emit(self, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        record = {
            "event_id": _new_id("ievt"),
            "event_type": event_type,
            "data": data,
            "timestamp": _now_iso(),
        }

        filename = EVENT_FILE_MAP.get(event_type, f"intelligence_{event_type}.jsonl")
        path = self._state_dir / filename
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

        self._total_events += 1
        if event_type in self._event_counts:
            self._event_counts[event_type] += 1

        return record

    def emit_intelligence_synthesized(
        self, sources: list[str] | None = None, signal_count: int = 0, **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("intelligence_synthesized", {
            "sources": sources or [], "signal_count": signal_count, **kw,
        })

    def emit_relevance_scored(
        self, signal_id: str = "", score: float = 0.0, **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("relevance_scored", {
            "signal_id": signal_id, "score": score, **kw,
        })

    def emit_context_compressed(
        self, original: int = 0, compressed: int = 0, **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("context_compressed", {
            "original": original, "compressed": compressed, **kw,
        })

    def emit_operational_awareness_updated(
        self, subsystems: int = 0, pressures: int = 0, **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("operational_awareness_updated", {
            "subsystems": subsystems, "pressures": pressures, **kw,
        })

    def emit_intent_anchor_validated(
        self, intent: str = "", valid: bool = True, **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("intent_anchor_validated", {
            "intent": intent, "valid": valid, **kw,
        })

    def emit_intelligence_route_created(
        self, source: str = "", target: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("intelligence_route_created", {
            "source": source, "target": target, **kw,
        })

    def emit_reasoning_composed(
        self, reasoning_type: str = "", confidence: float = 0.0, **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("reasoning_composed", {
            "reasoning_type": reasoning_type, "confidence": confidence, **kw,
        })

    def emit_intelligence_boundary_denied(
        self, action: str = "", reason: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("intelligence_boundary_denied", {
            "action": action, "reason": reason, **kw,
        })

    def emit_cognition_window_regulated(
        self, window_size: int = 0, max_size: int = 0, **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("cognition_window_regulated", {
            "window_size": window_size, "max_size": max_size, **kw,
        })

    def emit_operational_projection_updated(
        self, risks: int = 0, pressures: int = 0, **kw: Any,
    ) -> dict[str, Any]:
        return self._emit("operational_projection_updated", {
            "risks": risks, "pressures": pressures, **kw,
        })

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_events": self._total_events,
            "event_counts": dict(self._event_counts),
        }
