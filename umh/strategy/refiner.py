"""UMH Strategy Refiner — deterministic refinement proposals.

Analyzes strategy performance and suggests improvements as
RefinementProposal objects. Proposals are ADVISORY — they do not
auto-apply. The operator must explicitly apply via API/CLI.

This module never modifies existing strategies. It only creates
new candidate strategies based on detected patterns.
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field

from umh.core.clock import iso_now as _iso_now
from umh.events.stream import publish as _publish_event
from umh.strategy.history import (
    PerformanceMetrics,
    StrategyVersion,
    get_strategy_history,
)
from umh.strategy.models import (
    ApproachType,
    StepComplexity,
    StepStatus,
    StepType,
    Strategy,
    StrategyStep,
)
from umh.strategy.scoring import StrategyScore, score_strategy

_log = logging.getLogger(__name__)

REFINEMENT_MIN_EVALUATIONS = 3
HIGH_FAILURE_THRESHOLD = 0.3
HIGH_RETRY_THRESHOLD = 0.25


@dataclass
class RefinementIssue:
    """A detected issue in the current strategy."""

    issue_type: str
    description: str
    step_id: str = ""
    severity: str = "medium"

    def to_dict(self) -> dict:
        return {
            "issue_type": self.issue_type,
            "description": self.description,
            "step_id": self.step_id,
            "severity": self.severity,
        }


@dataclass
class RefinementProposal:
    """A proposed strategy refinement — ADVISORY only."""

    goal_id: str
    issues_detected: list[RefinementIssue] = field(default_factory=list)
    suggested_changes: list[str] = field(default_factory=list)
    new_strategy: Strategy | None = None
    current_score: StrategyScore | None = None
    expected_improvement: float = 0.0
    confidence: float = 0.0
    recommended: bool = False
    id: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"ref_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = _iso_now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "issues_detected": [i.to_dict() for i in self.issues_detected],
            "suggested_changes": self.suggested_changes,
            "new_strategy": self.new_strategy.to_dict() if self.new_strategy else None,
            "current_score": (self.current_score.to_dict() if self.current_score else None),
            "expected_improvement": round(self.expected_improvement, 3),
            "confidence": round(self.confidence, 3),
            "recommended": self.recommended,
            "created_at": self.created_at,
        }


def refine_strategy(goal_id: str) -> RefinementProposal | None:
    """Analyze current strategy performance and propose refinements.

    Returns a RefinementProposal if issues are detected, None otherwise.
    Requires at least REFINEMENT_MIN_EVALUATIONS before analyzing.
    """
    history = get_strategy_history(goal_id)
    active = history.active_version()

    if active is None:
        return None

    perf = active.performance
    if perf.evaluations < REFINEMENT_MIN_EVALUATIONS:
        return None

    current_score = score_strategy(active)
    strategy = active.strategy

    issues: list[RefinementIssue] = []
    changes: list[str] = []

    # Detection 1: High failure rate
    if perf.success_rate < (1.0 - HIGH_FAILURE_THRESHOLD):
        failed_steps = [s for s in strategy.steps if s.status == StepStatus.FAILED]
        for step in failed_steps:
            issues.append(
                RefinementIssue(
                    issue_type="high_failure_rate",
                    description=(f"Step '{step.description[:50]}' failed — consider restructuring"),
                    step_id=step.id,
                    severity="high",
                )
            )
        changes.append("Restructure steps with high failure rate")

    # Detection 2: Frequent retries
    retry_rate = perf.tasks_retried / max(perf.evaluations, 1)
    if retry_rate > HIGH_RETRY_THRESHOLD:
        issues.append(
            RefinementIssue(
                issue_type="frequent_retries",
                description=(
                    f"Retry rate {retry_rate:.0%} exceeds threshold"
                    " — consider splitting complex steps"
                ),
                severity="medium",
            )
        )
        changes.append("Split complex steps that require frequent retries")

    # Detection 3: Bottleneck steps (high complexity with many tasks)
    for step in strategy.steps:
        if (
            step.estimated_complexity == StepComplexity.HIGH
            and len(step.task_ids) > 2
            and step.status != StepStatus.COMPLETED
        ):
            issues.append(
                RefinementIssue(
                    issue_type="bottleneck",
                    description=(
                        f"Step '{step.description[:50]}' is high complexity"
                        f" with {len(step.task_ids)} tasks"
                    ),
                    step_id=step.id,
                    severity="medium",
                )
            )
            changes.append(f"Consider splitting bottleneck step {step.id}")

    # Detection 4: Dead steps (never produce tasks)
    for step in strategy.steps:
        if (
            step.generates_tasks
            and step.status == StepStatus.PENDING
            and perf.evaluations >= REFINEMENT_MIN_EVALUATIONS * 2
        ):
            issues.append(
                RefinementIssue(
                    issue_type="dead_step",
                    description=(
                        f"Step '{step.description[:50]}' has not produced tasks"
                        f" after {perf.evaluations} evaluations"
                    ),
                    step_id=step.id,
                    severity="low",
                )
            )
            changes.append(f"Remove or restructure dead step {step.id}")

    if not issues:
        return None

    # Build candidate strategy
    new_strategy = _build_refined_strategy(strategy, issues)
    expected_improvement = _estimate_improvement(issues, current_score)

    proposal = RefinementProposal(
        goal_id=goal_id,
        issues_detected=issues,
        suggested_changes=changes,
        new_strategy=new_strategy,
        current_score=current_score,
        expected_improvement=expected_improvement,
        confidence=_compute_confidence(perf, issues),
        recommended=(
            expected_improvement > 0.1 and perf.evaluations >= REFINEMENT_MIN_EVALUATIONS * 2
        ),
    )

    _publish_event(
        "strategy.refinement_proposed",
        payload={
            "goal_id": goal_id,
            "proposal_id": proposal.id,
            "issues": len(issues),
            "expected_improvement": proposal.expected_improvement,
            "recommended": proposal.recommended,
        },
        actor_id=f"goal:{goal_id}",
    )

    return proposal


def _build_refined_strategy(original: Strategy, issues: list[RefinementIssue]) -> Strategy:
    """Build a new strategy candidate addressing detected issues.

    Never modifies the original — creates a fresh copy with adjustments.
    """
    new_steps: list[StrategyStep] = []
    dead_ids = {i.step_id for i in issues if i.issue_type == "dead_step"}
    bottleneck_ids = {i.step_id for i in issues if i.issue_type == "bottleneck"}
    failed_ids = {i.step_id for i in issues if i.issue_type == "high_failure_rate"}

    for step in original.steps:
        if step.id in dead_ids:
            continue

        if step.id in bottleneck_ids:
            new_steps.append(
                StrategyStep(
                    description=f"Prepare: {step.description}",
                    type=StepType.RESEARCH,
                    estimated_complexity=StepComplexity.LOW,
                    generates_tasks=True,
                )
            )
            new_steps.append(
                StrategyStep(
                    description=step.description,
                    type=step.type,
                    estimated_complexity=StepComplexity.MEDIUM,
                    generates_tasks=True,
                )
            )
            continue

        if step.id in failed_ids:
            new_steps.append(
                StrategyStep(
                    description=f"Validate prerequisites for: {step.description}",
                    type=StepType.VALIDATION,
                    estimated_complexity=StepComplexity.LOW,
                    generates_tasks=True,
                )
            )
            new_steps.append(
                StrategyStep(
                    description=step.description,
                    type=step.type,
                    estimated_complexity=step.estimated_complexity,
                    generates_tasks=True,
                )
            )
            continue

        new_steps.append(
            StrategyStep(
                description=step.description,
                type=step.type,
                estimated_complexity=step.estimated_complexity,
                generates_tasks=step.generates_tasks,
            )
        )

    # Wire sequential dependencies
    if len(new_steps) > 1:
        for i in range(1, len(new_steps)):
            new_steps[i].dependencies = [new_steps[i - 1].id]

    return Strategy(
        goal_id=original.goal_id,
        objective=original.objective,
        approach_type=original.approach_type,
        steps=new_steps,
        confidence=original.confidence * 0.9,
        reasoning=f"Refined from {original.id}: addressed {len(issues)} issues",
        template_used=f"refined_{original.template_used}",
    )


def _estimate_improvement(issues: list[RefinementIssue], current_score: StrategyScore) -> float:
    """Estimate expected improvement from addressing issues."""
    severity_impact = {"high": 0.15, "medium": 0.08, "low": 0.03}
    total = sum(severity_impact.get(i.severity, 0.05) for i in issues)
    return min(total, 0.5)


def _compute_confidence(perf: PerformanceMetrics, issues: list[RefinementIssue]) -> float:
    """Compute confidence in the refinement proposal."""
    base = min(perf.evaluations / 10, 1.0) * 0.5
    issue_factor = min(len(issues) / 3, 1.0) * 0.3
    data_factor = min((perf.tasks_completed + perf.tasks_failed) / 10, 1.0) * 0.2
    return min(base + issue_factor + data_factor, 1.0)


# -- Proposal Store ---------------------------------------------------

_proposals: dict[str, RefinementProposal] = {}
_proposals_lock = threading.Lock()


def get_proposal(goal_id: str) -> RefinementProposal | None:
    """Return the latest refinement proposal for a goal."""
    with _proposals_lock:
        return _proposals.get(goal_id)


def store_proposal(proposal: RefinementProposal) -> None:
    """Store a refinement proposal."""
    with _proposals_lock:
        _proposals[proposal.goal_id] = proposal


def clear_proposal(goal_id: str) -> bool:
    """Clear a proposal. Returns True if it existed."""
    with _proposals_lock:
        return _proposals.pop(goal_id, None) is not None


def reset_proposals() -> None:
    """Clear all proposals (for testing)."""
    with _proposals_lock:
        _proposals.clear()
