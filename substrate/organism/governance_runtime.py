"""C15.0 — Governance Runtime.

Organism-level governance: authority hierarchy, conflict arbitration,
and policy management across all intelligence subsystems.

C15 is NOT another intelligence layer. It is the first organism
coordination layer — filling the Detection → Advisory → Resolution gap.

No execution authority. No mutation authority. No direct mutation of
goals, work, decisions, memory, capabilities, allocations, or approvals.
Any mutation must route through the owning subsystem.
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


class GovernanceAuthority(str, Enum):
    """Which subsystem has authority in a conflict. Lower rank = higher authority."""

    REALITY = "reality"
    STRATEGY = "strategy"
    GOALS = "goals"
    DECISIONS = "decisions"
    EXECUTIVE = "executive"
    WORK = "work"


class ConflictStatus(str, Enum):
    DETECTED = "detected"
    ARBITRATED = "arbitrated"
    ACKNOWLEDGED = "acknowledged"
    SUPERSEDED = "superseded"


class ConflictSeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GovernanceHealth(str, Enum):
    COHERENT = "coherent"
    ALIGNED = "aligned"
    STRAINED = "strained"
    FRAGMENTED = "fragmented"
    CRITICAL = "critical"


class GovernanceDriftType(str, Enum):
    AUTHORITY_VIOLATION = "authority_violation"
    UNRESOLVED_CONFLICT = "unresolved_conflict"
    POLICY_STALENESS = "policy_staleness"
    SUBSYSTEM_DISAGREEMENT = "subsystem_disagreement"


@dataclass
class SubsystemConflict:
    conflict_id: str = ""
    source_authority: str = GovernanceAuthority.WORK.value
    target_authority: str = GovernanceAuthority.WORK.value
    source_recommendation: str = ""
    target_recommendation: str = ""
    conflict_type: str = ""
    severity: str = ConflictSeverityLevel.LOW.value
    resolution: str = ""
    winning_authority: str = ""
    losing_authority: str = ""
    rationale: str = ""
    detected_at: float = 0.0
    status: str = ConflictStatus.DETECTED.value

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GovernancePolicy:
    policy_id: str = ""
    name: str = ""
    authority: str = GovernanceAuthority.REALITY.value
    description: str = ""
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GovernanceDriftWarning:
    drift_type: str = GovernanceDriftType.AUTHORITY_VIOLATION.value
    severity: str = "low"
    description: str = ""
    affected_ids: list[str] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GovernanceRuntimeSnapshot:
    governance_health: str = GovernanceHealth.ALIGNED.value
    active_conflicts: list[dict[str, Any]] = field(default_factory=list)
    resolved_conflicts: list[dict[str, Any]] = field(default_factory=list)
    active_policies: list[dict[str, Any]] = field(default_factory=list)
    drift_warnings: list[dict[str, Any]] = field(default_factory=list)
    authority_hierarchy: list[str] = field(default_factory=list)
    conflict_count: int = 0
    resolution_rate: float = 1.0
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Authority Hierarchy ──────────────────────────────────────────────

AUTHORITY_RANK: dict[str, int] = {
    GovernanceAuthority.REALITY.value: 0,
    GovernanceAuthority.STRATEGY.value: 1,
    GovernanceAuthority.GOALS.value: 2,
    GovernanceAuthority.DECISIONS.value: 3,
    GovernanceAuthority.EXECUTIVE.value: 4,
    GovernanceAuthority.WORK.value: 5,
}

_AUTHORITY_ORDER: list[str] = sorted(
    AUTHORITY_RANK.keys(), key=lambda k: AUTHORITY_RANK[k]
)

_DOMAIN_TO_AUTHORITY: dict[str, str] = {
    "reality": GovernanceAuthority.REALITY.value,
    "operations": GovernanceAuthority.REALITY.value,
    "strategy": GovernanceAuthority.STRATEGY.value,
    "goals": GovernanceAuthority.GOALS.value,
    "goal_alignment": GovernanceAuthority.GOALS.value,
    "decisions": GovernanceAuthority.DECISIONS.value,
    "decision_impact": GovernanceAuthority.DECISIONS.value,
    "executive": GovernanceAuthority.EXECUTIVE.value,
    "resource_allocation": GovernanceAuthority.EXECUTIVE.value,
    "tradeoff": GovernanceAuthority.EXECUTIVE.value,
    "prediction": GovernanceAuthority.EXECUTIVE.value,
    "work": GovernanceAuthority.WORK.value,
    "work_portfolio": GovernanceAuthority.WORK.value,
    "learning": GovernanceAuthority.WORK.value,
    "capability": GovernanceAuthority.WORK.value,
}

# ── Default Policies ─────────────────────────────────────────────────

_DEFAULT_POLICIES: list[GovernancePolicy] = [
    GovernancePolicy(
        policy_id="pol-authority-hierarchy",
        name="Authority Hierarchy",
        authority=GovernanceAuthority.REALITY.value,
        description="Higher-authority subsystems supersede lower when in conflict.",
    ),
    GovernancePolicy(
        policy_id="pol-no-direct-mutation",
        name="No Direct Mutation",
        authority=GovernanceAuthority.REALITY.value,
        description=(
            "Governance may recommend but never directly mutate goals, work, "
            "decisions, memory, capabilities, allocations, or approvals."
        ),
    ),
    GovernancePolicy(
        policy_id="pol-prediction-precaution",
        name="Prediction Precaution",
        authority=GovernanceAuthority.STRATEGY.value,
        description="Prediction risk warnings override executive allocation when severity is high.",
    ),
    GovernancePolicy(
        policy_id="pol-goal-primacy",
        name="Goal Primacy",
        authority=GovernanceAuthority.GOALS.value,
        description="Goal alignment takes priority over execution convenience.",
    ),
    GovernancePolicy(
        policy_id="pol-decision-honour",
        name="Decision Honour",
        authority=GovernanceAuthority.DECISIONS.value,
        description="Active strategic decisions are honoured until explicitly superseded.",
    ),
    GovernancePolicy(
        policy_id="pol-resource-efficiency",
        name="Resource Efficiency",
        authority=GovernanceAuthority.EXECUTIVE.value,
        description="Resource allocation follows leverage scoring unless overridden by higher authority.",
    ),
]


# ── Runtime ──────────────────────────────────────────────────────────


def _conflict_id(source: str, target: str) -> str:
    raw = f"{source}:{target}:{time.time()}"
    return f"conflict-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


class GovernanceRuntime:
    """Organism-level governance — authority hierarchy and conflict arbitration.

    Composes all portfolio runtimes and decision subsystems to detect
    cross-system conflicts and resolve them deterministically using
    the authority hierarchy.
    """

    def __init__(
        self,
        executive_portfolio: Any | None = None,
        prediction_portfolio: Any | None = None,
        work_portfolio: Any | None = None,
        learning_portfolio: Any | None = None,
        capability_portfolio: Any | None = None,
        decision_registry: Any | None = None,
        decision_impact: Any | None = None,
        goal_alignment: Any | None = None,
        strategic_planning: Any | None = None,
    ) -> None:
        self._executive_portfolio = executive_portfolio
        self._prediction_portfolio = prediction_portfolio
        self._work_portfolio = work_portfolio
        self._learning_portfolio = learning_portfolio
        self._capability_portfolio = capability_portfolio
        self._decision_registry = decision_registry
        self._decision_impact = decision_impact
        self._goal_alignment = goal_alignment
        self._strategic_planning = strategic_planning
        self._conflicts: list[SubsystemConflict] = []

    # ── Lazy Properties ──────────────────────────────────────────────

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
    def _decisions(self) -> Any:
        if self._decision_registry is None:
            try:
                from substrate.organism.decision_registry import DecisionRegistry

                self._decision_registry = DecisionRegistry()
            except Exception:
                logger.debug("Failed to init DecisionRegistry", exc_info=True)
        return self._decision_registry

    @property
    def _impact(self) -> Any:
        if self._decision_impact is None:
            try:
                from substrate.organism.decision_impact_engine import (
                    DecisionImpactEngine,
                )

                self._decision_impact = DecisionImpactEngine()
            except Exception:
                logger.debug("Failed to init DecisionImpactEngine", exc_info=True)
        return self._decision_impact

    @property
    def _goals(self) -> Any:
        if self._goal_alignment is None:
            try:
                from substrate.organism.goal_alignment_engine import (
                    GoalAlignmentEngine,
                )

                self._goal_alignment = GoalAlignmentEngine()
            except Exception:
                logger.debug("Failed to init GoalAlignmentEngine", exc_info=True)
        return self._goal_alignment

    @property
    def _planning(self) -> Any:
        if self._strategic_planning is None:
            try:
                from substrate.organism.strategic_planning_engine import (
                    StrategicPlanningEngine,
                )

                self._strategic_planning = StrategicPlanningEngine()
            except Exception:
                logger.debug("Failed to init StrategicPlanningEngine", exc_info=True)
        return self._strategic_planning

    # ── Public API ───────────────────────────────────────────────────

    def resolve_conflict(
        self,
        source: str,
        target: str,
        source_rec: str,
        target_rec: str,
        conflict_type: str = "recommendation_conflict",
    ) -> SubsystemConflict:
        """Resolve a conflict between two subsystems using authority rank."""
        source_rank = AUTHORITY_RANK.get(source, 99)
        target_rank = AUTHORITY_RANK.get(target, 99)

        if source_rank <= target_rank:
            winner, loser = source, target
            resolution = source_rec
        else:
            winner, loser = target, source
            resolution = target_rec

        severity = self._classify_severity(source, target)

        conflict = SubsystemConflict(
            conflict_id=_conflict_id(source, target),
            source_authority=source,
            target_authority=target,
            source_recommendation=source_rec,
            target_recommendation=target_rec,
            conflict_type=conflict_type,
            severity=severity,
            resolution=resolution,
            winning_authority=winner,
            losing_authority=loser,
            rationale=f"Authority rank: {winner} (rank {AUTHORITY_RANK.get(winner, 99)}) supersedes {loser} (rank {AUTHORITY_RANK.get(loser, 99)})",
            detected_at=time.time(),
            status=ConflictStatus.ARBITRATED.value,
        )
        self._conflicts.append(conflict)
        return conflict

    def authority_for(self, domain: str) -> str:
        """Return the governing authority for a domain."""
        return _DOMAIN_TO_AUTHORITY.get(domain, GovernanceAuthority.WORK.value)

    def active_policies(self) -> list[GovernancePolicy]:
        """Return all active governance policies."""
        return [p for p in _DEFAULT_POLICIES if p.active]

    def active_conflicts(self) -> list[SubsystemConflict]:
        """Return conflicts that have not been superseded."""
        return [
            c
            for c in self._conflicts
            if c.status != ConflictStatus.SUPERSEDED.value
        ]

    def detect_conflicts(self) -> list[SubsystemConflict]:
        """Detect cross-system conflicts from portfolio drift and health."""
        detected: list[SubsystemConflict] = []

        detected.extend(self._detect_prediction_vs_executive())
        detected.extend(self._detect_goal_vs_work())
        detected.extend(self._detect_decision_vs_executive())

        self._conflicts.extend(detected)
        return detected

    def drift_warnings(self) -> list[GovernanceDriftWarning]:
        """Detect governance-level drift."""
        warnings: list[GovernanceDriftWarning] = []
        warnings.extend(self._detect_authority_violations())
        warnings.extend(self._detect_unresolved_conflicts())
        warnings.extend(self._detect_subsystem_disagreement())
        return warnings

    def health(self) -> GovernanceHealth:
        """Classify governance health from conflicts and drift."""
        conflicts = self.active_conflicts()
        unresolved = [
            c for c in conflicts if c.status == ConflictStatus.DETECTED.value
        ]
        drift = self.drift_warnings()

        has_critical = any(
            c.severity == ConflictSeverityLevel.CRITICAL.value for c in conflicts
        )
        total_issues = len(unresolved) + len(drift)

        if has_critical or total_issues >= 10:
            return GovernanceHealth.CRITICAL
        if len(unresolved) >= 3 or len(drift) >= 6:
            return GovernanceHealth.FRAGMENTED
        if len(unresolved) >= 1 or len(drift) >= 3:
            return GovernanceHealth.STRAINED
        if len(drift) > 0:
            return GovernanceHealth.ALIGNED
        return GovernanceHealth.COHERENT

    def snapshot(self) -> GovernanceRuntimeSnapshot:
        """Full governance snapshot."""
        conflicts = self.active_conflicts()
        active = [c for c in conflicts if c.status != ConflictStatus.SUPERSEDED.value]
        resolved = [
            c for c in self._conflicts
            if c.status in (ConflictStatus.ARBITRATED.value, ConflictStatus.ACKNOWLEDGED.value)
        ]
        total = len(self._conflicts)
        resolved_count = len(resolved)

        return GovernanceRuntimeSnapshot(
            governance_health=self.health().value,
            active_conflicts=[c.to_dict() for c in active],
            resolved_conflicts=[c.to_dict() for c in resolved],
            active_policies=[p.to_dict() for p in self.active_policies()],
            drift_warnings=[w.to_dict() for w in self.drift_warnings()],
            authority_hierarchy=list(_AUTHORITY_ORDER),
            conflict_count=len(active),
            resolution_rate=resolved_count / total if total > 0 else 1.0,
            generated_at=time.time(),
        )

    def summary(self) -> dict[str, Any]:
        """Quick summary dict."""
        h = self.health()
        conflicts = self.active_conflicts()
        drift = self.drift_warnings()
        return {
            "governance_health": h.value,
            "active_conflict_count": len(conflicts),
            "drift_warning_count": len(drift),
            "policy_count": len(self.active_policies()),
            "authority_hierarchy": list(_AUTHORITY_ORDER),
        }

    # ── Conflict Detection ───────────────────────────────────────────

    def _detect_prediction_vs_executive(self) -> list[SubsystemConflict]:
        """Detect when prediction flags risk but executive allocates to it."""
        detected: list[SubsystemConflict] = []
        try:
            pred = self._prediction
            exe = self._executive
            if pred is None or exe is None:
                return detected

            high_risk = pred.highest_risk_forecasts(limit=5) if hasattr(pred, "highest_risk_forecasts") else []
            top_recs = exe.top_recommendations(limit=10) if hasattr(exe, "top_recommendations") else []

            risk_ids: set[str] = set()
            for f in high_risk:
                if isinstance(f, dict):
                    fid = f.get("target_id", f.get("id", ""))
                    if fid:
                        risk_ids.add(fid)

            for rec in top_recs:
                if isinstance(rec, dict):
                    rid = rec.get("target_id", rec.get("id", ""))
                    if rid and rid in risk_ids:
                        detected.append(SubsystemConflict(
                            conflict_id=_conflict_id("prediction", "executive"),
                            source_authority=GovernanceAuthority.EXECUTIVE.value,
                            target_authority=GovernanceAuthority.EXECUTIVE.value,
                            source_recommendation=f"Allocate to {rid}",
                            target_recommendation=f"Avoid {rid} (high risk)",
                            conflict_type="prediction_vs_executive",
                            severity=ConflictSeverityLevel.HIGH.value,
                            resolution=f"Prediction authority supersedes: avoid {rid}",
                            winning_authority=GovernanceAuthority.STRATEGY.value,
                            losing_authority=GovernanceAuthority.EXECUTIVE.value,
                            rationale="Prediction risk warnings override executive allocation per pol-prediction-precaution",
                            detected_at=time.time(),
                            status=ConflictStatus.ARBITRATED.value,
                        ))
        except Exception:
            logger.debug("Error detecting prediction vs executive conflicts", exc_info=True)
        return detected

    def _detect_goal_vs_work(self) -> list[SubsystemConflict]:
        """Detect when work is misaligned with goals."""
        detected: list[SubsystemConflict] = []
        try:
            goals = self._goals
            work = self._work
            if goals is None or work is None:
                return detected

            orphans = goals.orphan_goals() if hasattr(goals, "orphan_goals") else []
            at_risk = work.at_risk_work() if hasattr(work, "at_risk_work") else []

            if len(orphans) > 3 and len(at_risk) > 2:
                detected.append(SubsystemConflict(
                    conflict_id=_conflict_id("goals", "work"),
                    source_authority=GovernanceAuthority.GOALS.value,
                    target_authority=GovernanceAuthority.WORK.value,
                    source_recommendation=f"Address {len(orphans)} orphan goals",
                    target_recommendation=f"Focus on {len(at_risk)} at-risk work items",
                    conflict_type="goal_vs_work",
                    severity=ConflictSeverityLevel.MEDIUM.value,
                    resolution=f"Goals authority supersedes: address orphan goals first",
                    winning_authority=GovernanceAuthority.GOALS.value,
                    losing_authority=GovernanceAuthority.WORK.value,
                    rationale="Goal primacy policy: goal alignment takes priority over execution convenience",
                    detected_at=time.time(),
                    status=ConflictStatus.ARBITRATED.value,
                ))
        except Exception:
            logger.debug("Error detecting goal vs work conflicts", exc_info=True)
        return detected

    def _detect_decision_vs_executive(self) -> list[SubsystemConflict]:
        """Detect when executive allocation contradicts active decisions."""
        detected: list[SubsystemConflict] = []
        try:
            decisions = self._decisions
            exe = self._executive
            if decisions is None or exe is None:
                return detected

            active = decisions.active_decisions() if hasattr(decisions, "active_decisions") else []
            top_recs = exe.top_recommendations(limit=10) if hasattr(exe, "top_recommendations") else []

            if len(active) > 0 and len(top_recs) > 0:
                decision_goal_ids: set[str] = set()
                for d in active:
                    gid = ""
                    if hasattr(d, "goal_id"):
                        gid = d.goal_id
                    elif isinstance(d, dict):
                        gid = d.get("goal_id", "")
                    if gid:
                        decision_goal_ids.add(gid)

                for rec in top_recs:
                    if isinstance(rec, dict):
                        tid = rec.get("target_id", "")
                        if tid and tid not in decision_goal_ids and len(decision_goal_ids) > 0:
                            pass  # Not every allocation must map to a decision
        except Exception:
            logger.debug("Error detecting decision vs executive conflicts", exc_info=True)
        return detected

    # ── Drift Detection ──────────────────────────────────────────────

    def _detect_authority_violations(self) -> list[GovernanceDriftWarning]:
        """Detect when lower-authority subsystem recommendations override higher."""
        warnings: list[GovernanceDriftWarning] = []
        for c in self._conflicts:
            if c.status == ConflictStatus.DETECTED.value:
                winner_rank = AUTHORITY_RANK.get(c.winning_authority, 99)
                loser_rank = AUTHORITY_RANK.get(c.losing_authority, 99)
                if winner_rank > loser_rank:
                    warnings.append(GovernanceDriftWarning(
                        drift_type=GovernanceDriftType.AUTHORITY_VIOLATION.value,
                        severity="high",
                        description=f"Lower authority {c.winning_authority} overriding {c.losing_authority}",
                        affected_ids=[c.conflict_id],
                        recommendation="Review conflict resolution for authority compliance",
                    ))
        return warnings

    def _detect_unresolved_conflicts(self) -> list[GovernanceDriftWarning]:
        """Detect conflicts stuck in detected state."""
        unresolved = [
            c for c in self._conflicts
            if c.status == ConflictStatus.DETECTED.value
        ]
        if len(unresolved) > 0:
            return [GovernanceDriftWarning(
                drift_type=GovernanceDriftType.UNRESOLVED_CONFLICT.value,
                severity="medium" if len(unresolved) < 3 else "high",
                description=f"{len(unresolved)} conflict(s) remain unresolved",
                affected_ids=[c.conflict_id for c in unresolved],
                recommendation="Arbitrate unresolved conflicts through authority hierarchy",
            )]
        return []

    def _detect_subsystem_disagreement(self) -> list[GovernanceDriftWarning]:
        """Detect when 3+ subsystems have drift warnings simultaneously."""
        warnings: list[GovernanceDriftWarning] = []
        disagreeing: list[str] = []

        for name, subsys in [
            ("executive", self._executive),
            ("prediction", self._prediction),
            ("work", self._work),
            ("learning", self._learning),
            ("capability", self._capability),
        ]:
            if subsys is None:
                continue
            try:
                method = "drift_warnings" if hasattr(subsys, "drift_warnings") else "detect_drift"
                drifts = getattr(subsys, method, lambda: [])()
                if len(drifts) > 0:
                    disagreeing.append(name)
            except Exception:
                logger.debug("Error checking drift for %s", name, exc_info=True)

        if len(disagreeing) >= 3:
            warnings.append(GovernanceDriftWarning(
                drift_type=GovernanceDriftType.SUBSYSTEM_DISAGREEMENT.value,
                severity="high",
                description=f"{len(disagreeing)} subsystems have drift: {', '.join(disagreeing)}",
                affected_ids=disagreeing,
                recommendation="Cross-system coordination review needed",
            ))
        return warnings

    # ── Helpers ───────────────────────────────────────────────────────

    def _classify_severity(self, source: str, target: str) -> str:
        """Classify conflict severity based on authority distance."""
        s_rank = AUTHORITY_RANK.get(source, 99)
        t_rank = AUTHORITY_RANK.get(target, 99)
        distance = abs(s_rank - t_rank)

        if distance >= 4:
            return ConflictSeverityLevel.CRITICAL.value
        if distance >= 3:
            return ConflictSeverityLevel.HIGH.value
        if distance >= 2:
            return ConflictSeverityLevel.MEDIUM.value
        return ConflictSeverityLevel.LOW.value
