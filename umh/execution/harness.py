"""UMH Agent Harness — multi-step execution orchestration.

The harness coordinates work across agents with capability enforcement:
  1. A HarnessTask arrives (natural language or structured)
  2. A HarnessPlan is created (sequence of HarnessStep instances)
  3. Each step is gated by CapabilityEnforcer (may this agent do this?)
  4. Permitted steps execute through an injectable StepExecutor
  5. Results are collected into a HarnessResult with full trace
  6. Observers receive lifecycle events at every transition

No umh imports. No core imports. No services imports.

Usage:
    from umh.execution.harness import AgentHarness, HarnessTask

    harness = AgentHarness()
    task = HarnessTask(input_text="analyze the data")
    result = harness.execute(task)
    print(result.ok, result.output)
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from umh.core.clock import now_ms as _now_ms


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class HarnessMode(str, Enum):
    SINGLE = "single"
    MULTI = "multi"
    PLAN = "plan"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class HarnessTask:
    """Input to the harness — what needs to be done."""

    input_text: str
    task_id: str = ""
    agent: str = "default"
    operation: str = "process_input"
    authority: str = "analyze"
    risk: str = "none"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.task_id:
            self.task_id = f"task_{uuid.uuid4().hex[:12]}"


@dataclass
class HarnessStep:
    """A single unit of work within a plan."""

    step_id: str
    operation: str
    inputs: dict[str, Any]
    description: str = ""
    depends_on: list[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    output: Any = None
    error: str | None = None
    duration_ms: int = 0
    capability_used: str = ""
    provider: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "operation": self.operation,
            "inputs": self.inputs,
            "description": self.description,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "capability_used": self.capability_used,
            "provider": self.provider,
        }


@dataclass
class HarnessPlan:
    """Ordered sequence of steps to execute."""

    plan_id: str
    task_id: str
    steps: list[HarnessStep] = field(default_factory=list)
    mode: HarnessMode = HarnessMode.SINGLE
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def completed_steps(self) -> int:
        return sum(
            1
            for s in self.steps
            if s.status in (StepStatus.SUCCEEDED, StepStatus.SKIPPED)
        )

    @property
    def failed_steps(self) -> int:
        return sum(1 for s in self.steps if s.status == StepStatus.FAILED)

    @property
    def all_done(self) -> bool:
        return all(
            s.status in (StepStatus.SUCCEEDED, StepStatus.FAILED, StepStatus.SKIPPED)
            for s in self.steps
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "task_id": self.task_id,
            "mode": self.mode.value,
            "total_steps": self.total_steps,
            "completed": self.completed_steps,
            "failed": self.failed_steps,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
        }


@dataclass
class HarnessResult:
    """Canonical return from every harness execution.

    ok/output/error contract. Never raises from public methods.
    """

    ok: bool
    output: Any
    error: str | None = None
    task_id: str = ""
    plan_id: str = ""
    agent: str = ""
    operation: str = ""
    provider: str = ""
    duration_ms: int = 0
    steps_completed: int = 0
    steps_failed: int = 0
    steps_total: int = 0
    plan: HarnessPlan | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "output": self.output,
            "error": self.error,
            "task_id": self.task_id,
            "plan_id": self.plan_id,
            "agent": self.agent,
            "operation": self.operation,
            "provider": self.provider,
            "duration_ms": self.duration_ms,
            "steps_completed": self.steps_completed,
            "steps_failed": self.steps_failed,
            "steps_total": self.steps_total,
            "plan": self.plan.to_dict() if self.plan else None,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Observer protocol — lifecycle callbacks
# ---------------------------------------------------------------------------


@runtime_checkable
class HarnessObserver(Protocol):
    """Receives lifecycle events from the harness."""

    def on_task_start(self, task: HarnessTask) -> None: ...
    def on_plan_created(self, plan: HarnessPlan) -> None: ...
    def on_step_start(self, step: HarnessStep) -> None: ...
    def on_step_complete(self, step: HarnessStep) -> None: ...
    def on_task_complete(self, result: HarnessResult) -> None: ...


class NullObserver:
    """No-op observer — safe default."""

    def on_task_start(self, task: HarnessTask) -> None:
        pass

    def on_plan_created(self, plan: HarnessPlan) -> None:
        pass

    def on_step_start(self, step: HarnessStep) -> None:
        pass

    def on_step_complete(self, step: HarnessStep) -> None:
        pass

    def on_task_complete(self, result: HarnessResult) -> None:
        pass


# ---------------------------------------------------------------------------
# Step executor protocol — how steps actually run
# ---------------------------------------------------------------------------


@runtime_checkable
class StepExecutor(Protocol):
    """Executes a single harness step.

    Implementations route through UMH capability/execution or any
    other backend. The harness itself is backend-agnostic.
    """

    def execute_step(
        self,
        step: HarnessStep,
        context: dict[str, Any],
    ) -> tuple[Any, str | None]:
        """Execute a step, returning (output, error_or_none)."""
        ...


class DefaultStepExecutor:
    """Routes steps through UMH's capability router and execution engine.

    Falls back to echo output if no real backend is configured.
    """

    def execute_step(
        self,
        step: HarnessStep,
        context: dict[str, Any],
    ) -> tuple[Any, str | None]:
        try:
            return self._execute_via_umh(step, context)
        except Exception as e:
            return None, str(e)

    def _execute_via_umh(
        self,
        step: HarnessStep,
        context: dict[str, Any],
    ) -> tuple[Any, str | None]:
        from umh.capability.router import route_to_capability
        from umh.governance.authority import AuthorityLevel, check_governance

        authority_str = context.get("authority", "analyze")
        authority_map = {
            "observe": AuthorityLevel.OBSERVE,
            "analyze": AuthorityLevel.ANALYZE,
            "act": AuthorityLevel.ACT,
            "execute": AuthorityLevel.EXECUTE,
        }
        authority = authority_map.get(authority_str, AuthorityLevel.ANALYZE)

        gov = check_governance(
            operation=step.operation,
            authority_level=authority,
            constraints=step.inputs.get("constraints", {}),
        )
        if not gov.allowed:
            return None, f"Governance blocked: {gov.reason}"

        routing = route_to_capability(
            step.operation,
            step.inputs.get("constraints"),
        )
        if routing.selected is None:
            return None, "No capability available for operation"

        step.capability_used = routing.selected.name

        from umh.adapters.base import get_adapter

        if routing.selected.capability_type == "llm":
            adapter = get_adapter("llm")
            prompt = step.inputs.get("prompt", step.inputs.get("input_text", ""))
            system = step.inputs.get("system_prompt", "")
            response = adapter.generate(prompt, system=system)
            return response, None

        return f"[{routing.selected.name}] Processed: {step.operation}", None


# ---------------------------------------------------------------------------
# Capability gate — optional pre-step enforcement
# ---------------------------------------------------------------------------


@runtime_checkable
class CapabilityGate(Protocol):
    """Checks whether an agent may perform an operation at a given risk."""

    def check(
        self,
        agent: str,
        operation: str,
        risk: str,
    ) -> tuple[bool, str, bool]:
        """Returns (allowed, reason, needs_approval)."""
        ...


class NoGate:
    """Permits everything — safe default for headless operation."""

    def check(
        self,
        agent: str,
        operation: str,
        risk: str,
    ) -> tuple[bool, str, bool]:
        return True, f"{agent} may {operation}", False


class EnforcerGate:
    """CapabilityGate backed by UMH's CapabilityEnforcer + ProfileRegistry."""

    def __init__(self) -> None:
        from umh.governance.capability import (
            CapabilityEnforcer,
            ProfileRegistry,
            default_registry,
            operation_for_action_type,
        )

        self._enforcer = CapabilityEnforcer()
        self._registry: ProfileRegistry = default_registry()
        self._op_for = operation_for_action_type

    def register_profile(self, profile: Any) -> None:
        self._registry.register(profile)

    def check(
        self,
        agent: str,
        operation: str,
        risk: str,
    ) -> tuple[bool, str, bool]:
        try:
            profile = self._registry.get(agent)
        except KeyError:
            return False, f"no capability profile for agent {agent!r}", False

        op_kind = self._op_for(operation)
        decision = self._enforcer.may(profile, op_kind, risk)
        return decision.allowed, decision.reason, decision.needs_approval


# ---------------------------------------------------------------------------
# Planner protocol — how tasks become plans
# ---------------------------------------------------------------------------


@runtime_checkable
class TaskPlanner(Protocol):
    """Decomposes a HarnessTask into a HarnessPlan."""

    def plan(self, task: HarnessTask) -> HarnessPlan: ...


class DefaultTaskPlanner:
    """Wraps every task as a single-step plan.

    For multi-step decomposition, inject an LLM-backed planner.
    """

    def plan(self, task: HarnessTask) -> HarnessPlan:
        step = HarnessStep(
            step_id=f"step_{uuid.uuid4().hex[:8]}",
            operation=task.operation,
            inputs={
                "input_text": task.input_text,
                "prompt": task.input_text,
            },
            description=f"Execute: {task.operation}",
        )
        return HarnessPlan(
            plan_id=f"plan_{uuid.uuid4().hex[:12]}",
            task_id=task.task_id,
            steps=[step],
            mode=HarnessMode.SINGLE,
        )


# ---------------------------------------------------------------------------
# The harness
# ---------------------------------------------------------------------------


class AgentHarness:
    """Multi-step execution orchestrator with capability enforcement.

    Coordinates plan creation, step execution, permission gating,
    failure handling, and observer notification. All external
    dependencies are injected via Protocol interfaces.
    """

    def __init__(
        self,
        *,
        planner: TaskPlanner | None = None,
        executor: StepExecutor | None = None,
        observer: HarnessObserver | None = None,
        gate: CapabilityGate | None = None,
        max_retries: int = 1,
    ) -> None:
        self._planner = planner or DefaultTaskPlanner()
        self._executor = executor or DefaultStepExecutor()
        self._observer = observer or NullObserver()
        self._gate = gate or NoGate()
        self._max_retries = max_retries

    @property
    def planner(self) -> TaskPlanner:
        return self._planner

    @property
    def executor(self) -> StepExecutor:
        return self._executor

    @property
    def observer(self) -> HarnessObserver:
        return self._observer

    @property
    def gate(self) -> CapabilityGate:
        return self._gate

    def execute(self, task: HarnessTask) -> HarnessResult:
        """Execute a task through plan → gate → step execution → result.

        Never raises. Always returns a HarnessResult.
        """
        t0 = _now_ms()

        self._notify_safe(self._observer.on_task_start, task)

        try:
            plan = self._planner.plan(task)
        except Exception as e:
            return self._fail(task, f"Planning failed: {e}", t0)

        self._notify_safe(self._observer.on_plan_created, plan)

        for step in plan.steps:
            if not self._deps_met(step, plan):
                step.status = StepStatus.SKIPPED
                step.error = "Dependency not met"
                self._notify_safe(self._observer.on_step_complete, step)
                continue

            self._run_step(step, task, plan)

        result = self._build_result(task, plan, t0)
        self._notify_safe(self._observer.on_task_complete, result)
        return result

    def execute_plan(self, plan: HarnessPlan, task: HarnessTask) -> HarnessResult:
        """Execute a pre-built plan (for callers who build plans externally)."""
        t0 = _now_ms()

        self._notify_safe(self._observer.on_task_start, task)
        self._notify_safe(self._observer.on_plan_created, plan)

        for step in plan.steps:
            if not self._deps_met(step, plan):
                step.status = StepStatus.SKIPPED
                step.error = "Dependency not met"
                self._notify_safe(self._observer.on_step_complete, step)
                continue

            self._run_step(step, task, plan)

        result = self._build_result(task, plan, t0)
        self._notify_safe(self._observer.on_task_complete, result)
        return result

    # ── Internal ────────────────────────────────────────────────────────

    def _run_step(
        self,
        step: HarnessStep,
        task: HarnessTask,
        plan: HarnessPlan,
    ) -> None:
        # Gate check before execution
        allowed, reason, needs_approval = self._gate.check(
            task.agent,
            step.operation,
            task.risk,
        )
        if not allowed:
            step.status = StepStatus.FAILED
            step.error = reason
            self._notify_safe(self._observer.on_step_complete, step)
            return

        if needs_approval:
            step.metadata["needs_approval"] = True
            step.metadata["approval_reason"] = reason

        step.status = StepStatus.RUNNING
        self._notify_safe(self._observer.on_step_start, step)

        context = {
            "task_id": task.task_id,
            "agent": task.agent,
            "authority": task.authority,
            "risk": task.risk,
            "plan_id": plan.plan_id,
            **task.metadata,
        }

        attempts = 0
        while attempts <= self._max_retries:
            step_t0 = _now_ms()
            try:
                output, error = self._executor.execute_step(step, context)
            except Exception as e:
                output, error = None, str(e)

            step.duration_ms += _now_ms() - step_t0

            if error is None:
                step.status = StepStatus.SUCCEEDED
                step.output = output
                break

            attempts += 1
            if attempts > self._max_retries:
                step.status = StepStatus.FAILED
                step.error = error
                step.output = output

        self._notify_safe(self._observer.on_step_complete, step)

    def _build_result(
        self,
        task: HarnessTask,
        plan: HarnessPlan,
        t0: int,
    ) -> HarnessResult:
        return HarnessResult(
            ok=plan.failed_steps == 0,
            output=self._collect_output(plan),
            error=self._collect_errors(plan),
            task_id=task.task_id,
            plan_id=plan.plan_id,
            agent=task.agent,
            operation=task.operation,
            duration_ms=_now_ms() - t0,
            steps_completed=plan.completed_steps,
            steps_failed=plan.failed_steps,
            steps_total=plan.total_steps,
            plan=plan,
            metadata=task.metadata,
        )

    def _deps_met(self, step: HarnessStep, plan: HarnessPlan) -> bool:
        if not step.depends_on:
            return True
        step_map = {s.step_id: s for s in plan.steps}
        return all(
            step_map.get(
                dep_id, HarnessStep(step_id="", operation="", inputs={})
            ).status
            == StepStatus.SUCCEEDED
            for dep_id in step.depends_on
        )

    def _collect_output(self, plan: HarnessPlan) -> Any:
        succeeded = [s for s in plan.steps if s.status == StepStatus.SUCCEEDED]
        if not succeeded:
            return None
        if len(succeeded) == 1:
            return succeeded[0].output
        return [s.output for s in succeeded]

    def _collect_errors(self, plan: HarnessPlan) -> str | None:
        errors = [
            f"{s.step_id}: {s.error}"
            for s in plan.steps
            if s.status == StepStatus.FAILED and s.error
        ]
        return "; ".join(errors) if errors else None

    def _fail(
        self,
        task: HarnessTask,
        error: str,
        t0: int,
    ) -> HarnessResult:
        result = HarnessResult(
            ok=False,
            output=None,
            error=error,
            task_id=task.task_id,
            agent=task.agent,
            operation=task.operation,
            duration_ms=_now_ms() - t0,
        )
        self._notify_safe(self._observer.on_task_complete, result)
        return result

    @staticmethod
    def _notify_safe(callback: Any, *args: Any) -> None:
        try:
            callback(*args)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Public convenience: run_harness
# ---------------------------------------------------------------------------


def run_harness(
    input_text: str,
    *,
    agent: str = "default",
    operation: str = "process_input",
    authority: str = "analyze",
    risk: str = "none",
    planner: TaskPlanner | None = None,
    executor: StepExecutor | None = None,
    observer: HarnessObserver | None = None,
    gate: CapabilityGate | None = None,
    max_retries: int = 1,
    metadata: dict[str, Any] | None = None,
) -> HarnessResult:
    """Convenience entry point — create task + harness and execute."""
    task = HarnessTask(
        input_text=input_text,
        agent=agent,
        operation=operation,
        authority=authority,
        risk=risk,
        metadata=metadata or {},
    )
    harness = AgentHarness(
        planner=planner,
        executor=executor,
        observer=observer,
        gate=gate,
        max_retries=max_retries,
    )
    return harness.execute(task)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


__all__ = [
    "AgentHarness",
    "CapabilityGate",
    "DefaultStepExecutor",
    "DefaultTaskPlanner",
    "EnforcerGate",
    "HarnessMode",
    "HarnessObserver",
    "HarnessPlan",
    "HarnessResult",
    "HarnessStep",
    "HarnessTask",
    "NoGate",
    "NullObserver",
    "StepExecutor",
    "StepStatus",
    "TaskPlanner",
    "run_harness",
]
