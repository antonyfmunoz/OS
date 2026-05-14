"""Temporal Continuity Engine v1.

Maintains temporal ordering and session chronology
for cognition continuity across restarts.

Responsibilities:
  - Track session start/end boundaries
  - Record restart events with gap measurement
  - Maintain chronological event ordering
  - Link sessions into a continuity chain
  - Persist temporal lineage to JSONL

The engine does not take autonomous action.
It records and exposes temporal context that
other components use for continuity decisions.

UMH substrate subsystem. Phase 96.8BT.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.cognition.persistent_operator_cognition_contracts_v1 import (
    TemporalExecutionContext,
    _content_hash,
    _new_id,
    _now_iso,
)


class TemporalContinuityEngine:
    """Tracks temporal context across sessions and restarts.

    Maintains a chronological record of session boundaries,
    restart events, and continuity gaps. Does not execute
    actions or generate intent.
    """

    def __init__(
        self,
        session_id: str = "",
        state_dir: str | Path = "data/runtime/cognition_state",
    ) -> None:
        self._session_id = session_id or _new_id("sess")
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._context = TemporalExecutionContext(
            session_id=self._session_id,
        )
        self._session_chain: list[str] = [self._session_id]
        self._chronology: list[dict[str, Any]] = []
        self._total_events: int = 0
        self._total_restarts: int = 0

        self._record_event("session_started", {
            "session_id": self._session_id,
        })

    @property
    def context(self) -> TemporalExecutionContext:
        return self._context

    @property
    def session_id(self) -> str:
        return self._session_id

    # ------------------------------------------------------------------
    # Session linking
    # ------------------------------------------------------------------

    def link_previous_session(
        self,
        previous_session_id: str,
        previous_end_iso: str = "",
    ) -> float:
        """Link this session to a previous one. Returns gap in seconds."""
        self._context.previous_session_id = previous_session_id
        self._context.restart_count += 1
        self._context.last_resumption_iso = _now_iso()
        self._total_restarts += 1

        gap = 0.0
        if previous_end_iso:
            try:
                prev_end = datetime.fromisoformat(previous_end_iso)
                now = datetime.now(timezone.utc)
                gap = (now - prev_end).total_seconds()
            except (ValueError, TypeError):
                pass

        self._context.continuity_gap_seconds = gap

        if previous_session_id not in self._session_chain:
            self._session_chain.insert(0, previous_session_id)

        self._record_event("session_linked", {
            "previous_session_id": previous_session_id,
            "gap_seconds": round(gap, 2),
            "restart_count": self._context.restart_count,
        })

        return gap

    # ------------------------------------------------------------------
    # Chronology
    # ------------------------------------------------------------------

    def record_checkpoint(self, checkpoint_id: str) -> None:
        """Record a checkpoint event in the chronology."""
        self._context.last_checkpoint_iso = _now_iso()
        self._record_event("checkpoint_recorded", {
            "checkpoint_id": checkpoint_id,
        })

    def record_workflow_event(
        self,
        workflow_id: str,
        event_type: str,
    ) -> None:
        """Record a workflow-related event in the chronology."""
        self._record_event("workflow_event", {
            "workflow_id": workflow_id,
            "event_type": event_type,
        })

    def record_focus_event(
        self,
        focus_id: str,
        event_type: str,
    ) -> None:
        """Record a focus-related event in the chronology."""
        self._record_event("focus_event", {
            "focus_id": focus_id,
            "event_type": event_type,
        })

    def record_custom_event(
        self,
        event_type: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Record a custom event in the chronology."""
        self._record_event(event_type, data or {})

    def _record_event(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        entry = {
            "event_id": _new_id("tevt"),
            "session_id": self._session_id,
            "event_type": event_type,
            "data": data,
            "timestamp": _now_iso(),
            "sequence": self._total_events,
        }
        self._chronology.append(entry)
        self._context.chronology_entries += 1
        self._total_events += 1

        path = self._state_dir / "temporal_chronology.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_chronology(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._chronology[-limit:]

    def get_session_chain(self) -> list[str]:
        return list(self._session_chain)

    def get_continuity_gap(self) -> float:
        return self._context.continuity_gap_seconds

    def get_restart_count(self) -> int:
        return self._context.restart_count

    # ------------------------------------------------------------------
    # Session end recording
    # ------------------------------------------------------------------

    def end_session(self) -> dict[str, Any]:
        """Record session end. Returns session summary."""
        self._record_event("session_ended", {
            "session_id": self._session_id,
            "total_events": self._total_events,
            "restart_count": self._total_restarts,
        })

        summary = {
            "session_id": self._session_id,
            "started_at": self._context.session_started_at,
            "ended_at": _now_iso(),
            "total_events": self._total_events,
            "restart_count": self._total_restarts,
            "previous_session_id": self._context.previous_session_id,
            "continuity_gap_seconds": self._context.continuity_gap_seconds,
        }

        path = self._state_dir / "session_summary.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(summary, default=str) + "\n")

        return summary

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        return {
            "session_id": self._session_id,
            "total_events": self._total_events,
            "total_restarts": self._total_restarts,
            "session_chain_length": len(self._session_chain),
            "continuity_gap_seconds": round(
                self._context.continuity_gap_seconds, 2
            ),
            "chronology_entries": self._context.chronology_entries,
        }
