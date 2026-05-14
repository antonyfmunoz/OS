"""Learning Observability Pipeline v1.

Emits structured events for all learning operations.
7 event types from LearningEventType enum.
JSONL per event type, dynamic EVENT_FILE_MAP.

UMH substrate subsystem. Phase 96.8CC.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.learning.adaptive_learning_contracts_v1 import (
    LearningEventType,
    _now_iso,
)

EVENT_FILE_MAP: dict[str, str] = {
    evt.value: f"{evt.value}.jsonl" for evt in LearningEventType
}


class LearningObservabilityPipeline:
    """Emits learning observability events."""

    def __init__(self, state_dir: str | Path = "data/runtime/learning/observability") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._counts: dict[str, int] = {evt.value: 0 for evt in LearningEventType}

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        event = {
            "event_type": event_type,
            "timestamp": _now_iso(),
            **payload,
        }
        filename = EVENT_FILE_MAP.get(event_type, "unknown.jsonl")
        path = self._state_dir / filename
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")
        self._counts[event_type] = self._counts.get(event_type, 0) + 1

    def emit_learning_signal_observed(
        self, signal_id: str, source: str,
    ) -> None:
        self._emit("learning_signal_observed", {
            "signal_id": signal_id, "source": source,
        })

    def emit_pattern_candidate_detected(
        self, pattern_id: str, pattern_type: str, confidence: float,
    ) -> None:
        self._emit("pattern_candidate_detected", {
            "pattern_id": pattern_id, "pattern_type": pattern_type,
            "confidence": confidence,
        })

    def emit_proposal_generated(
        self, proposal_id: str, proposal_type: str,
    ) -> None:
        self._emit("proposal_generated", {
            "proposal_id": proposal_id, "proposal_type": proposal_type,
        })

    def emit_proposal_denied(
        self, proposal_id: str, reason: str = "",
    ) -> None:
        self._emit("proposal_denied", {
            "proposal_id": proposal_id, "reason": reason,
        })

    def emit_proposal_approved(
        self, proposal_id: str, approved_by: str = "operator",
    ) -> None:
        self._emit("proposal_approved", {
            "proposal_id": proposal_id, "approved_by": approved_by,
        })

    def emit_learning_boundary_denied(
        self, action: str, reason: str,
    ) -> None:
        self._emit("learning_boundary_denied", {
            "action": action, "reason": reason,
        })

    def emit_learning_replay_validated(
        self, check_name: str, deterministic: bool,
    ) -> None:
        self._emit("learning_replay_validated", {
            "check_name": check_name, "deterministic": deterministic,
        })

    def get_stats(self) -> dict[str, Any]:
        return {
            "event_counts": dict(self._counts),
            "total_events": sum(self._counts.values()),
        }
