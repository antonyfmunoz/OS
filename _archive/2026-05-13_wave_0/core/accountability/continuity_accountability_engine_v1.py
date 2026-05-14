"""Continuity Accountability Engine v1.

Tracks checkpoint history, restoration lineage, continuity branching,
chronology restoration, and session transitions.

UMH substrate subsystem. Phase 96.8CL.
"""

from __future__ import annotations

from typing import Any

from core.accountability.sovereign_operational_accountability_contracts_v1 import (
    ContinuityHistoryState,
    _now_iso,
)

MAX_CONTINUITY_HISTORY = 200

CONTINUITY_HISTORY_TYPES: list[str] = [
    "checkpoint_history",
    "restoration_lineage",
    "continuity_branching",
    "chronology_restoration",
    "session_transitions",
]


class ContinuityAccountabilityEngine:
    def __init__(self) -> None:
        self._entries: list[ContinuityHistoryState] = []

    def record_history(self, checkpoints: int = 1, restorations: int = 0) -> dict[str, Any]:
        if len(self._entries) >= MAX_CONTINUITY_HISTORY:
            raise ValueError("Max continuity history reached")
        state = ContinuityHistoryState(checkpoints=checkpoints, restorations=restorations)
        self._entries.append(state)
        return state.to_dict()

    def record_all_types(self) -> dict[str, Any]:
        results = []
        for _ in CONTINUITY_HISTORY_TYPES:
            r = self.record_history(checkpoints=1, restorations=0)
            results.append(r)
        return {"all_preserved": all(r["integrity_preserved"] for r in results), "entries": results, "total": len(results)}

    def all_preserved(self) -> bool:
        if not self._entries:
            return True
        return all(e.integrity_preserved for e in self._entries)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_entries": len(self._entries),
            "all_preserved": self.all_preserved(),
            "history_types": len(CONTINUITY_HISTORY_TYPES),
        }
