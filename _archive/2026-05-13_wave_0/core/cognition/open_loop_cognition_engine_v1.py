"""Open Loop Cognition Engine v1.

Manages the 7-state lifecycle of open operational loops:
  active -> waiting -> suspended -> stale -> resumed -> resolved -> archived

Open loops represent unresolved work that requires future
attention or resolution. They persist across sessions and
are surfaced during continuity restoration.

The engine:
  - Creates and tracks loops
  - Validates state transitions
  - Detects stale loops (time-based)
  - Persists loop state to JSONL
  - Provides prioritized loop views
  - Emits lineage receipts for transitions

UMH substrate subsystem. Phase 96.8BT.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.cognition.persistent_operator_cognition_contracts_v1 import (
    CognitionDecisionType,
    CognitiveLineageReceipt,
    LoopState,
    OpenOperationalLoop,
    _content_hash,
    _new_id,
    _now_iso,
)


VALID_LOOP_TRANSITIONS: dict[str, list[str]] = {
    "active": ["waiting", "suspended", "stale", "resolved"],
    "waiting": ["active", "resumed", "stale", "resolved"],
    "suspended": ["resumed", "stale", "archived"],
    "stale": ["resumed", "archived"],
    "resumed": ["active", "resolved"],
    "resolved": ["archived"],
    "archived": [],
}

ACTIVE_LOOP_STATES: set[LoopState] = {
    LoopState.ACTIVE,
    LoopState.WAITING,
    LoopState.RESUMED,
}


class OpenLoopCognitionEngine:
    """Manages the lifecycle of open operational loops.

    Tracks unresolved work across sessions. Does not
    execute actions or generate intent — only tracks state.
    """

    def __init__(
        self,
        session_id: str = "",
        state_dir: str | Path = "data/runtime/cognition_state",
    ) -> None:
        self._session_id = session_id or _new_id("sess")
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._loops: dict[str, OpenOperationalLoop] = {}
        self._receipts: list[CognitiveLineageReceipt] = []
        self._total_opened: int = 0
        self._total_resolved: int = 0
        self._total_transitions: int = 0
        self._invalid_transitions: int = 0

    # ------------------------------------------------------------------
    # Loop creation
    # ------------------------------------------------------------------

    def open_loop(
        self,
        source_type: str,
        source_id: str,
        description: str,
        priority: float = 1.0,
        stale_after_seconds: float = 3600.0,
        tags: list[str] | None = None,
        related_workflow_ids: list[str] | None = None,
    ) -> OpenOperationalLoop:
        """Open a new operational loop."""
        loop = OpenOperationalLoop(
            session_id=self._session_id,
            source_type=source_type,
            source_id=source_id,
            description=description,
            priority=priority,
            stale_after_seconds=stale_after_seconds,
            tags=tags or [],
            related_workflow_ids=related_workflow_ids or [],
        )
        self._loops[loop.loop_id] = loop
        self._total_opened += 1

        self._persist_loop_event("loop_opened", loop)
        self._emit_receipt(
            action=f"loop_opened:{source_type}:{source_id}",
            input_hash=_content_hash({"source_id": source_id}),
            output_hash=_content_hash(loop.to_dict()),
        )
        return loop

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def transition(
        self,
        loop_id: str,
        to_state: LoopState,
        resolution_summary: str = "",
    ) -> bool:
        """Transition a loop to a new state. Returns False if invalid."""
        loop = self._loops.get(loop_id)
        if not loop:
            return False

        valid_targets = VALID_LOOP_TRANSITIONS.get(loop.state.value, [])
        if to_state.value not in valid_targets:
            self._invalid_transitions += 1
            return False

        old_state = loop.state
        loop.state = to_state
        loop.last_touched = _now_iso()
        if resolution_summary:
            loop.resolution_summary = resolution_summary
        if to_state == LoopState.RESOLVED:
            self._total_resolved += 1

        self._total_transitions += 1
        self._persist_loop_event(
            f"loop_transition:{old_state.value}->{to_state.value}", loop
        )
        self._emit_receipt(
            action=f"loop_transition:{loop_id}:{old_state.value}->{to_state.value}",
            input_hash=_content_hash({"old_state": old_state.value}),
            output_hash=_content_hash({"new_state": to_state.value}),
        )
        return True

    def resolve(self, loop_id: str, summary: str = "") -> bool:
        """Convenience: resolve a loop directly from any active-like state."""
        loop = self._loops.get(loop_id)
        if not loop:
            return False

        if loop.state == LoopState.RESOLVED:
            return True

        if loop.state in (LoopState.SUSPENDED, LoopState.STALE):
            if not self.transition(loop_id, LoopState.RESUMED):
                return False
        if loop.state in (LoopState.WAITING,):
            if not self.transition(loop_id, LoopState.RESUMED):
                return False

        return self.transition(loop_id, LoopState.RESOLVED, summary)

    # ------------------------------------------------------------------
    # Staleness detection
    # ------------------------------------------------------------------

    def detect_stale_loops(self) -> list[OpenOperationalLoop]:
        """Detect loops that have exceeded their stale threshold."""
        now = datetime.now(timezone.utc)
        stale: list[OpenOperationalLoop] = []

        for loop in self._loops.values():
            if loop.state in (LoopState.RESOLVED, LoopState.ARCHIVED):
                continue

            try:
                last_touched = datetime.fromisoformat(loop.last_touched)
            except (ValueError, TypeError):
                continue

            elapsed = (now - last_touched).total_seconds()
            if elapsed > loop.stale_after_seconds:
                if loop.state != LoopState.STALE:
                    self.transition(loop.loop_id, LoopState.STALE)
                    stale.append(loop)

        return stale

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_loop(self, loop_id: str) -> OpenOperationalLoop | None:
        return self._loops.get(loop_id)

    def get_active_loops(self) -> list[OpenOperationalLoop]:
        return [l for l in self._loops.values() if l.state in ACTIVE_LOOP_STATES]

    def get_all_loops(self) -> list[OpenOperationalLoop]:
        return list(self._loops.values())

    def get_loops_by_priority(self, limit: int = 10) -> list[OpenOperationalLoop]:
        """Get active loops sorted by priority (highest first)."""
        active = self.get_active_loops()
        active.sort(key=lambda l: l.priority, reverse=True)
        return active[:limit]

    def get_loops_by_tag(self, tag: str) -> list[OpenOperationalLoop]:
        return [l for l in self._loops.values() if tag in l.tags]

    def get_loops_by_source(self, source_type: str) -> list[OpenOperationalLoop]:
        return [l for l in self._loops.values() if l.source_type == source_type]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_loop_event(
        self, event_type: str, loop: OpenOperationalLoop
    ) -> None:
        record = {
            "event_type": event_type,
            "loop_id": loop.loop_id,
            "source_type": loop.source_type,
            "state": loop.state.value,
            "priority": loop.priority,
            "timestamp": _now_iso(),
        }
        path = self._state_dir / "open_loop_events.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def _emit_receipt(
        self,
        action: str,
        input_hash: str = "",
        output_hash: str = "",
    ) -> CognitiveLineageReceipt:
        receipt = CognitiveLineageReceipt(
            session_id=self._session_id,
            decision_type=CognitionDecisionType.LOOP_PRIORITIZE,
            action=action,
            component="open_loop_engine",
            input_hash=input_hash,
            output_hash=output_hash,
        )
        self._receipts.append(receipt)
        return receipt

    # ------------------------------------------------------------------
    # Bulk operations for continuity restoration
    # ------------------------------------------------------------------

    def restore_loops(
        self, loops_data: list[dict[str, Any]]
    ) -> list[OpenOperationalLoop]:
        """Restore loops from checkpoint/snapshot data."""
        restored: list[OpenOperationalLoop] = []
        for data in loops_data:
            loop = OpenOperationalLoop(
                loop_id=data.get("loop_id", ""),
                session_id=self._session_id,
                source_type=data.get("source_type", ""),
                source_id=data.get("source_id", ""),
                description=data.get("description", ""),
                state=LoopState(data.get("state", "active")),
                priority=data.get("priority", 1.0),
                stale_after_seconds=data.get("stale_after_seconds", 3600.0),
                tags=data.get("tags", []),
                related_workflow_ids=data.get("related_workflow_ids", []),
            )
            self._loops[loop.loop_id] = loop
            restored.append(loop)
        return restored

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_opened": self._total_opened,
            "total_resolved": self._total_resolved,
            "total_transitions": self._total_transitions,
            "invalid_transitions": self._invalid_transitions,
            "active_loops": len(self.get_active_loops()),
            "total_loops": len(self._loops),
            "total_receipts": len(self._receipts),
        }
