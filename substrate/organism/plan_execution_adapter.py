"""Plan Execution Adapter — bridges CompositionPlan to GovernedExecutionSpine.

Converts:
  CompositionPlan → ExecutionGraph (ActionEnvelope DAG) → GovernedExecutionSpine

Supports:
  - Sequential and parallel execution via dependency graph
  - Dependency blocking and failed-node propagation
  - Governance integration (MutationRegistry, SpineGuard, AutonomousGateway)
  - Outcome recording into OutcomeLearningLoop
  - Memory candidate generation into MemoryPromotionPipeline
  - Retry eligibility per step
  - Rollback orchestration

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

from substrate.organism.action_envelope import (
    ActionEnvelope,
    ActionType,
    BlastRadius,
    EnvelopeStatus,
    ExecutionConstraints,
    ReversibilityClass,
    RollbackStrategy,
    VerificationStrategy,
)
from substrate.organism.composition_engine import (
    CompositionPlan,
    CompositionStep,
    GovernanceMode,
    RiskClass,
    StepStatus,
)
from substrate.organism.outcome_learning import (
    OutcomeLearningLoop,
    OutcomeRecord,
    OutcomeStatus,
)
from substrate.organism.memory_promotion import (
    MemoryCategory,
    MemoryEvidence,
    MemoryPromotionPipeline,
)

logger = logging.getLogger(__name__)


class ExecutionGraphStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"
    CANCELLED = "cancelled"


class StepExecutionStatus(str, Enum):
    PENDING = "pending"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"
    BLOCKED_BY_FAILURE = "blocked_by_failure"


_RISK_MAP: dict[str, str] = {
    RiskClass.LOW.value: "low",
    RiskClass.MEDIUM.value: "medium",
    RiskClass.HIGH.value: "high",
    RiskClass.CRITICAL.value: "critical",
}

_ACTION_TYPE_MAP: dict[str, ActionType] = {
    "filesystem": ActionType.FILESYSTEM,
    "container": ActionType.CONTAINER,
    "process": ActionType.PROCESS,
    "network": ActionType.NETWORK,
    "state": ActionType.STATE,
    "graph": ActionType.GRAPH,
    "test": ActionType.TEST,
    "cleanup": ActionType.CLEANUP,
    "ingestion": ActionType.INGESTION,
    "deployment": ActionType.DEPLOYMENT,
}

_BLAST_RADIUS_BY_RISK: dict[str, BlastRadius] = {
    "low": BlastRadius.LOCAL_FILE,
    "medium": BlastRadius.LOCAL_RUNTIME,
    "high": BlastRadius.SINGLE_SERVICE,
    "critical": BlastRadius.MULTI_SERVICE,
}


@dataclass
class ExecutionDependency:
    source_step_id: str
    target_step_id: str
    dep_type: str = "sequential"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source_step_id,
            "target": self.target_step_id,
            "type": self.dep_type,
        }


@dataclass
class ExecutableStep:
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    plan_id: str = ""
    composition_step_id: str = ""
    description: str = ""
    action: str = ""
    risk_level: str = "low"
    governance_mode: str = "autonomous"
    requires_approval: bool = False
    depends_on: list[str] = field(default_factory=list)
    status: StepExecutionStatus = StepExecutionStatus.PENDING
    envelope_id: str = ""
    verification: str = ""
    rollback_plan: str = ""
    evidence_chain: list[str] = field(default_factory=list)
    result_output: str = ""
    result_success: bool = False
    started_at: float = 0.0
    completed_at: float = 0.0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "composition_step_id": self.composition_step_id,
            "description": self.description,
            "action": self.action,
            "risk_level": self.risk_level,
            "governance_mode": self.governance_mode,
            "requires_approval": self.requires_approval,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "envelope_id": self.envelope_id,
            "verification": self.verification,
            "rollback_plan": self.rollback_plan,
            "evidence_chain": self.evidence_chain,
            "result_output": self.result_output[:500],
            "result_success": self.result_success,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }


@dataclass
class ExecutablePlan:
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    source_plan_id: str = ""
    intent: str = ""
    steps: list[ExecutableStep] = field(default_factory=list)
    dependencies: list[ExecutionDependency] = field(default_factory=list)
    overall_risk: str = "low"
    governance_required: str = "autonomous"
    rollback_plan: str = ""
    evidence: list[str] = field(default_factory=list)
    status: ExecutionGraphStatus = ExecutionGraphStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0

    def ready_steps(self) -> list[ExecutableStep]:
        completed_ids = {
            s.composition_step_id for s in self.steps
            if s.status == StepExecutionStatus.COMPLETED
        }
        failed_ids = {
            s.composition_step_id for s in self.steps
            if s.status in (
                StepExecutionStatus.FAILED,
                StepExecutionStatus.BLOCKED_BY_FAILURE,
            )
        }
        changed = True
        while changed:
            changed = False
            for step in self.steps:
                if step.status != StepExecutionStatus.PENDING:
                    continue
                if any(dep in failed_ids for dep in step.depends_on):
                    step.status = StepExecutionStatus.BLOCKED_BY_FAILURE
                    failed_ids.add(step.composition_step_id)
                    changed = True
        ready = []
        for step in self.steps:
            if step.status != StepExecutionStatus.PENDING:
                continue
            if all(dep in completed_ids for dep in step.depends_on):
                ready.append(step)
        return ready

    def is_complete(self) -> bool:
        terminal = {
            StepExecutionStatus.COMPLETED,
            StepExecutionStatus.FAILED,
            StepExecutionStatus.ROLLED_BACK,
            StepExecutionStatus.SKIPPED,
            StepExecutionStatus.BLOCKED_BY_FAILURE,
        }
        return all(s.status in terminal for s in self.steps)

    def success_count(self) -> int:
        return sum(1 for s in self.steps if s.status == StepExecutionStatus.COMPLETED)

    def failure_count(self) -> int:
        return sum(
            1 for s in self.steps
            if s.status in (StepExecutionStatus.FAILED, StepExecutionStatus.BLOCKED_BY_FAILURE)
        )

    def summary(self) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        for s in self.steps:
            status_counts[s.status.value] = status_counts.get(s.status.value, 0) + 1
        return {
            "id": self.id,
            "source_plan_id": self.source_plan_id,
            "intent": self.intent,
            "status": self.status.value,
            "total_steps": len(self.steps),
            "step_status": status_counts,
            "overall_risk": self.overall_risk,
            "governance_required": self.governance_required,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "steps": [s.to_dict() for s in self.steps],
            "dependencies": [d.to_dict() for d in self.dependencies],
            "rollback_plan": self.rollback_plan,
            "evidence": self.evidence,
        }


@dataclass
class ExecutionGraph:
    plans: dict[str, ExecutablePlan] = field(default_factory=dict)

    def add(self, plan: ExecutablePlan) -> None:
        self.plans[plan.id] = plan

    def get(self, plan_id: str) -> ExecutablePlan | None:
        return self.plans.get(plan_id)

    def active_plans(self) -> list[ExecutablePlan]:
        return [
            p for p in self.plans.values()
            if p.status in (ExecutionGraphStatus.PENDING, ExecutionGraphStatus.EXECUTING)
        ]

    def completed_plans(self, limit: int = 20) -> list[ExecutablePlan]:
        completed = [
            p for p in self.plans.values()
            if p.status in (
                ExecutionGraphStatus.COMPLETED,
                ExecutionGraphStatus.FAILED,
                ExecutionGraphStatus.PARTIALLY_COMPLETED,
            )
        ]
        completed.sort(key=lambda p: p.completed_at, reverse=True)
        return completed[:limit]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_plans": len(self.plans),
            "active": len(self.active_plans()),
            "plans": {pid: p.summary() for pid, p in self.plans.items()},
        }


def _infer_action_type(action: str) -> ActionType:
    action_lower = action.lower()
    for keyword, at in _ACTION_TYPE_MAP.items():
        if keyword in action_lower:
            return at
    if any(w in action_lower for w in ("file", "write", "read", "create", "delete", "move")):
        return ActionType.FILESYSTEM
    if any(w in action_lower for w in ("docker", "container", "image")):
        return ActionType.CONTAINER
    if any(w in action_lower for w in ("deploy", "release", "publish")):
        return ActionType.DEPLOYMENT
    if any(w in action_lower for w in ("test", "verify", "check", "validate")):
        return ActionType.TEST
    if any(w in action_lower for w in ("start", "stop", "restart", "run", "execute")):
        return ActionType.PROCESS
    return ActionType.STATE


class PlanExecutionAdapter:
    """Bridges CompositionPlan → ActionEnvelope graph → GovernedExecutionSpine."""

    def __init__(
        self,
        governed_spine: Any = None,
        spine_guard: Any = None,
        autonomous_gateway: Any = None,
        outcome_loop: OutcomeLearningLoop | None = None,
        memory_pipeline: MemoryPromotionPipeline | None = None,
    ) -> None:
        self._spine = governed_spine
        self._spine_guard = spine_guard
        self._gateway = autonomous_gateway
        self._outcome_loop = outcome_loop
        self._memory_pipeline = memory_pipeline
        self._graph = ExecutionGraph()
        self._step_to_envelope: dict[str, ActionEnvelope] = {}

    @property
    def execution_graph(self) -> ExecutionGraph:
        return self._graph

    def convert_plan(self, plan: CompositionPlan) -> ExecutablePlan:
        """Convert a CompositionPlan into an ExecutablePlan with dependency graph."""
        executable = ExecutablePlan(
            source_plan_id=plan.id,
            intent=plan.intent.description if plan.intent else "",
            overall_risk=_RISK_MAP.get(plan.overall_risk.value, "low"),
            governance_required=plan.governance_required.value,
            rollback_plan=plan.rollback_plan,
            evidence=list(plan.evidence),
        )

        for comp_step in plan.steps:
            requires_approval = comp_step.governance_mode != GovernanceMode.AUTONOMOUS
            risk_level = _RISK_MAP.get(comp_step.risk_class.value, "low")

            exec_step = ExecutableStep(
                plan_id=executable.id,
                composition_step_id=comp_step.id,
                description=comp_step.description,
                action=comp_step.action,
                risk_level=risk_level,
                governance_mode=comp_step.governance_mode.value,
                requires_approval=requires_approval,
                depends_on=list(comp_step.depends_on),
                verification=comp_step.verification,
                evidence_chain=list(plan.evidence),
            )
            executable.steps.append(exec_step)

        for comp_step in plan.steps:
            for dep_id in comp_step.depends_on:
                executable.dependencies.append(ExecutionDependency(
                    source_step_id=dep_id,
                    target_step_id=comp_step.id,
                ))

        self._graph.add(executable)
        return executable

    def _build_envelope(
        self,
        step: ExecutableStep,
        plan: ExecutablePlan,
        execute_fn: Callable[[], tuple[str, bool]] | None = None,
    ) -> ActionEnvelope:
        """Build an ActionEnvelope from an ExecutableStep."""
        action_type = _infer_action_type(step.action)
        risk = step.risk_level
        blast = _BLAST_RADIUS_BY_RISK.get(risk, BlastRadius.LOCAL_RUNTIME)

        if risk in ("high", "critical"):
            reversibility = ReversibilityClass.PARTIALLY_REVERSIBLE
        else:
            reversibility = ReversibilityClass.FULLY_REVERSIBLE

        verification = None
        if step.verification:
            verification = VerificationStrategy(
                description=step.verification,
            )

        rollback = None
        if plan.rollback_plan:
            rollback = RollbackStrategy(
                description=plan.rollback_plan,
            )

        def _default_execute() -> tuple[str, bool]:
            return (f"Step '{step.description}' executed (plan_executor)", True)

        envelope = ActionEnvelope(
            intent=step.description,
            action_type=action_type,
            source="plan_executor",
            execute_fn=execute_fn or _default_execute,
            risk_level=risk,
            blast_radius=blast,
            reversibility=reversibility,
            verification=verification,
            rollback=rollback,
            constraints=ExecutionConstraints(
                require_approval=step.requires_approval,
                max_retries=1 if risk in ("low", "medium") else 0,
                timeout_seconds=120.0 if risk in ("high", "critical") else 60.0,
            ),
            metadata={
                "plan_id": step.plan_id,
                "step_id": step.composition_step_id,
                "execution_step_id": step.id,
                "governance_mode": step.governance_mode,
                "risk_level": risk,
            },
        )

        step.envelope_id = envelope.envelope_id
        self._step_to_envelope[step.id] = envelope
        return envelope

    def execute_plan(
        self,
        plan: ExecutablePlan,
        step_executors: dict[str, Callable[[], tuple[str, bool]]] | None = None,
    ) -> ExecutablePlan:
        """Execute an entire plan through the GovernedExecutionSpine.

        Traverses the dependency graph, submitting ready steps to the spine.
        Propagates failures to dependent steps.
        Records outcomes and generates memory candidates.
        """
        if self._spine is None:
            logger.error("Cannot execute plan: no GovernedExecutionSpine configured")
            plan.status = ExecutionGraphStatus.FAILED
            return plan

        plan.status = ExecutionGraphStatus.EXECUTING
        plan.started_at = time.time()
        executors = step_executors or {}

        max_iterations = len(plan.steps) * 2
        iteration = 0

        while not plan.is_complete() and iteration < max_iterations:
            iteration += 1
            ready = plan.ready_steps()

            if not ready:
                pending_non_blocked = [
                    s for s in plan.steps
                    if s.status in (
                        StepExecutionStatus.PENDING,
                        StepExecutionStatus.AWAITING_APPROVAL,
                        StepExecutionStatus.EXECUTING,
                    )
                ]
                if not pending_non_blocked:
                    break
                break

            for step in ready:
                executor = executors.get(step.composition_step_id)
                envelope = self._build_envelope(step, plan, execute_fn=executor)

                if self._spine_guard is not None:
                    guard_result = self._spine_guard.evaluate(envelope)
                    if hasattr(guard_result, "blocked") and guard_result.blocked:
                        step.status = StepExecutionStatus.FAILED
                        step.error = f"SpineGuard blocked: {getattr(guard_result, 'reason', 'policy violation')}"
                        step.completed_at = time.time()
                        self._record_outcome(step, plan)
                        continue

                if self._gateway is not None and step.governance_mode == "autonomous":
                    gateway_result = self._gateway.evaluate(envelope)
                    if hasattr(gateway_result, "blocked") and gateway_result.blocked:
                        step.requires_approval = True
                        envelope.constraints.require_approval = True

                step.status = StepExecutionStatus.EXECUTING
                step.started_at = time.time()

                result_envelope = self._spine.submit(envelope)

                if result_envelope.status == EnvelopeStatus.PROPOSED:
                    step.status = StepExecutionStatus.AWAITING_APPROVAL
                    step.envelope_id = result_envelope.envelope_id
                    continue

                if result_envelope.status == EnvelopeStatus.REJECTED:
                    step.status = StepExecutionStatus.FAILED
                    step.error = result_envelope.rejected_reason
                    step.completed_at = time.time()
                    self._record_outcome(step, plan)
                    continue

                step.result_output = result_envelope.result_output
                step.result_success = result_envelope.result_success
                step.completed_at = time.time()

                if result_envelope.status in (
                    EnvelopeStatus.COMPLETED,
                    EnvelopeStatus.VERIFIED,
                ):
                    step.status = StepExecutionStatus.COMPLETED
                elif result_envelope.status == EnvelopeStatus.ROLLED_BACK:
                    step.status = StepExecutionStatus.ROLLED_BACK
                else:
                    step.status = StepExecutionStatus.FAILED
                    step.error = result_envelope.result_output[:500]

                self._record_outcome(step, plan)

        plan.completed_at = time.time()

        if plan.failure_count() == 0 and plan.success_count() == len(plan.steps):
            plan.status = ExecutionGraphStatus.COMPLETED
        elif plan.success_count() > 0:
            plan.status = ExecutionGraphStatus.PARTIALLY_COMPLETED
        else:
            plan.status = ExecutionGraphStatus.FAILED

        self._generate_memory_candidates(plan)

        return plan

    def check_pending_approvals(self, plan: ExecutablePlan) -> list[ExecutableStep]:
        """Return steps awaiting operator approval."""
        return [
            s for s in plan.steps
            if s.status == StepExecutionStatus.AWAITING_APPROVAL
        ]

    def approve_step(
        self,
        plan: ExecutablePlan,
        step_id: str,
        approved_by: str = "operator",
    ) -> ExecutableStep | None:
        """Approve a pending step and execute it through the spine."""
        step = next(
            (s for s in plan.steps if s.composition_step_id == step_id),
            None,
        )
        if step is None or step.status != StepExecutionStatus.AWAITING_APPROVAL:
            return None

        if self._spine is None:
            return None

        result = self._spine.approve(step.envelope_id, approved_by=approved_by)
        if result is None:
            return None

        step.result_output = result.result_output
        step.result_success = result.result_success
        step.completed_at = time.time()

        if result.status in (EnvelopeStatus.COMPLETED, EnvelopeStatus.VERIFIED):
            step.status = StepExecutionStatus.COMPLETED
        elif result.status == EnvelopeStatus.ROLLED_BACK:
            step.status = StepExecutionStatus.ROLLED_BACK
        else:
            step.status = StepExecutionStatus.FAILED
            step.error = result.result_output[:500]

        self._record_outcome(step, plan)

        if plan.is_complete():
            plan.completed_at = time.time()
            if plan.failure_count() == 0:
                plan.status = ExecutionGraphStatus.COMPLETED
            elif plan.success_count() > 0:
                plan.status = ExecutionGraphStatus.PARTIALLY_COMPLETED
            else:
                plan.status = ExecutionGraphStatus.FAILED
            self._generate_memory_candidates(plan)

        return step

    def _record_outcome(self, step: ExecutableStep, plan: ExecutablePlan) -> None:
        """Record an OutcomeRecord for a completed step."""
        if self._outcome_loop is None:
            return

        if step.status == StepExecutionStatus.COMPLETED:
            status = OutcomeStatus.SUCCESS
        elif step.status == StepExecutionStatus.ROLLED_BACK:
            status = OutcomeStatus.PARTIAL
        elif step.status in (
            StepExecutionStatus.SKIPPED,
            StepExecutionStatus.BLOCKED_BY_FAILURE,
        ):
            status = OutcomeStatus.SKIPPED
        else:
            status = OutcomeStatus.FAILURE

        duration = max(step.completed_at - step.started_at, 0) if step.started_at else 0

        record = OutcomeRecord(
            action_type=step.action or "plan_step",
            plan_id=plan.source_plan_id,
            step_id=step.composition_step_id,
            description=step.description,
            status=status,
            expected_result=step.verification or "step completion",
            actual_result=step.result_output[:500] if step.result_output else "",
            duration_seconds=duration,
            error=step.error,
        )

        self._outcome_loop.record_outcome(record)

    def _generate_memory_candidates(self, plan: ExecutablePlan) -> None:
        """Generate MemoryCandidates for completed plans. Never auto-promotes."""
        if self._memory_pipeline is None:
            return

        if plan.status == ExecutionGraphStatus.COMPLETED:
            self._memory_pipeline.submit_candidate(
                content=(
                    f"Plan '{plan.intent}' completed successfully "
                    f"with {len(plan.steps)} steps"
                ),
                category=MemoryCategory.PATTERN,
                evidence=[
                    MemoryEvidence(
                        source="plan_executor",
                        detail=(
                            f"All {len(plan.steps)} steps succeeded "
                            f"in plan {plan.source_plan_id}"
                        ),
                        confidence=0.8,
                    ),
                ],
                source_action=f"plan_execution:{plan.source_plan_id}",
            )

        elif plan.status == ExecutionGraphStatus.FAILED:
            failed_steps = [
                s for s in plan.steps
                if s.status == StepExecutionStatus.FAILED
            ]
            errors = "; ".join(s.error[:100] for s in failed_steps if s.error)
            self._memory_pipeline.submit_candidate(
                content=f"Plan '{plan.intent}' failed: {errors[:300]}",
                category=MemoryCategory.OBSERVATION,
                evidence=[
                    MemoryEvidence(
                        source="plan_executor",
                        detail=(
                            f"{len(failed_steps)} steps failed "
                            f"in plan {plan.source_plan_id}"
                        ),
                        confidence=0.7,
                    ),
                ],
                source_action=f"plan_execution:{plan.source_plan_id}",
            )

        elif plan.status == ExecutionGraphStatus.PARTIALLY_COMPLETED:
            self._memory_pipeline.submit_candidate(
                content=(
                    f"Plan '{plan.intent}' partially completed: "
                    f"{plan.success_count()}/{len(plan.steps)} steps succeeded"
                ),
                category=MemoryCategory.OBSERVATION,
                evidence=[
                    MemoryEvidence(
                        source="plan_executor",
                        detail=(
                            f"{plan.success_count()} succeeded, "
                            f"{plan.failure_count()} failed "
                            f"in plan {plan.source_plan_id}"
                        ),
                        confidence=0.6,
                    ),
                ],
                source_action=f"plan_execution:{plan.source_plan_id}",
            )

    def get_execution_graph(self, plan_id: str) -> ExecutablePlan | None:
        return self._graph.get(plan_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_graph": self._graph.to_dict(),
            "pending_envelopes": len(self._step_to_envelope),
        }
