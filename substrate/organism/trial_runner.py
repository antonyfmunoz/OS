"""Phase 9.3 — Self-Improvement Reliability Campaign Trial Runner.

Runs multiple governed self-improvement trials from observed contradictions,
readiness gaps, and world model defects. Each trial flows through the
full closed loop:

  Observe → Detect → Compose → Convert → Govern → Execute → Validate → Learn → Memory Candidate

Reuses Phase 9.2 infrastructure:
  - WorldModel + ContradictionEngine for candidate detection
  - CompositionEngine for plan composition
  - PlanExecutionAdapter for execution graph conversion
  - GovernedExecutionSpine for governed execution
  - OutcomeLearningLoop for outcome capture
  - MemoryPromotionPipeline for memory candidates
  - ReadinessModel for readiness delta tracking

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

from substrate.organism.composition_engine import (
    CompositionConstraint,
    CompositionEngine,
    CompositionIntent,
    CompositionPlan,
    GovernanceMode,
    RiskClass,
)
from substrate.organism.contradiction_engine import (
    Contradiction,
    ContradictionReport,
    ContradictionSeverity,
    detect_contradictions,
)
from substrate.organism.plan_execution_adapter import (
    ExecutablePlan,
    ExecutionGraphStatus,
    PlanExecutionAdapter,
    StepExecutionStatus,
)
from substrate.organism.readiness_model import ReadinessModel, ReadinessReport
from substrate.organism.world_model import WorldModel, extract_world_model
from substrate.organism.dependency_graph import build_dependency_graph

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class TrialStatus(str, Enum):
    PENDING = "pending"
    COMPOSING = "composing"
    CONVERTING = "converting"
    GOVERNING = "governing"
    EXECUTING = "executing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class CandidateSource(str, Enum):
    CONTRADICTION = "contradiction"
    READINESS_GAP = "readiness_gap"
    WORLD_MODEL_DEFECT = "world_model_defect"
    BOTTLENECK = "bottleneck"
    DEPENDENCY_WEAK_POINT = "dependency_weak_point"


@dataclass
class TrialCandidate:
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    source: CandidateSource = CandidateSource.CONTRADICTION
    description: str = ""
    risk: str = "low"
    severity: str = "info"
    evidence: str = ""
    recommended_fix: str = ""
    entity_id: str = ""
    reversible: bool = True
    measurable: bool = True
    priority_score: float = 0.0
    custom_steps: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source.value,
            "description": self.description,
            "risk": self.risk,
            "severity": self.severity,
            "evidence": self.evidence,
            "recommended_fix": self.recommended_fix,
            "entity_id": self.entity_id,
            "reversible": self.reversible,
            "measurable": self.measurable,
            "priority_score": self.priority_score,
            "has_custom_steps": self.custom_steps is not None,
        }


@dataclass
class TrialMetrics:
    steps_total: int = 0
    steps_succeeded: int = 0
    steps_failed: int = 0
    steps_blocked: int = 0
    approvals_required: int = 0
    execution_duration_seconds: float = 0.0
    validation_passed: bool = False
    rollback_triggered: bool = False
    contradiction_delta: int = 0
    readiness_delta: float = 0.0
    tests_run: int = 0
    memory_candidates_generated: int = 0
    outcome_reliability: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "steps_total": self.steps_total,
            "steps_succeeded": self.steps_succeeded,
            "steps_failed": self.steps_failed,
            "steps_blocked": self.steps_blocked,
            "approvals_required": self.approvals_required,
            "execution_duration_seconds": round(self.execution_duration_seconds, 3),
            "validation_passed": self.validation_passed,
            "rollback_triggered": self.rollback_triggered,
            "contradiction_delta": self.contradiction_delta,
            "readiness_delta": round(self.readiness_delta, 2),
            "tests_run": self.tests_run,
            "memory_candidates_generated": self.memory_candidates_generated,
            "outcome_reliability": round(self.outcome_reliability, 3),
        }


@dataclass
class TrialResult:
    trial_id: str = ""
    candidate: TrialCandidate | None = None
    status: TrialStatus = TrialStatus.PENDING
    metrics: TrialMetrics = field(default_factory=TrialMetrics)
    plan_id: str = ""
    executable_id: str = ""
    governance_dry_run: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    error: str = ""
    learning_signals: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "candidate": self.candidate.to_dict() if self.candidate else None,
            "status": self.status.value,
            "metrics": self.metrics.to_dict(),
            "plan_id": self.plan_id,
            "executable_id": self.executable_id,
            "governance_dry_run": self.governance_dry_run,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "learning_signals": self.learning_signals,
        }


@dataclass
class CampaignBaseline:
    commit: str = ""
    timestamp: float = field(default_factory=time.time)
    entities: int = 0
    contradictions_total: int = 0
    contradictions_by_severity: dict[str, int] = field(default_factory=dict)
    readiness_composite: float = 0.0
    readiness_by_dimension: dict[str, float] = field(default_factory=dict)
    gaps: int = 0
    uncertainties: int = 0
    memory_candidates: int = 0
    journal_entries: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "commit": self.commit,
            "timestamp": self.timestamp,
            "entities": self.entities,
            "contradictions_total": self.contradictions_total,
            "contradictions_by_severity": self.contradictions_by_severity,
            "readiness_composite": round(self.readiness_composite, 1),
            "readiness_by_dimension": {
                k: round(v, 1) for k, v in self.readiness_by_dimension.items()
            },
            "gaps": self.gaps,
            "uncertainties": self.uncertainties,
            "memory_candidates": self.memory_candidates,
            "journal_entries": self.journal_entries,
        }


@dataclass
class CampaignResult:
    campaign_id: str = field(default_factory=lambda: str(uuid4())[:8])
    baseline: CampaignBaseline = field(default_factory=CampaignBaseline)
    after: CampaignBaseline = field(default_factory=CampaignBaseline)
    candidate_queue: list[TrialCandidate] = field(default_factory=list)
    trials: list[TrialResult] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0

    @property
    def completed_trials(self) -> list[TrialResult]:
        return [t for t in self.trials if t.status == TrialStatus.COMPLETED]

    @property
    def failed_trials(self) -> list[TrialResult]:
        return [t for t in self.trials if t.status == TrialStatus.FAILED]

    @property
    def blocked_trials(self) -> list[TrialResult]:
        return [t for t in self.trials if t.status == TrialStatus.BLOCKED]

    @property
    def success_rate(self) -> float:
        total = len(self.completed_trials) + len(self.failed_trials)
        if total == 0:
            return 0.0
        return len(self.completed_trials) / total

    @property
    def contradiction_delta(self) -> int:
        return self.after.contradictions_total - self.baseline.contradictions_total

    @property
    def readiness_delta(self) -> float:
        return self.after.readiness_composite - self.baseline.readiness_composite

    @property
    def total_memory_candidates(self) -> int:
        return sum(t.metrics.memory_candidates_generated for t in self.trials)

    def summary(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "total_candidates": len(self.candidate_queue),
            "total_trials": len(self.trials),
            "completed": len(self.completed_trials),
            "failed": len(self.failed_trials),
            "blocked": len(self.blocked_trials),
            "success_rate": round(self.success_rate, 3),
            "contradiction_delta": self.contradiction_delta,
            "readiness_delta": round(self.readiness_delta, 2),
            "total_memory_candidates": self.total_memory_candidates,
            "duration_seconds": round(self.completed_at - self.started_at, 2)
            if self.completed_at
            else 0,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "baseline": self.baseline.to_dict(),
            "after": self.after.to_dict(),
            "candidate_queue": [c.to_dict() for c in self.candidate_queue],
            "trials": [t.to_dict() for t in self.trials],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


# ---------------------------------------------------------------------------
# Candidate ranking
# ---------------------------------------------------------------------------

_SEVERITY_SCORES: dict[str, float] = {
    "critical": 100.0,
    "high": 80.0,
    "medium": 60.0,
    "low": 40.0,
    "info": 20.0,
}

_RISK_FILTER = {"low", "medium"}
_BLOCKED_RISKS = {"high", "critical"}


def rank_candidates(candidates: list[TrialCandidate]) -> list[TrialCandidate]:
    """Rank candidates by priority score (highest first). Filter out blocked risks."""
    eligible = [c for c in candidates if c.risk not in _BLOCKED_RISKS]
    for c in eligible:
        c.priority_score = _SEVERITY_SCORES.get(c.severity, 10.0)
        if c.reversible:
            c.priority_score += 10.0
        if c.measurable:
            c.priority_score += 10.0
        if c.source == CandidateSource.CONTRADICTION:
            c.priority_score += 5.0
        if c.source == CandidateSource.READINESS_GAP:
            c.priority_score += 3.0
    eligible.sort(key=lambda c: c.priority_score, reverse=True)
    return eligible


def build_candidate_queue(
    world_model: WorldModel | None = None,
    contradiction_report: ContradictionReport | None = None,
) -> list[TrialCandidate]:
    """Build ranked candidate queue from observed reality."""
    if world_model is None:
        world_model = extract_world_model()
    dep_graph = build_dependency_graph(world_model)
    if contradiction_report is None:
        contradiction_report = detect_contradictions(world_model, dep_graph)

    candidates: list[TrialCandidate] = []

    for c in contradiction_report.contradictions:
        risk = "low"
        if c.severity in (ContradictionSeverity.HIGH, ContradictionSeverity.CRITICAL):
            risk = "medium"

        candidate = TrialCandidate(
            source=CandidateSource.CONTRADICTION,
            description=c.evidence,
            risk=risk,
            severity=c.severity.value,
            evidence=c.evidence,
            recommended_fix=c.recommended_fix,
            entity_id=c.claim.entity_id if c.claim else "",
            reversible=True,
            measurable=True,
        )

        if c.contradiction_type.value == "stale_deployment":
            candidate.custom_steps = _deployment_fix_steps(c)
        elif c.contradiction_type.value == "wiring_mismatch":
            candidate.custom_steps = _wiring_fix_steps(c)
        elif c.contradiction_type.value == "route_mismatch":
            candidate.custom_steps = _route_verification_steps(c)

        candidates.append(candidate)

    for gap in world_model.gaps:
        candidates.append(TrialCandidate(
            source=CandidateSource.WORLD_MODEL_DEFECT,
            description=gap.description,
            risk="low",
            severity=gap.severity.value,
            evidence=gap.description,
            recommended_fix=gap.recommendation,
            entity_id=gap.entity_id,
            reversible=True,
            measurable=True,
        ))

    return rank_candidates(candidates)


def _deployment_fix_steps(c: Contradiction) -> list[dict[str, Any]]:
    return [
        {"action": "verify_current_state", "desc": f"Verify contradiction exists: {c.evidence[:60]}",
         "risk": "low", "gov": "autonomous", "verify": "Contradiction confirmed"},
        {"action": "fix_world_model_path", "desc": f"Fix world model observation path",
         "risk": "low", "gov": "autonomous", "verify": "World model path corrected"},
        {"action": "verify_contradiction_resolved", "desc": "Re-run contradiction engine",
         "risk": "low", "gov": "autonomous", "verify": "Contradiction count reduced"},
        {"action": "verify_tests_pass", "desc": "Verify no regressions",
         "risk": "low", "gov": "autonomous", "verify": "py_compile succeeds"},
    ]


def _wiring_fix_steps(c: Contradiction) -> list[dict[str, Any]]:
    return [
        {"action": "verify_current_state", "desc": f"Verify orphaned subsystem: {c.evidence[:60]}",
         "risk": "low", "gov": "autonomous", "verify": "Orphan confirmed"},
        {"action": "add_dependency_edge", "desc": "Add dependency edge in dependency graph",
         "risk": "low", "gov": "autonomous", "verify": "Edge added"},
        {"action": "verify_contradiction_resolved", "desc": "Re-run contradiction engine",
         "risk": "low", "gov": "autonomous", "verify": "Orphan eliminated"},
        {"action": "verify_tests_pass", "desc": "Verify no regressions",
         "risk": "low", "gov": "autonomous", "verify": "Tests pass"},
    ]


def _route_verification_steps(c: Contradiction) -> list[dict[str, Any]]:
    return [
        {"action": "verify_current_state", "desc": f"Verify route mismatch: {c.evidence[:60]}",
         "risk": "low", "gov": "autonomous", "verify": "Mismatch confirmed"},
        {"action": "verify_route_exists", "desc": "Check if route exists in alternate location",
         "risk": "low", "gov": "autonomous", "verify": "Route location determined"},
        {"action": "verify_tests_pass", "desc": "Verify no regressions",
         "risk": "low", "gov": "autonomous", "verify": "Tests pass"},
    ]


# ---------------------------------------------------------------------------
# Safety gates
# ---------------------------------------------------------------------------

_HARD_BLOCK_RISKS = {"high", "critical"}
_BLOCKED_ACTIONS = {
    "credential", "auth", "dns", "deploy", "container_restart",
    "shell_mutation", "broad_rewrite",
}


def safety_check(candidate: TrialCandidate) -> str:
    """Returns empty string if safe, or rejection reason."""
    if candidate.risk in _HARD_BLOCK_RISKS:
        return f"risk={candidate.risk} is hard-blocked"
    desc_lower = candidate.description.lower()
    for blocked in _BLOCKED_ACTIONS:
        if blocked in desc_lower:
            return f"action contains blocked keyword: {blocked}"
    return ""


# ---------------------------------------------------------------------------
# Trial Runner
# ---------------------------------------------------------------------------

class ReliabilityCampaignRunner:
    """Runs a reliability campaign of multiple governed self-improvement trials."""

    def __init__(
        self,
        adapter: PlanExecutionAdapter,
        composition_engine: CompositionEngine | None = None,
        readiness_model: ReadinessModel | None = None,
        readiness_state_fn: Callable[[], dict[str, dict[str, Any]]] | None = None,
    ) -> None:
        self._adapter = adapter
        self._composition = composition_engine
        self._readiness = readiness_model or ReadinessModel()
        self._readiness_state_fn = readiness_state_fn
        self._campaign: CampaignResult | None = None
        self._prev_memory_count: int = 0

    def _ensure_composition(self) -> CompositionEngine:
        if self._composition is None:
            self._composition = CompositionEngine()
        return self._composition

    def _compute_readiness(self) -> ReadinessReport:
        if self._readiness_state_fn:
            states = self._readiness_state_fn()
            return self._readiness.compute(**states)
        return self._readiness.compute()

    def _capture_baseline(
        self,
        commit: str = "",
        world_model: WorldModel | None = None,
        contradiction_report: ContradictionReport | None = None,
    ) -> CampaignBaseline:
        if world_model is None:
            world_model = extract_world_model()
        dep_graph = build_dependency_graph(world_model)
        if contradiction_report is None:
            contradiction_report = detect_contradictions(world_model, dep_graph)

        readiness = self._compute_readiness()

        sev_counts: dict[str, int] = {}
        for c in contradiction_report.contradictions:
            sev_counts[c.severity.value] = sev_counts.get(c.severity.value, 0) + 1

        return CampaignBaseline(
            commit=commit,
            entities=len(world_model.entities),
            contradictions_total=len(contradiction_report.contradictions),
            contradictions_by_severity=sev_counts,
            readiness_composite=readiness.composite_score,
            readiness_by_dimension={
                d.dimension: d.score for d in readiness.dimensions
            },
            gaps=len(world_model.gaps),
            uncertainties=len(world_model.uncertainties),
        )

    def run_campaign(
        self,
        candidates: list[TrialCandidate],
        commit: str = "",
        max_trials: int = 12,
        step_executors_factory: Callable[
            [TrialCandidate, CompositionPlan], dict[str, Callable[[], tuple[str, bool]]]
        ]
        | None = None,
    ) -> CampaignResult:
        """Run the full reliability campaign."""
        campaign = CampaignResult()
        campaign.baseline = self._capture_baseline(commit=commit)
        campaign.candidate_queue = list(candidates)
        self._campaign = campaign

        trials_run = 0
        for candidate in candidates:
            if trials_run >= max_trials:
                break

            safety_reason = safety_check(candidate)
            if safety_reason:
                result = TrialResult(
                    trial_id=f"trial_{trials_run + 1}_{candidate.id}",
                    candidate=candidate,
                    status=TrialStatus.BLOCKED,
                    error=safety_reason,
                )
                campaign.trials.append(result)
                trials_run += 1
                continue

            result = self._run_single_trial(
                candidate,
                trial_number=trials_run + 1,
                step_executors_factory=step_executors_factory,
            )
            campaign.trials.append(result)
            trials_run += 1

        campaign.after = self._capture_baseline(commit=commit)
        campaign.completed_at = time.time()

        return campaign

    def _run_single_trial(
        self,
        candidate: TrialCandidate,
        trial_number: int,
        step_executors_factory: Callable[
            [TrialCandidate, CompositionPlan], dict[str, Callable[[], tuple[str, bool]]]
        ]
        | None = None,
    ) -> TrialResult:
        trial_id = f"trial_{trial_number}_{candidate.id}"
        result = TrialResult(
            trial_id=trial_id,
            candidate=candidate,
            started_at=time.time(),
        )

        try:
            result.status = TrialStatus.COMPOSING
            engine = self._ensure_composition()
            intent = CompositionIntent(
                description=candidate.description,
                priority="normal",
                source="reliability_campaign",
            )
            constraints = [
                CompositionConstraint(
                    name="no_high_risk",
                    description="Block HIGH/CRITICAL risk actions",
                    hard=True,
                ),
                CompositionConstraint(
                    name="reversible_only",
                    description="Only fully reversible changes",
                    hard=True,
                ),
            ]
            plan = engine.compose(
                intent,
                constraints=constraints,
                custom_steps=candidate.custom_steps,
            )
            result.plan_id = plan.id

            if plan.overall_risk in (RiskClass.HIGH, RiskClass.CRITICAL):
                result.status = TrialStatus.BLOCKED
                result.error = f"Plan risk {plan.overall_risk.value} exceeds campaign threshold"
                result.completed_at = time.time()
                return result

            result.status = TrialStatus.CONVERTING
            executable = self._adapter.convert_plan(plan)
            result.executable_id = executable.id

            result.status = TrialStatus.GOVERNING
            high_risk_steps = [
                s for s in executable.steps if s.risk_level in ("high", "critical")
            ]
            if high_risk_steps:
                result.status = TrialStatus.BLOCKED
                result.governance_dry_run = "blocked"
                result.error = f"{len(high_risk_steps)} steps exceed risk threshold"
                result.completed_at = time.time()
                return result
            result.governance_dry_run = "passed"

            result.status = TrialStatus.EXECUTING
            step_executors: dict[str, Callable[[], tuple[str, bool]]] = {}
            if step_executors_factory:
                step_executors = step_executors_factory(candidate, plan)

            executed = self._adapter.execute_plan(executable, step_executors=step_executors)

            result.status = TrialStatus.VALIDATING
            metrics = result.metrics
            metrics.steps_total = len(executed.steps)
            metrics.steps_succeeded = executed.success_count()
            metrics.steps_failed = executed.failure_count()
            metrics.steps_blocked = sum(
                1 for s in executed.steps
                if s.status == StepExecutionStatus.BLOCKED_BY_FAILURE
            )
            metrics.approvals_required = sum(
                1 for s in executed.steps if s.requires_approval
            )
            metrics.execution_duration_seconds = max(
                executed.completed_at - executed.started_at, 0
            )

            if executed.status == ExecutionGraphStatus.COMPLETED:
                metrics.validation_passed = True
                result.status = TrialStatus.COMPLETED
            elif executed.status == ExecutionGraphStatus.PARTIALLY_COMPLETED:
                metrics.validation_passed = False
                result.status = TrialStatus.COMPLETED
            else:
                metrics.validation_passed = False
                result.status = TrialStatus.FAILED
                result.error = "Execution failed"

            if metrics.steps_total > 0:
                metrics.outcome_reliability = metrics.steps_succeeded / metrics.steps_total

            if hasattr(self._adapter, '_memory_pipeline') and self._adapter._memory_pipeline is not None:
                current_count = len(self._adapter._memory_pipeline.list_candidates())
                metrics.memory_candidates_generated = max(
                    current_count - getattr(self, '_prev_memory_count', 0), 0
                )
                self._prev_memory_count = current_count

        except Exception as exc:
            result.status = TrialStatus.FAILED
            result.error = str(exc)[:500]
            logger.warning("Trial %s failed: %s", trial_id, exc)

        result.completed_at = time.time()
        return result

    @property
    def campaign(self) -> CampaignResult | None:
        return self._campaign

    def to_dict(self) -> dict[str, Any]:
        if self._campaign is None:
            return {"status": "not_started"}
        return self._campaign.to_dict()


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def persist_campaign(campaign: CampaignResult, path: str | None = None) -> str:
    if path is None:
        path = os.path.join(_REPO_ROOT, "data", "umh", "trials", "phase9_3_campaign_results.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(campaign.to_dict(), f, indent=2, default=str)
    return path


def persist_candidate_queue(candidates: list[TrialCandidate], path: str | None = None) -> str:
    if path is None:
        path = os.path.join(_REPO_ROOT, "data", "umh", "trials", "phase9_3_candidate_queue.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump([c.to_dict() for c in candidates], f, indent=2, default=str)
    return path
