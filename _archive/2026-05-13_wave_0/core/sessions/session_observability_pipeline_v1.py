"""Session Observability Pipeline v1.

Records 9 event types for session observability:
  session_created, session_restored, session_checkpointed,
  session_suspended, session_resumed, session_archived,
  session_terminated, session_expired, chronology_updated

Each event type persists to its own JSONL file.

UMH substrate subsystem. Phase 96.8BV.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.sessions.persistent_substrate_session_contracts_v1 import (
    SessionEventType,
    _new_id,
    _now_iso,
)


EVENT_FILE_MAP: dict[str, str] = {
    SessionEventType.SESSION_CREATED.value: "session_created_events.jsonl",
    SessionEventType.SESSION_RESTORED.value: "session_restored_events.jsonl",
    SessionEventType.SESSION_CHECKPOINTED.value: "session_checkpointed_events.jsonl",
    SessionEventType.SESSION_SUSPENDED.value: "session_suspended_events.jsonl",
    SessionEventType.SESSION_RESUMED.value: "session_resumed_events.jsonl",
    SessionEventType.SESSION_ARCHIVED.value: "session_archived_events.jsonl",
    SessionEventType.SESSION_TERMINATED.value: "session_terminated_events.jsonl",
    SessionEventType.SESSION_EXPIRED.value: "session_expired_events.jsonl",
    SessionEventType.CHRONOLOGY_UPDATED.value: "chronology_updated_events.jsonl",
}


class SessionObservabilityPipeline:
    """Records session events to JSONL files.

    9 event types, each with its own file.
    All events are immutable and append-only.
    """

    def __init__(
        self,
        obs_dir: str | Path = "data/runtime/session_observability",
    ) -> None:
        self._obs_dir = Path(obs_dir)
        self._obs_dir.mkdir(parents=True, exist_ok=True)
        self._event_counts: dict[str, int] = {
            et.value: 0 for et in SessionEventType
        }
        self._total_events: int = 0

    def record_event(
        self,
        event_type: SessionEventType,
        session_id: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record a session observability event."""
        event = {
            "event_id": _new_id("ssobs"),
            "event_type": event_type.value,
            "session_id": session_id,
            "data": data or {},
            "timestamp": _now_iso(),
        }

        filename = EVENT_FILE_MAP.get(
            event_type.value, "session_unknown_events.jsonl"
        )
        path = self._obs_dir / filename
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")

        self._event_counts[event_type.value] += 1
        self._total_events += 1
        return event

    def record_created(
        self, session_id: str, operator_id: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self.record_event(
            SessionEventType.SESSION_CREATED, session_id,
            {"operator_id": operator_id, **kw},
        )

    def record_restored(
        self, session_id: str, checkpoint_id: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self.record_event(
            SessionEventType.SESSION_RESTORED, session_id,
            {"checkpoint_id": checkpoint_id, **kw},
        )

    def record_checkpointed(
        self, session_id: str, checkpoint_id: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self.record_event(
            SessionEventType.SESSION_CHECKPOINTED, session_id,
            {"checkpoint_id": checkpoint_id, **kw},
        )

    def record_suspended(
        self, session_id: str, reason: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self.record_event(
            SessionEventType.SESSION_SUSPENDED, session_id,
            {"reason": reason, **kw},
        )

    def record_resumed(
        self, session_id: str, checkpoint_id: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self.record_event(
            SessionEventType.SESSION_RESUMED, session_id,
            {"checkpoint_id": checkpoint_id, **kw},
        )

    def record_archived(
        self, session_id: str, reason: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self.record_event(
            SessionEventType.SESSION_ARCHIVED, session_id,
            {"reason": reason, **kw},
        )

    def record_terminated(
        self, session_id: str, reason: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self.record_event(
            SessionEventType.SESSION_TERMINATED, session_id,
            {"reason": reason, **kw},
        )

    def record_expired(
        self, session_id: str, reason: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self.record_event(
            SessionEventType.SESSION_EXPIRED, session_id,
            {"reason": reason, **kw},
        )

    def record_chronology_updated(
        self, session_id: str, event_kind: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self.record_event(
            SessionEventType.CHRONOLOGY_UPDATED, session_id,
            {"event_kind": event_kind, **kw},
        )

    def get_events_by_type(
        self, event_type: SessionEventType, limit: int = 50,
    ) -> list[dict[str, Any]]:
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

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_events": self._total_events,
            "event_counts": dict(self._event_counts),
        }
