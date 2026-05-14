"""Runtime Ingress Observability Pipeline v1.

Records 8 event types for ingress observability:
  ingress_received, ingress_normalized, ingress_authenticated,
  ingress_routed, ingress_denied, ingress_completed,
  ingress_resumed, ingress_expired

Each event type persists to its own JSONL file.

UMH substrate subsystem. Phase 96.8BU.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.ingress.live_runtime_ingress_contracts_v1 import (
    IngressEventType,
    _new_id,
    _now_iso,
)


EVENT_FILE_MAP: dict[str, str] = {
    IngressEventType.INGRESS_RECEIVED.value: "ingress_received_events.jsonl",
    IngressEventType.INGRESS_NORMALIZED.value: "ingress_normalized_events.jsonl",
    IngressEventType.INGRESS_AUTHENTICATED.value: "ingress_authenticated_events.jsonl",
    IngressEventType.INGRESS_ROUTED.value: "ingress_routed_events.jsonl",
    IngressEventType.INGRESS_DENIED.value: "ingress_denied_events.jsonl",
    IngressEventType.INGRESS_COMPLETED.value: "ingress_completed_events.jsonl",
    IngressEventType.INGRESS_RESUMED.value: "ingress_resumed_events.jsonl",
    IngressEventType.INGRESS_EXPIRED.value: "ingress_expired_events.jsonl",
}


class RuntimeIngressObservabilityPipeline:
    """Records ingress events to JSONL files.

    8 event types, each with its own file.
    All events are immutable and append-only.
    """

    def __init__(
        self,
        obs_dir: str | Path = "data/runtime/ingress_observability",
    ) -> None:
        self._obs_dir = Path(obs_dir)
        self._obs_dir.mkdir(parents=True, exist_ok=True)
        self._event_counts: dict[str, int] = {
            et.value: 0 for et in IngressEventType
        }
        self._total_events: int = 0

    def record_event(
        self,
        event_type: IngressEventType,
        session_id: str,
        signal_id: str = "",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record an ingress observability event."""
        event = {
            "event_id": _new_id("ingobs"),
            "event_type": event_type.value,
            "session_id": session_id,
            "signal_id": signal_id,
            "data": data or {},
            "timestamp": _now_iso(),
        }

        filename = EVENT_FILE_MAP.get(
            event_type.value, "ingress_unknown_events.jsonl"
        )
        path = self._obs_dir / filename
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")

        self._event_counts[event_type.value] += 1
        self._total_events += 1
        return event

    def record_received(
        self, session_id: str, signal_id: str, source: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self.record_event(
            IngressEventType.INGRESS_RECEIVED, session_id, signal_id,
            {"source": source, **kw},
        )

    def record_normalized(
        self, session_id: str, signal_id: str, command: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self.record_event(
            IngressEventType.INGRESS_NORMALIZED, session_id, signal_id,
            {"command": command, **kw},
        )

    def record_authenticated(
        self, session_id: str, signal_id: str, operator_id: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self.record_event(
            IngressEventType.INGRESS_AUTHENTICATED, session_id, signal_id,
            {"operator_id": operator_id, **kw},
        )

    def record_routed(
        self, session_id: str, signal_id: str, spine_source: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self.record_event(
            IngressEventType.INGRESS_ROUTED, session_id, signal_id,
            {"spine_source": spine_source, **kw},
        )

    def record_denied(
        self, session_id: str, signal_id: str, reason: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self.record_event(
            IngressEventType.INGRESS_DENIED, session_id, signal_id,
            {"reason": reason, **kw},
        )

    def record_completed(
        self, session_id: str, signal_id: str, outcome_id: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self.record_event(
            IngressEventType.INGRESS_COMPLETED, session_id, signal_id,
            {"outcome_id": outcome_id, **kw},
        )

    def record_resumed(
        self, session_id: str, signal_id: str, previous_session: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self.record_event(
            IngressEventType.INGRESS_RESUMED, session_id, signal_id,
            {"previous_session": previous_session, **kw},
        )

    def record_expired(
        self, session_id: str, signal_id: str, reason: str = "", **kw: Any,
    ) -> dict[str, Any]:
        return self.record_event(
            IngressEventType.INGRESS_EXPIRED, session_id, signal_id,
            {"reason": reason, **kw},
        )

    def get_events_by_type(
        self, event_type: IngressEventType, limit: int = 50,
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
