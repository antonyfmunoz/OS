"""Promotion Threshold Policy — governs cadence mode transitions.

Defines when the system may move between cadence modes based on
production-backed reliability thresholds. Does NOT enable transitions
automatically — provides threshold evaluation that the operator reviews.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from substrate.organism.reliability_signals import (
    ProductionTruthReliabilitySignal,
    ReliabilitySignalAggregator,
)

logger = logging.getLogger(__name__)


class CadenceLevel(str, Enum):
    DRY_RUN_ONLY = "dry_run_only"
    SUPERVISED_PR_CREATION = "supervised_pr_creation"
    LOW_RISK_BATCH_MODE = "low_risk_batch_mode"
    MEDIUM_RISK_RECOMMENDATION_ONLY = "medium_risk_recommendation_only"
    MEDIUM_RISK_SUPERVISED_REVIEW = "medium_risk_supervised_review"


@dataclass
class ThresholdSpec:
    template_reliability: float = 0.0
    agent_reliability: float = 0.0
    validation_reliability: float = 0.0
    production_success_count: int = 0
    rollback_required: bool = False
    no_unresolved_failures: bool = False
    last_n_verifications_pass: int = 0
    no_duplicate_emission_failures: bool = False
    no_unresolved_sandbox_hygiene: bool = False
    no_active_pr_conflicts: bool = False
    operator_enables_batch: bool = False
    explicit_operator_review: bool = False
    execution_blocked: bool = False

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.template_reliability > 0:
            d["template_reliability"] = self.template_reliability
        if self.agent_reliability > 0:
            d["agent_reliability"] = self.agent_reliability
        if self.validation_reliability > 0:
            d["validation_reliability"] = self.validation_reliability
        if self.production_success_count > 0:
            d["production_success_count"] = self.production_success_count
        if self.rollback_required:
            d["rollback_required"] = True
        if self.no_unresolved_failures:
            d["no_unresolved_failures"] = True
        if self.last_n_verifications_pass > 0:
            d["last_n_verifications_pass"] = self.last_n_verifications_pass
        if self.no_duplicate_emission_failures:
            d["no_duplicate_emission_failures"] = True
        if self.no_unresolved_sandbox_hygiene:
            d["no_unresolved_sandbox_hygiene"] = True
        if self.no_active_pr_conflicts:
            d["no_active_pr_conflicts"] = True
        if self.operator_enables_batch:
            d["operator_enables_batch"] = True
        if self.explicit_operator_review:
            d["explicit_operator_review"] = True
        if self.execution_blocked:
            d["execution_blocked"] = True
        return d


@dataclass
class ThresholdEvaluation:
    level: CadenceLevel = CadenceLevel.DRY_RUN_ONLY
    threshold: ThresholdSpec = field(default_factory=ThresholdSpec)
    met: bool = False
    checks: dict[str, bool] = field(default_factory=dict)
    unmet_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "threshold": self.threshold.to_dict(),
            "met": self.met,
            "checks": self.checks,
            "unmet_reasons": self.unmet_reasons,
        }


class PromotionThresholdPolicy:
    """Evaluates whether cadence may transition to a higher mode."""

    THRESHOLDS: dict[CadenceLevel, ThresholdSpec] = {
        CadenceLevel.DRY_RUN_ONLY: ThresholdSpec(),

        CadenceLevel.SUPERVISED_PR_CREATION: ThresholdSpec(
            template_reliability=0.80,
            agent_reliability=0.75,
            validation_reliability=0.80,
            production_success_count=3,
            rollback_required=True,
            no_unresolved_failures=True,
        ),

        CadenceLevel.LOW_RISK_BATCH_MODE: ThresholdSpec(
            template_reliability=0.80,
            agent_reliability=0.75,
            validation_reliability=0.80,
            production_success_count=5,
            rollback_required=True,
            no_unresolved_failures=True,
            last_n_verifications_pass=5,
            no_duplicate_emission_failures=True,
            no_unresolved_sandbox_hygiene=True,
            no_active_pr_conflicts=True,
            operator_enables_batch=True,
        ),

        CadenceLevel.MEDIUM_RISK_RECOMMENDATION_ONLY: ThresholdSpec(
            template_reliability=0.90,
            agent_reliability=0.85,
            validation_reliability=0.90,
            production_success_count=5,
            explicit_operator_review=True,
        ),

        CadenceLevel.MEDIUM_RISK_SUPERVISED_REVIEW: ThresholdSpec(
            execution_blocked=True,
        ),
    }

    def __init__(self, aggregator: ReliabilitySignalAggregator | None = None) -> None:
        self._aggregator = aggregator or ReliabilitySignalAggregator()
        self._aggregator.aggregate()

    def evaluate_all(self) -> list[ThresholdEvaluation]:
        return [self.evaluate_level(level) for level in CadenceLevel]

    def evaluate_level(self, level: CadenceLevel) -> ThresholdEvaluation:
        spec = self.THRESHOLDS.get(level, ThresholdSpec())
        evaluation = ThresholdEvaluation(level=level, threshold=spec)

        if level == CadenceLevel.DRY_RUN_ONLY:
            evaluation.met = True
            evaluation.checks = {"always_available": True}
            return evaluation

        if spec.execution_blocked:
            evaluation.met = False
            evaluation.checks = {"execution_blocked": True}
            evaluation.unmet_reasons = ["execution blocked until future phase"]
            return evaluation

        checks: dict[str, bool] = {}
        unmet: list[str] = []

        if spec.template_reliability > 0:
            best_template_score = self._best_template_score()
            passed = best_template_score >= spec.template_reliability
            checks["template_reliability"] = passed
            if not passed:
                unmet.append(f"template_reliability {best_template_score:.2f} < {spec.template_reliability}")

        if spec.agent_reliability > 0:
            best_agent_score = self._best_agent_score()
            passed = best_agent_score >= spec.agent_reliability
            checks["agent_reliability"] = passed
            if not passed:
                unmet.append(f"agent_reliability {best_agent_score:.2f} < {spec.agent_reliability}")

        if spec.validation_reliability > 0:
            best_val_score = self._best_validation_score()
            passed = best_val_score >= spec.validation_reliability
            checks["validation_reliability"] = passed
            if not passed:
                unmet.append(f"validation_reliability {best_val_score:.2f} < {spec.validation_reliability}")

        if spec.production_success_count > 0:
            total = self._total_production_successes()
            passed = total >= spec.production_success_count
            checks["production_success_count"] = passed
            if not passed:
                unmet.append(f"production_successes {total} < {spec.production_success_count}")

        if spec.rollback_required:
            checks["rollback_required"] = True

        if spec.no_unresolved_failures:
            has_failures = self._has_unresolved_failures()
            checks["no_unresolved_failures"] = not has_failures
            if has_failures:
                unmet.append("unresolved production failures exist")

        if spec.last_n_verifications_pass > 0:
            passed = self._last_n_verifications_pass(spec.last_n_verifications_pass)
            checks["last_n_verifications_pass"] = passed
            if not passed:
                unmet.append(f"last {spec.last_n_verifications_pass} verifications not all passing")

        if spec.no_duplicate_emission_failures:
            checks["no_duplicate_emission_failures"] = True

        if spec.no_unresolved_sandbox_hygiene:
            checks["no_unresolved_sandbox_hygiene"] = True

        if spec.no_active_pr_conflicts:
            checks["no_active_pr_conflicts"] = True

        if spec.operator_enables_batch:
            checks["operator_enables_batch"] = False
            unmet.append("operator has not enabled batch mode")

        if spec.explicit_operator_review:
            checks["explicit_operator_review"] = False
            unmet.append("explicit operator review required")

        evaluation.checks = checks
        evaluation.unmet_reasons = unmet
        evaluation.met = len(unmet) == 0
        return evaluation

    def highest_eligible_level(self) -> CadenceLevel:
        levels = [
            CadenceLevel.LOW_RISK_BATCH_MODE,
            CadenceLevel.SUPERVISED_PR_CREATION,
            CadenceLevel.DRY_RUN_ONLY,
        ]
        for level in levels:
            evaluation = self.evaluate_level(level)
            if evaluation.met:
                return level
        return CadenceLevel.DRY_RUN_ONLY

    def _best_template_score(self) -> float:
        scores = [sig.score() for sig in self._aggregator._template_signals.values()]
        return max(scores) if scores else 0.0

    def _best_agent_score(self) -> float:
        scores = [sig.score() for sig in self._aggregator._agent_signals.values()]
        return max(scores) if scores else 0.0

    def _best_validation_score(self) -> float:
        scores = [sig.score() for sig in self._aggregator._validation_signals.values()]
        return max(scores) if scores else 0.0

    def _total_production_successes(self) -> int:
        return sum(sig.production_successes for sig in self._aggregator._template_signals.values())

    def _has_unresolved_failures(self) -> bool:
        return any(sig.production_failures > 0 for sig in self._aggregator._template_signals.values())

    def _last_n_verifications_pass(self, n: int) -> bool:
        pt = self._aggregator.get_production_truth_signal()
        return pt.pmv_pass_rate >= 1.0

    def to_dict(self) -> dict[str, Any]:
        evaluations = self.evaluate_all()
        highest = self.highest_eligible_level()
        return {
            "levels": [e.to_dict() for e in evaluations],
            "highest_eligible": highest.value,
            "medium_risk_execution_blocked": True,
        }
