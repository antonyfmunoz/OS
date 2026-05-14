"""Session Chronology Engine v1.

Tracks ordered event history across all substrate layers
within a session:
  session_creation, runtime_traversal, cognition_transition,
  workflow_transition, embodiment_transition, ingress_transition,
  continuity_restoration, operator_resumption

All events are sequenced and persisted to JSONL.

UMH substrate subsystem. Phase 96.8BV.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.sessions.persistent_substrate_session_contracts_v1 import (
    ChronologyEventKind,
    SessionChronology,
    _now_iso,
)


class SessionChronologyEngine:
    """Tracks ordered chronological events for substrate sessions.

    Events are numbered sequentially per session. All events
    are immutable and append-only. Supports reconstruction
    of full session timeline.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/substrate_sessions",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._events: dict[str, list[SessionChronology]] = {}
        self._sequence_counters: dict[str, int] = {}
        self._total_events: int = 0

    def record(
        self,
        session_id: str,
        kind: ChronologyEventKind,
        description: str = "",
        source_layer: str = "",
        data: dict[str, Any] | None = None,
    ) -> SessionChronology:
        """Record a chronological event for a session."""
        seq = self._sequence_counters.get(session_id, 0)
        self._sequence_counters[session_id] = seq + 1

        event = SessionChronology(
            session_id=session_id,
            kind=kind.value,
            description=description,
            source_layer=source_layer,
            data=data or {},
            sequence_number=seq,
        )

        if session_id not in self._events:
            self._events[session_id] = []
        self._events[session_id].append(event)
        self._total_events += 1

        path = self._state_dir / "session_chronology.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), default=str) + "\n")

        return event

    def record_session_creation(
        self, session_id: str, operator_id: str = "",
    ) -> SessionChronology:
        return self.record(
            session_id, ChronologyEventKind.SESSION_CREATION,
            description="Session created",
            source_layer="session",
            data={"operator_id": operator_id},
        )

    def record_runtime_traversal(
        self, session_id: str, command: str = "", outcome_id: str = "",
    ) -> SessionChronology:
        return self.record(
            session_id, ChronologyEventKind.RUNTIME_TRAVERSAL,
            description=f"Runtime traversal: {command}",
            source_layer="runtime",
            data={"command": command, "outcome_id": outcome_id},
        )

    def record_cognition_transition(
        self, session_id: str, from_phase: str = "", to_phase: str = "",
    ) -> SessionChronology:
        return self.record(
            session_id, ChronologyEventKind.COGNITION_TRANSITION,
            description=f"Cognition: {from_phase} -> {to_phase}",
            source_layer="cognition",
            data={"from_phase": from_phase, "to_phase": to_phase},
        )

    def record_workflow_transition(
        self, session_id: str, workflow_id: str = "", step: str = "",
    ) -> SessionChronology:
        return self.record(
            session_id, ChronologyEventKind.WORKFLOW_TRANSITION,
            description=f"Workflow transition: {step}",
            source_layer="workflow",
            data={"workflow_id": workflow_id, "step": step},
        )

    def record_embodiment_transition(
        self, session_id: str, layer: str = "", mode: str = "",
    ) -> SessionChronology:
        return self.record(
            session_id, ChronologyEventKind.EMBODIMENT_TRANSITION,
            description=f"Embodiment: {layer} -> {mode}",
            source_layer="embodiment",
            data={"layer": layer, "mode": mode},
        )

    def record_ingress_transition(
        self, session_id: str, source: str = "", signal_id: str = "",
    ) -> SessionChronology:
        return self.record(
            session_id, ChronologyEventKind.INGRESS_TRANSITION,
            description=f"Ingress from {source}",
            source_layer="ingress",
            data={"source": source, "signal_id": signal_id},
        )

    def record_continuity_restoration(
        self, session_id: str, previous_session_id: str = "",
    ) -> SessionChronology:
        return self.record(
            session_id, ChronologyEventKind.CONTINUITY_RESTORATION,
            description=f"Continuity restored from {previous_session_id}",
            source_layer="continuity",
            data={"previous_session_id": previous_session_id},
        )

    def record_operator_resumption(
        self, session_id: str, operator_id: str = "",
    ) -> SessionChronology:
        return self.record(
            session_id, ChronologyEventKind.OPERATOR_RESUMPTION,
            description=f"Operator resumed: {operator_id}",
            source_layer="session",
            data={"operator_id": operator_id},
        )

    def get_chronology(
        self, session_id: str, limit: int = 100,
    ) -> list[dict[str, Any]]:
        events = self._events.get(session_id, [])
        return [e.to_dict() for e in events[-limit:]]

    def get_chronology_snapshot(
        self, session_id: str,
    ) -> list[dict[str, Any]]:
        events = self._events.get(session_id, [])
        return [e.to_dict() for e in events]

    def get_sequence_number(self, session_id: str) -> int:
        return self._sequence_counters.get(session_id, 0)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_events": self._total_events,
            "tracked_sessions": len(self._events),
        }
