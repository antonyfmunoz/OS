"""Cognition Observability Pipeline v1.

Records 10 event types for cognition observability:
  cognition_initialized, focus_shifted, loop_opened,
  loop_resolved, continuity_restored, cognition_checkpoint_created,
  attention_reweighted, temporal_snapshot_created,
  cognition_resumed, cognition_archived

Each event type persists to its own JSONL file.
All events are append-only and immutable.

UMH substrate subsystem. Phase 96.8BT.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.cognition.persistent_operator_cognition_contracts_v1 import (
    CognitionEventType,
    _new_id,
    _now_iso,
)


EVENT_FILE_MAP: dict[str, str] = {
    CognitionEventType.COGNITION_INITIALIZED.value: "cognition_init_events.jsonl",
    CognitionEventType.FOCUS_SHIFTED.value: "cognition_focus_events.jsonl",
    CognitionEventType.LOOP_OPENED.value: "cognition_loop_open_events.jsonl",
    CognitionEventType.LOOP_RESOLVED.value: "cognition_loop_resolve_events.jsonl",
    CognitionEventType.CONTINUITY_RESTORED.value: "cognition_continuity_events.jsonl",
    CognitionEventType.CHECKPOINT_CREATED.value: "cognition_checkpoint_events.jsonl",
    CognitionEventType.ATTENTION_REWEIGHTED.value: "cognition_attention_events.jsonl",
    CognitionEventType.TEMPORAL_SNAPSHOT_CREATED.value: "cognition_temporal_events.jsonl",
    CognitionEventType.COGNITION_RESUMED.value: "cognition_resume_events.jsonl",
    CognitionEventType.COGNITION_ARCHIVED.value: "cognition_archive_events.jsonl",
}


class CognitionObservabilityPipeline:
    """Records cognition events to JSONL files.

    10 event types, each with its own file.
    All events are immutable and append-only.
    """

    def __init__(
        self,
        obs_dir: str | Path = "data/runtime/cognition_observability",
    ) -> None:
        self._obs_dir = Path(obs_dir)
        self._obs_dir.mkdir(parents=True, exist_ok=True)
        self._event_counts: dict[str, int] = {
            et.value: 0 for et in CognitionEventType
        }
        self._total_events: int = 0

    def record_event(
        self,
        event_type: CognitionEventType,
        session_id: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record a cognition observability event."""
        event = {
            "event_id": _new_id("cogobs"),
            "event_type": event_type.value,
            "session_id": session_id,
            "data": data or {},
            "timestamp": _now_iso(),
        }

        filename = EVENT_FILE_MAP.get(event_type.value, "cognition_unknown_events.jsonl")
        path = self._obs_dir / filename
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")

        self._event_counts[event_type.value] += 1
        self._total_events += 1
        return event

    # ------------------------------------------------------------------
    # Convenience methods for each event type
    # ------------------------------------------------------------------

    def record_initialized(
        self, session_id: str, mode: str = "", **kwargs: Any
    ) -> dict[str, Any]:
        return self.record_event(
            CognitionEventType.COGNITION_INITIALIZED,
            session_id,
            {"mode": mode, **kwargs},
        )

    def record_focus_shifted(
        self, session_id: str, focus_id: str = "", focus_type: str = "", **kwargs: Any
    ) -> dict[str, Any]:
        return self.record_event(
            CognitionEventType.FOCUS_SHIFTED,
            session_id,
            {"focus_id": focus_id, "focus_type": focus_type, **kwargs},
        )

    def record_loop_opened(
        self, session_id: str, loop_id: str = "", source_type: str = "", **kwargs: Any
    ) -> dict[str, Any]:
        return self.record_event(
            CognitionEventType.LOOP_OPENED,
            session_id,
            {"loop_id": loop_id, "source_type": source_type, **kwargs},
        )

    def record_loop_resolved(
        self, session_id: str, loop_id: str = "", summary: str = "", **kwargs: Any
    ) -> dict[str, Any]:
        return self.record_event(
            CognitionEventType.LOOP_RESOLVED,
            session_id,
            {"loop_id": loop_id, "summary": summary, **kwargs},
        )

    def record_continuity_restored(
        self, session_id: str, previous_session_id: str = "", score: float = 0.0, **kwargs: Any
    ) -> dict[str, Any]:
        return self.record_event(
            CognitionEventType.CONTINUITY_RESTORED,
            session_id,
            {"previous_session_id": previous_session_id, "score": score, **kwargs},
        )

    def record_checkpoint_created(
        self, session_id: str, checkpoint_id: str = "", **kwargs: Any
    ) -> dict[str, Any]:
        return self.record_event(
            CognitionEventType.CHECKPOINT_CREATED,
            session_id,
            {"checkpoint_id": checkpoint_id, **kwargs},
        )

    def record_attention_reweighted(
        self, session_id: str, weight_type: str = "", old_value: float = 0.0, new_value: float = 0.0, **kwargs: Any
    ) -> dict[str, Any]:
        return self.record_event(
            CognitionEventType.ATTENTION_REWEIGHTED,
            session_id,
            {"weight_type": weight_type, "old_value": old_value, "new_value": new_value, **kwargs},
        )

    def record_temporal_snapshot(
        self, session_id: str, context_id: str = "", **kwargs: Any
    ) -> dict[str, Any]:
        return self.record_event(
            CognitionEventType.TEMPORAL_SNAPSHOT_CREATED,
            session_id,
            {"context_id": context_id, **kwargs},
        )

    def record_cognition_resumed(
        self, session_id: str, previous_session_id: str = "", **kwargs: Any
    ) -> dict[str, Any]:
        return self.record_event(
            CognitionEventType.COGNITION_RESUMED,
            session_id,
            {"previous_session_id": previous_session_id, **kwargs},
        )

    def record_cognition_archived(
        self, session_id: str, reason: str = "", **kwargs: Any
    ) -> dict[str, Any]:
        return self.record_event(
            CognitionEventType.COGNITION_ARCHIVED,
            session_id,
            {"reason": reason, **kwargs},
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_events_by_type(
        self,
        event_type: CognitionEventType,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Read events of a specific type from disk."""
        filename = EVENT_FILE_MAP.get(event_type.value)
        if not filename:
            return []

        path = self._obs_dir / filename
        if not path.exists():
            return []

        events: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))

        return events[-limit:]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_events": self._total_events,
            "event_counts": dict(self._event_counts),
        }
