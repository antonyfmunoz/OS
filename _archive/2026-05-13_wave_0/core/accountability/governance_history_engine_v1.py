"""Governance History Engine v1.

Reconstructs governance rule evolution, decisions, approvals/denials,
escalation lineage, and policy application history.

UMH substrate subsystem. Phase 96.8CL.
"""

from __future__ import annotations

from typing import Any

from core.accountability.sovereign_operational_accountability_contracts_v1 import (
    GovernanceHistoryState,
    _now_iso,
)

MAX_GOVERNANCE_HISTORY = 200

GOVERNANCE_HISTORY_TYPES: list[str] = [
    "rule_evolution",
    "governance_decisions",
    "approvals_denials",
    "escalation_lineage",
    "policy_application",
]


class GovernanceHistoryEngine:
    def __init__(self) -> None:
        self._entries: list[GovernanceHistoryState] = []

    def record_history(self, decision_count: int = 1, approvals: int = 1, denials: int = 0) -> dict[str, Any]:
        if len(self._entries) >= MAX_GOVERNANCE_HISTORY:
            raise ValueError("Max governance history reached")
        state = GovernanceHistoryState(decision_count=decision_count, approvals=approvals, denials=denials)
        self._entries.append(state)
        return state.to_dict()

    def record_all_types(self) -> dict[str, Any]:
        results = []
        for ht in GOVERNANCE_HISTORY_TYPES:
            r = self.record_history(decision_count=1, approvals=1, denials=0)
            results.append(r)
        return {"all_deterministic": all(r["timeline_deterministic"] for r in results), "entries": results, "total": len(results)}

    def all_deterministic(self) -> bool:
        if not self._entries:
            return True
        return all(e.timeline_deterministic for e in self._entries)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_entries": len(self._entries),
            "all_deterministic": self.all_deterministic(),
            "history_types": len(GOVERNANCE_HISTORY_TYPES),
        }
