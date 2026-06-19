"""C15.1 — Organism Coordination Engine.

Cross-system synchronization detection. Identifies when subsystems
are misaligned and surfaces coordination issues.

Named OrganismCoordinationEngine (not CoordinationEngine) because
substrate/control_plane/coordination/coordination_engine.py already
defines CoordinationEngine for task assignment.

No execution authority. No mutation authority. No direct mutation of
goals, work, decisions, memory, capabilities, allocations, or approvals.
"""
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ────────────────────────────────────────────────────────────


class CoordinationIssueType(str, Enum):
    GOAL_CONFLICT = "goal_conflict"
    RESOURCE_CONFLICT = "resource_conflict"
    PREDICTION_CONFLICT = "prediction_conflict"
    CAPABILITY_BOTTLENECK = "capability_bottleneck"
    EXECUTION_BOTTLENECK = "execution_bottleneck"
    LEARNING_GAP = "learning_gap"


class CoordinationHealth(str, Enum):
    SYNCHRONIZED = "synchronized"
    ALIGNED = "aligned"
    DRIFTING = "drifting"
    FRAGMENTED = "fragmented"
    CRITICAL = "critical"


@dataclass
class CoordinationIssue:
    issue_id: str = ""
    issue_type: str = CoordinationIssueType.GOAL_CONFLICT.value
    severity: str = "low"
    affected_subsystems: list[str] = field(default_factory=list)
    description: str = ""
    recommendation: str = ""
    detected_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CoordinationSnapshot:
    coordination_health: str = CoordinationHealth.ALIGNED.value
    issues: list[dict[str, Any]] = field(default_factory=list)
    subsystem_alignment: dict[str, str] = field(default_factory=dict)
    synchronization_score: float = 0.5
    bottleneck_count: int = 0
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Health Score Mapping ─────────────────────────────────────────────

_HEALTH_SCORE: dict[str, float] = {
    # Best tier
    "coherent": 1.0, "synchronized": 1.0, "optimized": 1.0,
    "thriving": 1.0, "high_confidence": 1.0,
    # Good tier
    "aligned": 0.7, "focused": 0.7, "healthy": 0.7,
    "growing": 0.7, "stable": 0.7, "balanced": 0.7,
    # Degraded tier
    "strained": 0.4, "fragmented": 0.4, "drifting": 0.4,
    "stagnant": 0.4, "uncertain": 0.4, "constrained": 0.4,
    # Bad tier
    "overcommitted": 0.2, "decaying": 0.2, "volatile": 0.2,
    "stalled": 0.2,
    # Critical tier
    "critical": 0.1, "blind": 0.1,
}


def _health_to_score(health_str: str) -> float:
    return _HEALTH_SCORE.get(health_str, 0.5)


def _issue_id(issue_type: str) -> str:
    raw = f"{issue_type}:{time.time()}"
    return f"coord-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


# ── Runtime ──────────────────────────────────────────────────────────


class OrganismCoordinationEngine:
    """Cross-system synchronization detection.

    Composes the governance runtime (C15.0), all portfolio runtimes,
    and resource/tradeoff engines to detect coordination failures.
    """

    def __init__(
        self,
        governance_runtime: Any | None = None,
        executive_portfolio: Any | None = None,
        prediction_portfolio: Any | None = None,
        work_portfolio: Any | None = None,
        learning_portfolio: Any | None = None,
        capability_portfolio: Any | None = None,
        resource_allocation: Any | None = None,
        tradeoff_engine: Any | None = None,
    ) -> None:
        self._governance_runtime = governance_runtime
        self._executive_portfolio = executive_portfolio
        self._prediction_portfolio = prediction_portfolio
        self._work_portfolio = work_portfolio
        self._learning_portfolio = learning_portfolio
        self._capability_portfolio = capability_portfolio
        self._resource_allocation = resource_allocation
        self._tradeoff_engine = tradeoff_engine

    # ── Lazy Properties ──────────────────────────────────────────────

    @property
    def _governance(self) -> Any:
        if self._governance_runtime is None:
            try:
                from substrate.organism.governance_runtime import GovernanceRuntime

                self._governance_runtime = GovernanceRuntime()
            except Exception:
                logger.debug("Failed to init GovernanceRuntime", exc_info=True)
        return self._governance_runtime

    @property
    def _executive(self) -> Any:
        if self._executive_portfolio is None:
            try:
                from substrate.organism.executive_portfolio_runtime import (
                    ExecutivePortfolioRuntime,
                )

                self._executive_portfolio = ExecutivePortfolioRuntime()
            except Exception:
                logger.debug("Failed to init ExecutivePortfolioRuntime", exc_info=True)
        return self._executive_portfolio

    @property
    def _prediction(self) -> Any:
        if self._prediction_portfolio is None:
            try:
                from substrate.organism.prediction_portfolio_runtime import (
                    PredictionPortfolioRuntime,
                )

                self._prediction_portfolio = PredictionPortfolioRuntime()
            except Exception:
                logger.debug("Failed to init PredictionPortfolioRuntime", exc_info=True)
        return self._prediction_portfolio

    @property
    def _work(self) -> Any:
        if self._work_portfolio is None:
            try:
                from substrate.organism.work_portfolio_runtime import (
                    WorkPortfolioRuntime,
                )

                self._work_portfolio = WorkPortfolioRuntime()
            except Exception:
                logger.debug("Failed to init WorkPortfolioRuntime", exc_info=True)
        return self._work_portfolio

    @property
    def _learning(self) -> Any:
        if self._learning_portfolio is None:
            try:
                from substrate.organism.learning_portfolio_runtime import (
                    LearningPortfolioRuntime,
                )

                self._learning_portfolio = LearningPortfolioRuntime()
            except Exception:
                logger.debug("Failed to init LearningPortfolioRuntime", exc_info=True)
        return self._learning_portfolio

    @property
    def _capability(self) -> Any:
        if self._capability_portfolio is None:
            try:
                from substrate.organism.capability_portfolio_runtime import (
                    CapabilityPortfolioRuntime,
                )

                self._capability_portfolio = CapabilityPortfolioRuntime()
            except Exception:
                logger.debug("Failed to init CapabilityPortfolioRuntime", exc_info=True)
        return self._capability_portfolio

    @property
    def _allocation(self) -> Any:
        if self._resource_allocation is None:
            try:
                from substrate.organism.resource_allocation_runtime import (
                    ResourceAllocationRuntime,
                )

                self._resource_allocation = ResourceAllocationRuntime()
            except Exception:
                logger.debug("Failed to init ResourceAllocationRuntime", exc_info=True)
        return self._resource_allocation

    @property
    def _tradeoff(self) -> Any:
        if self._tradeoff_engine is None:
            try:
                from substrate.organism.tradeoff_intelligence_engine import (
                    TradeoffIntelligenceEngine,
                )

                self._tradeoff_engine = TradeoffIntelligenceEngine()
            except Exception:
                logger.debug("Failed to init TradeoffIntelligenceEngine", exc_info=True)
        return self._tradeoff_engine

    # ── Public API ───────────────────────────────────────────────────

    def detect_issues(self) -> list[CoordinationIssue]:
        """Detect all coordination issues across subsystems."""
        issues: list[CoordinationIssue] = []
        issues.extend(self._detect_goal_conflicts())
        issues.extend(self._detect_resource_conflicts())
        issues.extend(self._detect_prediction_conflicts())
        issues.extend(self._detect_capability_bottlenecks())
        issues.extend(self._detect_execution_bottlenecks())
        issues.extend(self._detect_learning_gaps())
        return issues

    def subsystem_alignment(self) -> dict[str, str]:
        """Health status of each subsystem."""
        alignment: dict[str, str] = {}
        for name, subsys in self._subsystem_list():
            if subsys is None:
                alignment[name] = "unknown"
                continue
            try:
                h = subsys.health() if hasattr(subsys, "health") else None
                alignment[name] = h.value if hasattr(h, "value") else str(h) if h else "unknown"
            except Exception:
                alignment[name] = "unknown"
        return alignment

    def synchronization_score(self) -> float:
        """Weighted average of subsystem health scores (0.0-1.0)."""
        alignment = self.subsystem_alignment()
        if not alignment:
            return 0.5

        total = 0.0
        count = 0
        for health_str in alignment.values():
            total += _health_to_score(health_str)
            count += 1

        return round(total / count, 4) if count > 0 else 0.5

    def health(self) -> CoordinationHealth:
        """Classify coordination health."""
        score = self.synchronization_score()
        issues = self.detect_issues()

        has_critical = any(i.severity == "critical" for i in issues)
        issue_count = len(issues)

        if has_critical or score < 0.3:
            return CoordinationHealth.CRITICAL
        if score < 0.5 or issue_count >= 6:
            return CoordinationHealth.FRAGMENTED
        if score < 0.7 or issue_count >= 3:
            return CoordinationHealth.DRIFTING
        if issue_count > 0:
            return CoordinationHealth.ALIGNED
        return CoordinationHealth.SYNCHRONIZED

    def snapshot(self) -> CoordinationSnapshot:
        """Full coordination snapshot."""
        issues = self.detect_issues()
        bottlenecks = [
            i for i in issues
            if i.issue_type in (
                CoordinationIssueType.CAPABILITY_BOTTLENECK.value,
                CoordinationIssueType.EXECUTION_BOTTLENECK.value,
            )
        ]
        return CoordinationSnapshot(
            coordination_health=self.health().value,
            issues=[i.to_dict() for i in issues],
            subsystem_alignment=self.subsystem_alignment(),
            synchronization_score=self.synchronization_score(),
            bottleneck_count=len(bottlenecks),
            generated_at=time.time(),
        )

    def summary(self) -> dict[str, Any]:
        """Quick summary dict."""
        issues = self.detect_issues()
        return {
            "coordination_health": self.health().value,
            "synchronization_score": self.synchronization_score(),
            "issue_count": len(issues),
            "subsystem_alignment": self.subsystem_alignment(),
        }

    # ── Issue Detectors ──────────────────────────────────────────────

    def _detect_goal_conflicts(self) -> list[CoordinationIssue]:
        """Goals misaligned with resource allocations."""
        issues: list[CoordinationIssue] = []
        try:
            alloc = self._allocation
            gov = self._governance
            if alloc is None:
                return issues

            unallocated = alloc.unallocated_goals() if hasattr(alloc, "unallocated_goals") else []
            if len(unallocated) > 3:
                issues.append(CoordinationIssue(
                    issue_id=_issue_id("goal_conflict"),
                    issue_type=CoordinationIssueType.GOAL_CONFLICT.value,
                    severity="medium" if len(unallocated) < 6 else "high",
                    affected_subsystems=["goals", "executive"],
                    description=f"{len(unallocated)} goals have no resource allocation",
                    recommendation="Review resource allocation for orphaned goals",
                    detected_at=time.time(),
                ))
        except Exception:
            logger.debug("Error detecting goal conflicts", exc_info=True)
        return issues

    def _detect_resource_conflicts(self) -> list[CoordinationIssue]:
        """Resource contention from tradeoff engine."""
        issues: list[CoordinationIssue] = []
        try:
            tradeoff = self._tradeoff
            if tradeoff is None:
                return issues

            contention = tradeoff.contention_map() if hasattr(tradeoff, "contention_map") else {}
            for resource, targets in contention.items():
                if isinstance(targets, list) and len(targets) >= 3:
                    issues.append(CoordinationIssue(
                        issue_id=_issue_id("resource_conflict"),
                        issue_type=CoordinationIssueType.RESOURCE_CONFLICT.value,
                        severity="medium" if len(targets) < 5 else "high",
                        affected_subsystems=["executive", "work"],
                        description=f"Resource '{resource}' contended by {len(targets)} targets",
                        recommendation=f"Prioritize targets for {resource} using tradeoff analysis",
                        detected_at=time.time(),
                    ))
        except Exception:
            logger.debug("Error detecting resource conflicts", exc_info=True)
        return issues

    def _detect_prediction_conflicts(self) -> list[CoordinationIssue]:
        """Prediction drift not reflected in work priorities."""
        issues: list[CoordinationIssue] = []
        try:
            pred = self._prediction
            work = self._work
            if pred is None or work is None:
                return issues

            pred_drift = pred.drift_warnings() if hasattr(pred, "drift_warnings") else []
            work_drift = (
                work.detect_drift() if hasattr(work, "detect_drift")
                else work.drift_warnings() if hasattr(work, "drift_warnings")
                else []
            )

            if len(pred_drift) > 0 and len(work_drift) == 0:
                issues.append(CoordinationIssue(
                    issue_id=_issue_id("prediction_conflict"),
                    issue_type=CoordinationIssueType.PREDICTION_CONFLICT.value,
                    severity="medium",
                    affected_subsystems=["prediction", "work"],
                    description=f"Prediction has {len(pred_drift)} drift warnings but work shows no corresponding drift",
                    recommendation="Review work priorities against prediction risk signals",
                    detected_at=time.time(),
                ))
        except Exception:
            logger.debug("Error detecting prediction conflicts", exc_info=True)
        return issues

    def _detect_capability_bottlenecks(self) -> list[CoordinationIssue]:
        """Capability gaps blocking work items."""
        issues: list[CoordinationIssue] = []
        try:
            cap = self._capability
            work = self._work
            if cap is None or work is None:
                return issues

            cap_health = cap.health() if hasattr(cap, "health") else None
            cap_str = cap_health.value if hasattr(cap_health, "value") else str(cap_health) if cap_health else ""
            at_risk = work.at_risk_work() if hasattr(work, "at_risk_work") else []

            if cap_str in ("constrained", "stalled", "critical", "declining") and len(at_risk) > 0:
                issues.append(CoordinationIssue(
                    issue_id=_issue_id("capability_bottleneck"),
                    issue_type=CoordinationIssueType.CAPABILITY_BOTTLENECK.value,
                    severity="high",
                    affected_subsystems=["capability", "work"],
                    description=f"Capability health is {cap_str} with {len(at_risk)} at-risk work items",
                    recommendation="Build capability gaps before adding more work",
                    detected_at=time.time(),
                ))
        except Exception:
            logger.debug("Error detecting capability bottlenecks", exc_info=True)
        return issues

    def _detect_execution_bottlenecks(self) -> list[CoordinationIssue]:
        """At-risk work with no resource allocation."""
        issues: list[CoordinationIssue] = []
        try:
            work = self._work
            alloc = self._allocation
            if work is None:
                return issues

            at_risk = work.at_risk_work() if hasattr(work, "at_risk_work") else []
            if len(at_risk) > 3:
                budgets = alloc.budgets() if alloc and hasattr(alloc, "budgets") else []
                overcommitted = [
                    b for b in budgets
                    if hasattr(b, "overcommitted") and b.overcommitted
                ]

                if len(overcommitted) > 0:
                    issues.append(CoordinationIssue(
                        issue_id=_issue_id("execution_bottleneck"),
                        issue_type=CoordinationIssueType.EXECUTION_BOTTLENECK.value,
                        severity="high",
                        affected_subsystems=["work", "executive"],
                        description=f"{len(at_risk)} at-risk work items with {len(overcommitted)} overcommitted resource budgets",
                        recommendation="Reduce work in progress or increase resource allocation",
                        detected_at=time.time(),
                    ))
        except Exception:
            logger.debug("Error detecting execution bottlenecks", exc_info=True)
        return issues

    def _detect_learning_gaps(self) -> list[CoordinationIssue]:
        """Lessons not feeding back into decisions."""
        issues: list[CoordinationIssue] = []
        try:
            learning = self._learning
            if learning is None:
                return issues

            learning_health = learning.health() if hasattr(learning, "health") else None
            l_str = learning_health.value if hasattr(learning_health, "value") else str(learning_health) if learning_health else ""
            compounding = learning.compounding_score() if hasattr(learning, "compounding_score") else 0.5

            if l_str in ("stagnant", "declining", "critical") and compounding < 0.3:
                issues.append(CoordinationIssue(
                    issue_id=_issue_id("learning_gap"),
                    issue_type=CoordinationIssueType.LEARNING_GAP.value,
                    severity="medium",
                    affected_subsystems=["learning", "decisions"],
                    description=f"Learning health {l_str} with compounding score {compounding:.2f}",
                    recommendation="Review lesson extraction and decision feedback loop",
                    detected_at=time.time(),
                ))
        except Exception:
            logger.debug("Error detecting learning gaps", exc_info=True)
        return issues

    # ── Helpers ───────────────────────────────────────────────────────

    def _subsystem_list(self) -> list[tuple[str, Any]]:
        return [
            ("governance", self._governance),
            ("executive", self._executive),
            ("prediction", self._prediction),
            ("work", self._work),
            ("learning", self._learning),
            ("capability", self._capability),
        ]
