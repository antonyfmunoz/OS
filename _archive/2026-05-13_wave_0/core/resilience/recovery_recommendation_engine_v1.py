"""Recovery Recommendation Engine v1.

Generates recovery recommendations based on detected instability.
All recommendations require operator approval — the engine CANNOT
execute repairs, rollbacks, mutations, or healing autonomously.

UMH substrate subsystem. Phase 96.8BZ.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.resilience.adaptive_resilience_contracts_v1 import (
    RecoveryRecommendation,
    RecoveryAction,
    _now_iso,
)


MAX_PENDING_RECOMMENDATIONS: int = 20
MAX_RECOMMENDATION_HISTORY: int = 100

SEVERITY_TO_ACTION: dict[str, str] = {
    "stable": "escalate_to_operator",
    "transient": "escalate_to_operator",
    "intermittent": "reduce_concurrency",
    "persistent": "isolate_environment",
    "cascading": "isolate_environment",
    "systemic": "escalate_to_operator",
}

SEVERITY_TO_PRIORITY: dict[str, str] = {
    "stable": "deferred",
    "transient": "standard",
    "intermittent": "standard",
    "persistent": "high",
    "cascading": "critical",
    "systemic": "critical",
}


class RecoveryRecommendationEngine:
    """Generates recovery recommendations without executing them."""

    def __init__(self, state_dir: str | Path = "data/runtime/resilience") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._pending: list[RecoveryRecommendation] = []
        self._history: list[RecoveryRecommendation] = []
        self._total_generated: int = 0
        self._total_approved: int = 0
        self._total_rejected: int = 0

    def recommend(
        self,
        target_subsystem: str,
        instability_class: str = "transient",
        rationale: str = "",
    ) -> RecoveryRecommendation:
        action = SEVERITY_TO_ACTION.get(instability_class, "escalate_to_operator")
        priority = SEVERITY_TO_PRIORITY.get(instability_class, "standard")

        rec = RecoveryRecommendation(
            target_subsystem=target_subsystem,
            action=action,
            priority=priority,
            rationale=rationale or f"Instability detected: {instability_class}",
        )

        self._pending.append(rec)
        if len(self._pending) > MAX_PENDING_RECOMMENDATIONS:
            overflow = self._pending.pop(0)
            self._history.append(overflow)

        self._total_generated += 1

        path = self._state_dir / "recovery_recommendations.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec.to_dict(), default=str) + "\n")

        return rec

    def approve(
        self,
        recommendation_id: str,
        approved_by: str = "operator",
    ) -> bool:
        for rec in self._pending:
            if rec.recommendation_id == recommendation_id:
                rec.approved = True
                rec.approved_by = approved_by
                self._pending.remove(rec)
                self._history.append(rec)
                self._total_approved += 1
                return True
        return False

    def reject(self, recommendation_id: str) -> bool:
        for rec in self._pending:
            if rec.recommendation_id == recommendation_id:
                rec.approved = False
                self._pending.remove(rec)
                self._history.append(rec)
                self._total_rejected += 1
                return True
        return False

    def get_pending(self) -> list[RecoveryRecommendation]:
        return list(self._pending)

    def get_pending_by_priority(self, priority: str) -> list[RecoveryRecommendation]:
        return [r for r in self._pending if r.priority == priority]

    def get_history(self, limit: int = 10) -> list[RecoveryRecommendation]:
        return self._history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        return {
            "pending_count": len(self._pending),
            "total_generated": self._total_generated,
            "total_approved": self._total_approved,
            "total_rejected": self._total_rejected,
            "history_length": len(self._history),
        }
