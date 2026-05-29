"""Autonomous Improvement Lane — bounded autonomous LOW-risk self-improvement.

Selects safe, template-guided improvement candidates from observed reality
and executes them through the governed spine with full validation, rollback,
propagation, and audit trail.

Autonomy is earned through:
  - observed reality (evidence-based candidates)
  - template confidence >= threshold
  - agent reliability >= threshold
  - risk classification (LOW only)
  - governance gates (dry-run first)
  - validation proof
  - rollback availability
  - spine-native propagation
  - cockpit transparency

If conditions are not met: recommend only, request approval, or block.

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

from substrate.organism.agent_capability_model import AgentCapabilityModel
from substrate.organism.composition_engine import (
    CompositionConstraint,
    CompositionEngine,
    CompositionIntent,
    CompositionPlan,
    GovernanceMode,
    RiskClass,
)
from substrate.organism.contradiction_engine import (
    ContradictionReport,
    ContradictionSeverity,
    detect_contradictions,
)
from substrate.organism.dependency_graph import build_dependency_graph
from substrate.organism.plan_execution_adapter import (
    ExecutionGraphStatus,
    PlanExecutionAdapter,
    StepExecutionStatus,
)
from substrate.organism.template_registry import (
    TemplateCandidate,
    TemplateRegistry,
    TemplateStatus,
)
from substrate.organism.trial_runner import (
    CandidateSource,
    TrialCandidate,
    safety_check,
)
from substrate.organism.world_model import WorldModel, extract_world_model

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LaneDecision(str, Enum):
    ELIGIBLE = "eligible"
    RECOMMENDED = "recommended"
    BLOCKED = "blocked"
    APPROVAL_REQUIRED = "approval_required"


class LaneRunStatus(str, Enum):
    DRY_RUN = "dry_run"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ELIGIBLE = "no_eligible"
    BLOCKED = "blocked"


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


@dataclass
class AutonomousLanePolicy:
    max_candidates_per_run: int = 3
    max_executions_per_run: int = 1
    max_file_changes_per_execution: int = 2
    allowed_risk: str = "low"
    require_template: bool = True
    require_rollback_or_non_mutating: bool = True
    require_validation: bool = True
    require_agent_reliability: float = 0.70
    require_template_confidence: float = 0.60
    cooldown_minutes_per_template: int = 30
    cooldown_minutes_per_file: int = 60
    dry_run_first: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_candidates_per_run": self.max_candidates_per_run,
            "max_executions_per_run": self.max_executions_per_run,
            "max_file_changes_per_execution": self.max_file_changes_per_execution,
            "allowed_risk": self.allowed_risk,
            "require_template": self.require_template,
            "require_rollback_or_non_mutating": self.require_rollback_or_non_mutating,
            "require_validation": self.require_validation,
            "require_agent_reliability": self.require_agent_reliability,
            "require_template_confidence": self.require_template_confidence,
            "cooldown_minutes_per_template": self.cooldown_minutes_per_template,
            "cooldown_minutes_per_file": self.cooldown_minutes_per_file,
            "dry_run_first": self.dry_run_first,
        }


# ---------------------------------------------------------------------------
# Candidate
# ---------------------------------------------------------------------------


@dataclass
class AutonomousImprovementCandidate:
    candidate_id: str = field(default_factory=lambda: f"alc-{uuid4().hex[:8]}")
    source: CandidateSource = CandidateSource.CONTRADICTION
    description: str = ""
    affected_files: list[str] = field(default_factory=list)
    affected_entities: list[str] = field(default_factory=list)
    risk_class: str = "low"
    reversible: bool = True
    non_mutating: bool = False
    validation_method: str = ""
    rollback_method: str = ""
    matching_template_id: str = ""
    template_confidence: float = 0.0
    required_agent_type: str = "developer_agent"
    required_capabilities: list[str] = field(default_factory=list)
    agent_reliability: float = 0.0
    governance_mode_required: str = "autonomous"
    expected_outcome: str = ""
    selection_score: float = 0.0
    selection_reason: str = ""
    evidence: str = ""
    entity_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source": self.source.value,
            "description": self.description,
            "affected_files": self.affected_files,
            "affected_entities": self.affected_entities,
            "risk_class": self.risk_class,
            "reversible": self.reversible,
            "non_mutating": self.non_mutating,
            "validation_method": self.validation_method,
            "rollback_method": self.rollback_method,
            "matching_template_id": self.matching_template_id,
            "template_confidence": round(self.template_confidence, 3),
            "required_agent_type": self.required_agent_type,
            "required_capabilities": self.required_capabilities,
            "agent_reliability": round(self.agent_reliability, 3),
            "governance_mode_required": self.governance_mode_required,
            "expected_outcome": self.expected_outcome,
            "selection_score": round(self.selection_score, 2),
            "selection_reason": self.selection_reason,
            "evidence": self.evidence,
            "entity_id": self.entity_id,
        }


@dataclass
class CandidateEvaluation:
    candidate_id: str = ""
    decision: LaneDecision = LaneDecision.BLOCKED
    block_reasons: list[str] = field(default_factory=list)
    policy_checks: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "decision": self.decision.value,
            "block_reasons": self.block_reasons,
            "policy_checks": self.policy_checks,
        }


# ---------------------------------------------------------------------------
# Run result
# ---------------------------------------------------------------------------


@dataclass
class AutonomousLaneRun:
    run_id: str = field(default_factory=lambda: f"alr-{uuid4().hex[:8]}")
    status: LaneRunStatus = LaneRunStatus.DRY_RUN
    policy: AutonomousLanePolicy = field(default_factory=AutonomousLanePolicy)
    candidates: list[AutonomousImprovementCandidate] = field(default_factory=list)
    evaluations: list[CandidateEvaluation] = field(default_factory=list)
    selected_candidate: AutonomousImprovementCandidate | None = None
    plan_id: str = ""
    executable_id: str = ""
    governance_dry_run: str = ""
    execution_status: str = ""
    validation_result: str = ""
    propagation_events: int = 0
    template_confidence_before: float = 0.0
    template_confidence_after: float = 0.0
    agent_reliability_before: float = 0.0
    agent_reliability_after: float = 0.0
    rollback_available: bool = False
    error: str = ""
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0

    @property
    def eligible_candidates(self) -> list[AutonomousImprovementCandidate]:
        eligible_ids = {
            e.candidate_id
            for e in self.evaluations
            if e.decision == LaneDecision.ELIGIBLE
        }
        return [c for c in self.candidates if c.candidate_id in eligible_ids]

    @property
    def blocked_candidates(self) -> list[tuple[AutonomousImprovementCandidate, CandidateEvaluation]]:
        blocked_evals = {
            e.candidate_id: e
            for e in self.evaluations
            if e.decision in (LaneDecision.BLOCKED, LaneDecision.APPROVAL_REQUIRED)
        }
        return [
            (c, blocked_evals[c.candidate_id])
            for c in self.candidates
            if c.candidate_id in blocked_evals
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status.value,
            "policy": self.policy.to_dict(),
            "candidates_count": len(self.candidates),
            "eligible_count": len(self.eligible_candidates),
            "blocked_count": len(self.blocked_candidates),
            "selected_candidate": self.selected_candidate.to_dict() if self.selected_candidate else None,
            "plan_id": self.plan_id,
            "executable_id": self.executable_id,
            "governance_dry_run": self.governance_dry_run,
            "execution_status": self.execution_status,
            "validation_result": self.validation_result,
            "propagation_events": self.propagation_events,
            "template_confidence_before": round(self.template_confidence_before, 3),
            "template_confidence_after": round(self.template_confidence_after, 3),
            "agent_reliability_before": round(self.agent_reliability_before, 3),
            "agent_reliability_after": round(self.agent_reliability_after, 3),
            "rollback_available": self.rollback_available,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": round(self.completed_at - self.started_at, 2) if self.completed_at else 0,
            "evaluations": [e.to_dict() for e in self.evaluations],
            "candidates": [c.to_dict() for c in self.candidates],
        }


# ---------------------------------------------------------------------------
# Sensitive keyword filter
# ---------------------------------------------------------------------------

_SENSITIVE_KEYWORDS = frozenset({
    "credential", "auth", "dns", "deploy", "container_restart",
    "shell_mutation", "broad_rewrite", "password", "secret",
    "token", "certificate", "ssl", "tls", "ssh_key", "api_key",
    "migration", "drop_table", "truncate", "rm -rf", "sudo",
})

_SENSITIVE_PATHS = frozenset({
    ".env", "credentials", "secrets", "certs", "keys",
    "docker-compose", "dockerfile", "nginx.conf",
    "authorized_keys", "id_rsa", "ssh_config",
})


def _has_sensitive_content(candidate: AutonomousImprovementCandidate) -> str | None:
    desc_lower = candidate.description.lower()
    for kw in _SENSITIVE_KEYWORDS:
        if kw in desc_lower:
            return f"description contains sensitive keyword: {kw}"
    for path in candidate.affected_files:
        path_lower = path.lower()
        for sp in _SENSITIVE_PATHS:
            if sp in path_lower:
                return f"affects sensitive path: {path}"
    return None


# ---------------------------------------------------------------------------
# Candidate selector
# ---------------------------------------------------------------------------


class AutonomousCandidateSelector:
    """Builds autonomous improvement candidates from observed reality."""

    def __init__(
        self,
        template_registry: TemplateRegistry,
        agent_capability_model: AgentCapabilityModel,
    ) -> None:
        self._templates = template_registry
        self._acm = agent_capability_model

    def build_candidates(
        self,
        world_model: WorldModel | None = None,
        contradiction_report: ContradictionReport | None = None,
        max_candidates: int = 10,
    ) -> list[AutonomousImprovementCandidate]:
        if world_model is None:
            world_model = extract_world_model()
        dep_graph = build_dependency_graph(world_model)
        if contradiction_report is None:
            contradiction_report = detect_contradictions(world_model, dep_graph)

        candidates: list[AutonomousImprovementCandidate] = []

        candidates.extend(self._from_contradictions(contradiction_report))
        candidates.extend(self._from_world_model_gaps(world_model))
        candidates.extend(self._from_dependency_orphans(world_model, dep_graph))

        for c in candidates:
            self._enrich_with_template(c)
            self._enrich_with_agent_reliability(c)
            c.selection_score = self._score(c)

        candidates.sort(key=lambda c: c.selection_score, reverse=True)
        return candidates[:max_candidates]

    def _from_contradictions(
        self, report: ContradictionReport
    ) -> list[AutonomousImprovementCandidate]:
        candidates = []
        for c in report.contradictions:
            if c.severity in (ContradictionSeverity.HIGH, ContradictionSeverity.CRITICAL):
                continue

            candidate = AutonomousImprovementCandidate(
                source=CandidateSource.CONTRADICTION,
                description=c.evidence,
                risk_class="low",
                reversible=True,
                non_mutating=False,
                validation_method="re-run contradiction engine to verify resolution",
                rollback_method="revert world model observation",
                expected_outcome=f"Resolve contradiction: {c.evidence[:80]}",
                evidence=c.evidence,
                entity_id=c.claim.entity_id if c.claim else "",
                affected_entities=[c.claim.entity_id] if c.claim else [],
                required_capabilities=["code_search", "file_edit"],
                selection_reason=f"contradiction ({c.severity.value})",
            )
            candidates.append(candidate)
        return candidates

    def _from_world_model_gaps(
        self, world_model: WorldModel
    ) -> list[AutonomousImprovementCandidate]:
        candidates = []
        for gap in world_model.gaps:
            candidate = AutonomousImprovementCandidate(
                source=CandidateSource.WORLD_MODEL_DEFECT,
                description=gap.description,
                risk_class="low",
                reversible=True,
                non_mutating=True,
                validation_method="verify gap resolved in world model",
                rollback_method="",
                expected_outcome=f"Close world model gap: {gap.description[:80]}",
                evidence=gap.description,
                entity_id=gap.entity_id,
                affected_entities=[gap.entity_id],
                required_capabilities=["code_search"],
                selection_reason="world model gap",
            )
            candidates.append(candidate)
        return candidates

    def _from_dependency_orphans(
        self, world_model: WorldModel, dep_graph: Any
    ) -> list[AutonomousImprovementCandidate]:
        candidates = []
        if not hasattr(dep_graph, "orphan_nodes"):
            return candidates
        for orphan_id in dep_graph.orphan_nodes():
            candidate = AutonomousImprovementCandidate(
                source=CandidateSource.DEPENDENCY_WEAK_POINT,
                description=f"Dependency graph orphan: {orphan_id}",
                risk_class="low",
                reversible=True,
                non_mutating=False,
                validation_method="verify node has edges in dependency graph",
                rollback_method="remove added edge",
                expected_outcome=f"Connect orphan node: {orphan_id}",
                evidence=f"Node {orphan_id} has no edges",
                entity_id=orphan_id,
                affected_entities=[orphan_id],
                required_capabilities=["dependency_analysis"],
                selection_reason="dependency graph orphan",
            )
            candidates.append(candidate)
        return candidates

    def _enrich_with_template(self, candidate: AutonomousImprovementCandidate) -> None:
        type_hints = {
            CandidateSource.CONTRADICTION: "contradiction_fix",
            CandidateSource.WORLD_MODEL_DEFECT: "world_model_accuracy_fix",
            CandidateSource.DEPENDENCY_WEAK_POINT: "dependency_graph_fix",
            CandidateSource.READINESS_GAP: "readiness_improvement",
            CandidateSource.BOTTLENECK: "maintenance_action",
        }
        template_type = type_hints.get(candidate.source, "maintenance_action")
        matches = self._templates.find_matching(template_type)
        promoted = [m for m in matches if m.status == TemplateStatus.PROMOTED]

        if promoted:
            best = max(promoted, key=lambda t: t.confidence)
            candidate.matching_template_id = best.template_id
            candidate.template_confidence = best.confidence
        elif matches:
            best = max(matches, key=lambda t: t.confidence)
            candidate.matching_template_id = best.template_id
            candidate.template_confidence = best.confidence

    def _enrich_with_agent_reliability(
        self, candidate: AutonomousImprovementCandidate
    ) -> None:
        profile = self._acm.get_profile(candidate.required_agent_type)
        if profile:
            candidate.agent_reliability = profile.overall_reliability

    def _score(self, candidate: AutonomousImprovementCandidate) -> float:
        score = 0.0
        if candidate.matching_template_id:
            score += 40.0
            score += candidate.template_confidence * 20.0
        if candidate.agent_reliability > 0:
            score += candidate.agent_reliability * 15.0
        if candidate.non_mutating:
            score += 10.0
        if candidate.reversible:
            score += 5.0
        if candidate.source == CandidateSource.CONTRADICTION:
            score += 5.0
        if candidate.validation_method:
            score += 5.0
        return score


# ---------------------------------------------------------------------------
# Policy evaluator
# ---------------------------------------------------------------------------


class AutonomousPolicyEvaluator:
    """Evaluates candidates against autonomous lane policy."""

    def __init__(
        self,
        policy: AutonomousLanePolicy,
        recent_runs: list[AutonomousLaneRun] | None = None,
    ) -> None:
        self._policy = policy
        self._recent_runs = recent_runs or []

    def evaluate(
        self, candidate: AutonomousImprovementCandidate
    ) -> CandidateEvaluation:
        evaluation = CandidateEvaluation(candidate_id=candidate.candidate_id)
        checks: dict[str, bool] = {}
        reasons: list[str] = []

        checks["risk_is_low"] = candidate.risk_class == self._policy.allowed_risk
        if not checks["risk_is_low"]:
            reasons.append(f"risk_class={candidate.risk_class}, required={self._policy.allowed_risk}")

        checks["template_exists"] = bool(candidate.matching_template_id)
        if self._policy.require_template and not checks["template_exists"]:
            reasons.append("no matching template found")

        checks["template_confidence_met"] = (
            candidate.template_confidence >= self._policy.require_template_confidence
        )
        if self._policy.require_template and not checks["template_confidence_met"]:
            reasons.append(
                f"template confidence {candidate.template_confidence:.2f} < "
                f"required {self._policy.require_template_confidence:.2f}"
            )

        checks["agent_reliability_met"] = (
            candidate.agent_reliability >= self._policy.require_agent_reliability
        )
        if not checks["agent_reliability_met"]:
            reasons.append(
                f"agent reliability {candidate.agent_reliability:.2f} < "
                f"required {self._policy.require_agent_reliability:.2f}"
            )

        checks["validation_exists"] = bool(candidate.validation_method)
        if self._policy.require_validation and not checks["validation_exists"]:
            reasons.append("no validation method defined")

        has_rollback = bool(candidate.rollback_method) or candidate.non_mutating
        checks["rollback_or_non_mutating"] = has_rollback
        if self._policy.require_rollback_or_non_mutating and not has_rollback:
            reasons.append("mutating action with no rollback method")

        sensitive = _has_sensitive_content(candidate)
        checks["no_sensitive_content"] = sensitive is None
        if sensitive:
            reasons.append(sensitive)

        checks["file_count_ok"] = (
            len(candidate.affected_files) <= self._policy.max_file_changes_per_execution
        )
        if not checks["file_count_ok"]:
            reasons.append(
                f"affects {len(candidate.affected_files)} files, "
                f"max {self._policy.max_file_changes_per_execution}"
            )

        checks["has_evidence"] = bool(candidate.evidence)
        if not checks["has_evidence"]:
            reasons.append("no objective evidence")

        checks["not_duplicate"] = not self._is_duplicate(candidate)
        if not checks["not_duplicate"]:
            reasons.append("duplicate of recently executed action")

        checks["not_in_cooldown"] = not self._in_cooldown(candidate)
        if not checks["not_in_cooldown"]:
            reasons.append("template or file in cooldown period")

        evaluation.policy_checks = checks

        if all(checks.values()):
            evaluation.decision = LaneDecision.ELIGIBLE
        elif candidate.risk_class != self._policy.allowed_risk:
            if candidate.risk_class in ("high", "critical"):
                evaluation.decision = LaneDecision.BLOCKED
            else:
                evaluation.decision = LaneDecision.APPROVAL_REQUIRED
        elif sensitive:
            evaluation.decision = LaneDecision.BLOCKED
        else:
            evaluation.decision = LaneDecision.RECOMMENDED

        evaluation.block_reasons = reasons
        return evaluation

    def _is_duplicate(self, candidate: AutonomousImprovementCandidate) -> bool:
        for run in self._recent_runs:
            if run.status != LaneRunStatus.COMPLETED:
                continue
            if not run.selected_candidate:
                continue
            if (
                run.selected_candidate.entity_id == candidate.entity_id
                and run.selected_candidate.source == candidate.source
                and candidate.entity_id
            ):
                return True
        return False

    def _in_cooldown(self, candidate: AutonomousImprovementCandidate) -> bool:
        now = time.time()
        template_cooldown = self._policy.cooldown_minutes_per_template * 60
        file_cooldown = self._policy.cooldown_minutes_per_file * 60

        for run in self._recent_runs:
            if run.status != LaneRunStatus.COMPLETED:
                continue
            if not run.selected_candidate:
                continue
            age = now - run.completed_at
            if (
                candidate.matching_template_id
                and run.selected_candidate.matching_template_id == candidate.matching_template_id
                and age < template_cooldown
            ):
                return True
            for f in candidate.affected_files:
                if f in (run.selected_candidate.affected_files or []) and age < file_cooldown:
                    return True
        return False


# ---------------------------------------------------------------------------
# Autonomous Lane Runner
# ---------------------------------------------------------------------------


class AutonomousImprovementLane:
    """Bounded autonomous lane for LOW-risk template-guided improvements."""

    def __init__(
        self,
        adapter: PlanExecutionAdapter,
        template_registry: TemplateRegistry,
        agent_capability_model: AgentCapabilityModel,
        composition_engine: CompositionEngine | None = None,
        policy: AutonomousLanePolicy | None = None,
        store_dir: str | None = None,
    ) -> None:
        self._adapter = adapter
        self._templates = template_registry
        self._acm = agent_capability_model
        self._composition = composition_engine or CompositionEngine()
        self._policy = policy or AutonomousLanePolicy()
        self._store_dir = store_dir or os.path.join(
            _REPO_ROOT, "data", "umh", "autonomous_lane"
        )
        self._runs: list[AutonomousLaneRun] = []
        self._selector = AutonomousCandidateSelector(
            template_registry=self._templates,
            agent_capability_model=self._acm,
        )
        self._evaluator = AutonomousPolicyEvaluator(
            policy=self._policy,
            recent_runs=self._runs,
        )
        self._load_runs()

    def _load_runs(self) -> None:
        runs_path = os.path.join(self._store_dir, "runs.jsonl")
        if not os.path.isfile(runs_path):
            return
        try:
            with open(runs_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    run = AutonomousLaneRun(
                        run_id=data.get("run_id", ""),
                        status=LaneRunStatus(data.get("status", "dry_run")),
                        started_at=data.get("started_at", 0),
                        completed_at=data.get("completed_at", 0),
                    )
                    self._runs.append(run)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load autonomous lane runs: %s", e)

    def _persist_run(self, run: AutonomousLaneRun) -> None:
        os.makedirs(self._store_dir, exist_ok=True)
        runs_path = os.path.join(self._store_dir, "runs.jsonl")
        with open(runs_path, "a") as f:
            f.write(json.dumps(run.to_dict(), default=str) + "\n")

    @property
    def policy(self) -> AutonomousLanePolicy:
        return self._policy

    @property
    def recent_runs(self) -> list[AutonomousLaneRun]:
        return self._runs[-20:]

    def get_run(self, run_id: str) -> AutonomousLaneRun | None:
        for r in reversed(self._runs):
            if r.run_id == run_id:
                return r
        return None

    def dry_run(
        self,
        step_executors_factory: Callable | None = None,
    ) -> AutonomousLaneRun:
        run = AutonomousLaneRun(policy=self._policy)
        run.status = LaneRunStatus.DRY_RUN

        candidates = self._selector.build_candidates(
            max_candidates=self._policy.max_candidates_per_run,
        )
        run.candidates = candidates

        for c in candidates:
            evaluation = self._evaluator.evaluate(c)
            run.evaluations.append(evaluation)

        eligible = run.eligible_candidates
        if eligible:
            best = max(eligible, key=lambda c: c.selection_score)
            run.selected_candidate = best

            try:
                intent = CompositionIntent(
                    description=best.description,
                    priority="normal",
                    source="autonomous_lane",
                )
                constraints = [
                    CompositionConstraint(
                        name="low_risk_only",
                        description="Only LOW risk actions",
                        hard=True,
                    ),
                    CompositionConstraint(
                        name="reversible_required",
                        description="Must be reversible or non-mutating",
                        hard=True,
                    ),
                ]
                plan = self._composition.compose(intent, constraints=constraints)
                run.plan_id = plan.id

                if plan.overall_risk in (RiskClass.HIGH, RiskClass.CRITICAL):
                    run.governance_dry_run = "blocked_high_risk"
                else:
                    executable = self._adapter.convert_plan(plan)
                    run.executable_id = executable.id
                    high_risk_steps = [
                        s for s in executable.steps
                        if s.risk_level in ("high", "critical")
                    ]
                    if high_risk_steps:
                        run.governance_dry_run = "blocked_step_risk"
                    else:
                        run.governance_dry_run = "passed"
                        run.rollback_available = best.reversible or best.non_mutating

            except Exception as exc:
                run.governance_dry_run = "error"
                run.error = str(exc)[:200]
                logger.warning("Dry-run governance failed: %s", exc)
        else:
            run.status = LaneRunStatus.NO_ELIGIBLE

        run.completed_at = time.time()
        self._persist_run(run)
        self._runs.append(run)
        return run

    def run_once(
        self,
        step_executors_factory: Callable | None = None,
    ) -> AutonomousLaneRun:
        run = AutonomousLaneRun(policy=self._policy)

        candidates = self._selector.build_candidates(
            max_candidates=self._policy.max_candidates_per_run,
        )
        run.candidates = candidates

        for c in candidates:
            evaluation = self._evaluator.evaluate(c)
            run.evaluations.append(evaluation)

        eligible = run.eligible_candidates
        if not eligible:
            run.status = LaneRunStatus.NO_ELIGIBLE
            run.completed_at = time.time()
            self._persist_run(run)
            self._runs.append(run)
            return run

        best = max(eligible, key=lambda c: c.selection_score)
        run.selected_candidate = best

        if best.matching_template_id:
            tpl = self._templates.get_template(best.matching_template_id)
            if tpl:
                run.template_confidence_before = tpl.confidence

        profile = self._acm.get_profile(best.required_agent_type)
        if profile:
            run.agent_reliability_before = profile.overall_reliability

        try:
            run.status = LaneRunStatus.EXECUTING

            intent = CompositionIntent(
                description=best.description,
                priority="normal",
                source="autonomous_lane",
            )
            constraints = [
                CompositionConstraint(
                    name="low_risk_only",
                    description="Only LOW risk actions",
                    hard=True,
                ),
                CompositionConstraint(
                    name="reversible_required",
                    description="Must be reversible or non-mutating",
                    hard=True,
                ),
            ]
            plan = self._composition.compose(intent, constraints=constraints)
            run.plan_id = plan.id

            if plan.overall_risk in (RiskClass.HIGH, RiskClass.CRITICAL):
                run.status = LaneRunStatus.BLOCKED
                run.governance_dry_run = "blocked_high_risk"
                run.error = "Plan risk exceeds LOW threshold"
                run.completed_at = time.time()
                self._persist_run(run)
                self._runs.append(run)
                return run

            executable = self._adapter.convert_plan(plan)
            run.executable_id = executable.id

            high_risk_steps = [
                s for s in executable.steps
                if s.risk_level in ("high", "critical")
            ]
            if high_risk_steps:
                run.status = LaneRunStatus.BLOCKED
                run.governance_dry_run = "blocked_step_risk"
                run.error = f"{len(high_risk_steps)} steps exceed risk threshold"
                run.completed_at = time.time()
                self._persist_run(run)
                self._runs.append(run)
                return run

            run.governance_dry_run = "passed"
            run.rollback_available = best.reversible or best.non_mutating

            step_executors: dict[str, Callable[[], tuple[str, bool]]] = {}
            if step_executors_factory:
                step_executors = step_executors_factory(best, plan)

            executed = self._adapter.execute_plan(
                executable, step_executors=step_executors
            )

            if executed.status == ExecutionGraphStatus.COMPLETED:
                run.execution_status = "completed"
                run.validation_result = "success"
                run.status = LaneRunStatus.COMPLETED
            elif executed.status == ExecutionGraphStatus.PARTIALLY_COMPLETED:
                run.execution_status = "partial"
                run.validation_result = "partial"
                run.status = LaneRunStatus.COMPLETED
            else:
                run.execution_status = "failed"
                run.validation_result = "failed"
                run.status = LaneRunStatus.FAILED
                run.error = "Execution failed"

            if best.matching_template_id:
                tpl = self._templates.get_template(best.matching_template_id)
                if tpl:
                    run.template_confidence_after = tpl.confidence

            profile = self._acm.get_profile(best.required_agent_type)
            if profile:
                run.agent_reliability_after = profile.overall_reliability

        except Exception as exc:
            run.status = LaneRunStatus.FAILED
            run.execution_status = "error"
            run.error = str(exc)[:500]
            logger.warning("Autonomous lane execution failed: %s", exc)

        run.completed_at = time.time()
        self._persist_run(run)
        self._runs.append(run)
        return run

    def status(self) -> dict[str, Any]:
        last_run = self._runs[-1] if self._runs else None
        return {
            "lane_active": True,
            "policy": self._policy.to_dict(),
            "total_runs": len(self._runs),
            "completed_runs": sum(
                1 for r in self._runs if r.status == LaneRunStatus.COMPLETED
            ),
            "failed_runs": sum(
                1 for r in self._runs if r.status == LaneRunStatus.FAILED
            ),
            "last_run": last_run.to_dict() if last_run else None,
        }

    def to_dict(self) -> dict[str, Any]:
        return self.status()

    def to_safe_dict(self) -> dict[str, Any]:
        s = self.status()
        if s.get("last_run"):
            last = s["last_run"]
            last.pop("candidates", None)
            last.pop("evaluations", None)
        return s
