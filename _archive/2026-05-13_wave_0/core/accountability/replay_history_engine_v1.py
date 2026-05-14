"""Replay History Engine v1.

Tracks replay generations, restorations, certifications,
validations, and divergences prevented.

UMH substrate subsystem. Phase 96.8CL.
"""

from __future__ import annotations

from typing import Any

from core.accountability.sovereign_operational_accountability_contracts_v1 import (
    ReplayHistoryState,
    _now_iso,
)

MAX_REPLAY_HISTORY = 200

REPLAY_HISTORY_TYPES: list[str] = [
    "replay_generations",
    "replay_restorations",
    "replay_certifications",
    "replay_validations",
    "replay_divergences_prevented",
]


class ReplayHistoryEngine:
    def __init__(self) -> None:
        self._entries: list[ReplayHistoryState] = []

    def record_history(self, generations: int = 1, restorations: int = 0) -> dict[str, Any]:
        if len(self._entries) >= MAX_REPLAY_HISTORY:
            raise ValueError("Max replay history reached")
        state = ReplayHistoryState(generations=generations, restorations=restorations)
        self._entries.append(state)
        return state.to_dict()

    def record_all_types(self) -> dict[str, Any]:
        results = []
        for _ in REPLAY_HISTORY_TYPES:
            r = self.record_history(generations=1, restorations=0)
            results.append(r)
        return {"all_consistent": all(r["consistency_preserved"] for r in results), "entries": results, "total": len(results)}

    def all_consistent(self) -> bool:
        if not self._entries:
            return True
        return all(e.consistency_preserved for e in self._entries)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_entries": len(self._entries),
            "all_consistent": self.all_consistent(),
            "history_types": len(REPLAY_HISTORY_TYPES),
        }
