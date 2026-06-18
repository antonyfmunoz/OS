"""Decision Validity Engine — evaluates whether decisions still make sense.

Deterministic validity assessment based on assumption health, goal alignment,
and outcome progress. Read-only — never mutates decisions or assumptions.

Campaign 9.3 — Decision Intelligence & Strategic Memory.
UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


class ValidityStatus(str, Enum):
    VALID = "valid"
    WATCH = "watch"
    AT_RISK = "at_risk"
    INVALID = "invalid"


@dataclass
class DecisionValidity:
    decision_id: str = ""
    decision_title: str = ""
    validity: str = ValidityStatus.VALID.value
    assumption_health: dict[str, Any] = field(default_factory=dict)
    goal_alignment: str = ""
    outcome_progress: float = 0.0
    risk_factors: list[str] = field(default_factory=list)
    recommendation: str = ""
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_title": self.decision_title,
            "validity": self.validity,
            "assumption_health": dict(self.assumption_health),
            "goal_alignment": self.goal_alignment,
            "outcome_progress": self.outcome_progress,
            "risk_factors": list(self.risk_factors),
            "recommendation": self.recommendation,
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DecisionValidity:
        return cls(
            decision_id=d.get("decision_id", ""),
            decision_title=d.get("decision_title", ""),
            validity=d.get("validity", ValidityStatus.VALID.value),
            assumption_health=d.get("assumption_health", {}),
            goal_alignment=d.get("goal_alignment", ""),
            outcome_progress=d.get("outcome_progress", 0.0),
            risk_factors=d.get("risk_factors", []),
            recommendation=d.get("recommendation", ""),
            generated_at=d.get("generated_at", 0.0),
        )


# ── Engine ────────────────────────────────────────────────────────────────


class DecisionValidityEngine:
    """Deterministic validity assessment for strategic decisions."""

    def __init__(
        self,
        decision_registry: Any | None = None,
        assumption_tracking: Any | None = None,
        goal_alignment: Any | None = None,
        outcome_tracking: Any | None = None,
        reality_graph: Any | None = None,
    ) -> None:
        self._decision_registry = decision_registry
        self._assumption_tracking = assumption_tracking
        self._goal_alignment = goal_alignment
        self._outcome_tracking = outcome_tracking
        self._reality_graph = reality_graph

    def evaluate(self, decision_id: str) -> DecisionValidity:
        """Evaluate validity of a single decision."""
        result = DecisionValidity(
            decision_id=decision_id,
            generated_at=time.time(),
        )

        decision = self._get_decision(decision_id)
        if not decision:
            result.validity = ValidityStatus.INVALID.value
            result.recommendation = "not_found"
            return result

        result.decision_title = decision.title

        ah = self._assess_assumption_health(decision)
        result.assumption_health = ah

        ga = self._assess_goal_alignment(decision)
        result.goal_alignment = ga

        op = self._assess_outcome_progress(decision)
        result.outcome_progress = op

        risks = self._collect_risk_factors(ah, ga, op)
        result.risk_factors = risks

        validity, recommendation = self._classify(ah, ga, op, risks)
        result.validity = validity
        result.recommendation = recommendation

        return result

    def evaluate_all(self) -> list[DecisionValidity]:
        """Evaluate all active decisions."""
        if not self._decision_registry:
            return []
        try:
            decisions = self._decision_registry.active_decisions()
            return [self.evaluate(d.decision_id) for d in decisions]
        except Exception:
            logger.debug("Failed to evaluate all decisions", exc_info=True)
            return []

    def at_risk(self) -> list[DecisionValidity]:
        """Return decisions that are AT_RISK or WATCH."""
        return [
            v for v in self.evaluate_all()
            if v.validity in (ValidityStatus.AT_RISK.value, ValidityStatus.WATCH.value)
        ]

    def invalid(self) -> list[DecisionValidity]:
        """Return decisions that are INVALID."""
        return [
            v for v in self.evaluate_all()
            if v.validity == ValidityStatus.INVALID.value
        ]

    def summary(self) -> dict[str, Any]:
        """Aggregated validity summary."""
        all_v = self.evaluate_all()
        by_validity: dict[str, int] = {}
        for v in all_v:
            by_validity[v.validity] = by_validity.get(v.validity, 0) + 1
        at_risk_count = sum(
            1 for v in all_v
            if v.validity in (ValidityStatus.AT_RISK.value, ValidityStatus.WATCH.value)
        )
        invalid_count = sum(
            1 for v in all_v
            if v.validity == ValidityStatus.INVALID.value
        )
        recommendations = [
            {"decision_id": v.decision_id, "recommendation": v.recommendation}
            for v in all_v
            if v.recommendation and v.recommendation not in ("maintain", "")
        ]
        return {
            "total_evaluated": len(all_v),
            "by_validity": by_validity,
            "at_risk_count": at_risk_count,
            "invalid_count": invalid_count,
            "recommendations": recommendations,
            "generated_at": time.time(),
        }

    # ── Internal ──────────────────────────────────────────────────────

    def _get_decision(self, decision_id: str) -> Any | None:
        if not self._decision_registry:
            return None
        try:
            return self._decision_registry.get(decision_id)
        except Exception:
            logger.debug("Failed to get decision %s", decision_id, exc_info=True)
            return None

    def _assess_assumption_health(self, decision: Any) -> dict[str, Any]:
        """Check how many assumptions are still valid."""
        result: dict[str, Any] = {
            "total": 0,
            "active": 0,
            "validated": 0,
            "invalidated": 0,
            "unknown": 0,
        }
        if not self._assumption_tracking or not hasattr(decision, "assumptions"):
            return result

        try:
            for asm_id in decision.assumptions:
                asm = self._assumption_tracking.get(asm_id)
                if not asm:
                    result["unknown"] += 1
                    result["total"] += 1
                    continue
                result["total"] += 1
                status = asm.status if hasattr(asm, "status") else "unknown"
                if status in result:
                    result[status] += 1
                else:
                    result["unknown"] += 1
        except Exception:
            logger.debug("Failed to assess assumptions", exc_info=True)

        return result

    def _assess_goal_alignment(self, decision: Any) -> str:
        """Check if decision's goals are still active."""
        if not hasattr(decision, "goal_refs") or not decision.goal_refs:
            return "no_goals"

        if not self._goal_alignment:
            return "unknown"

        try:
            report = self._goal_alignment.report()
            if hasattr(report, "alignment_score"):
                score = report.alignment_score
                if score >= 0.7:
                    return "aligned"
                elif score >= 0.4:
                    return "drifted"
                else:
                    return "orphaned"
        except Exception:
            logger.debug("Failed to assess goal alignment", exc_info=True)

        return "unknown"

    def _assess_outcome_progress(self, decision: Any) -> float:
        """Check progress on goals this decision supports."""
        if not self._outcome_tracking or not hasattr(decision, "goal_refs"):
            return 0.0

        if not decision.goal_refs:
            return 0.0

        try:
            total = 0.0
            count = 0
            for goal_id in decision.goal_refs:
                progress = self._outcome_tracking.completion(goal_id)
                total += progress
                count += 1
            return total / count if count > 0 else 0.0
        except Exception:
            logger.debug("Failed to assess outcome progress", exc_info=True)
            return 0.0

    def _collect_risk_factors(
        self,
        ah: dict[str, Any],
        ga: str,
        op: float,
    ) -> list[str]:
        """Collect risk factors from all assessments."""
        risks: list[str] = []
        if ah.get("invalidated", 0) > 0:
            risks.append(
                f"{ah['invalidated']} of {ah['total']} assumptions invalidated"
            )
        if ah.get("unknown", 0) > 0 and ah.get("total", 0) > 0:
            unknown_ratio = ah["unknown"] / ah["total"]
            if unknown_ratio > 0.5:
                risks.append("majority of assumptions untracked")
        if ga == "drifted":
            risks.append("goal alignment drifted")
        elif ga == "orphaned":
            risks.append("goals orphaned — no active work")
        if op < 0.1 and op >= 0.0:
            risks.append("near-zero outcome progress")
        return risks

    def _classify(
        self,
        ah: dict[str, Any],
        ga: str,
        op: float,
        risks: list[str],
    ) -> tuple[str, str]:
        """Deterministic classification into validity status + recommendation."""
        total_asm = ah.get("total", 0)
        invalidated = ah.get("invalidated", 0)

        if total_asm > 0 and invalidated == total_asm:
            return ValidityStatus.INVALID.value, "invalidate"

        if total_asm > 0 and invalidated > 0:
            ratio = invalidated / total_asm
            if ratio >= 0.5:
                return ValidityStatus.INVALID.value, "supersede"
            return ValidityStatus.AT_RISK.value, "review"

        if ga == "orphaned":
            return ValidityStatus.AT_RISK.value, "review"

        if ga == "drifted" or len(risks) >= 2:
            return ValidityStatus.WATCH.value, "monitor"

        if len(risks) == 1:
            return ValidityStatus.WATCH.value, "monitor"

        return ValidityStatus.VALID.value, "maintain"
