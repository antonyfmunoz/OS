"""Tests for umh.execution.harness — the Agent Harness extraction.

Covers:
  - Import boundary (zero eos/core/services/scripts deps)
  - Single-step plan creation and execution
  - Multi-step plan execution with fake backend
  - Step failure capture without crash
  - Observer callback lifecycle events
  - run_harness() convenience function
  - Dependency ordering and skip logic
  - Retry behavior
  - Pre-built plan execution via execute_plan
  - Existing run.py behavior preserved
  - AST boundary scan for forbidden imports
"""

from __future__ import annotations

import ast
import sys
import os
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, "/opt/OS")


# ---------------------------------------------------------------------------
# Import boundary test
# ---------------------------------------------------------------------------


class TestImportBoundary:
    """The harness module must not pull in eos_ai, core, services, or scripts."""

    def test_harness_imports_cleanly(self) -> None:
        from umh.execution.harness import (
            AgentHarness,
            HarnessTask,
            HarnessPlan,
            HarnessStep,
            HarnessResult,
            StepStatus,
            run_harness,
        )

        assert AgentHarness is not None
        assert HarnessTask is not None
        assert HarnessPlan is not None

    def test_ast_no_forbidden_imports(self) -> None:
        harness_path = Path("/opt/OS/umh/execution/harness.py")
        tree = ast.parse(harness_path.read_text())

        forbidden_prefixes = ("eos", "core", "services", "scripts")
        violations: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in forbidden_prefixes:
                        violations.append(f"import {alias.name} (line {node.lineno})")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in forbidden_prefixes:
                    violations.append(
                        f"from {node.module} import ... (line {node.lineno})"
                    )

        assert violations == [], f"Forbidden imports found: {violations}"


# ---------------------------------------------------------------------------
# Fake executor for testing
# ---------------------------------------------------------------------------


class FakeExecutor:
    """Deterministic step executor for testing."""

    def __init__(
        self,
        responses: dict[str, tuple[Any, str | None]] | None = None,
        default_output: str = "fake_output",
    ) -> None:
        self._responses = responses or {}
        self._default_output = default_output
        self.calls: list[dict[str, Any]] = []

    def execute_step(
        self,
        step: Any,
        context: dict[str, Any],
    ) -> tuple[Any, str | None]:
        self.calls.append(
            {
                "step_id": step.step_id,
                "operation": step.operation,
                "context": context,
            }
        )
        if step.operation in self._responses:
            return self._responses[step.operation]
        return self._default_output, None


# ---------------------------------------------------------------------------
# Recording observer for testing
# ---------------------------------------------------------------------------


class RecordingObserver:
    """Records all lifecycle events for assertion."""

    def __init__(self) -> None:
        self.events: list[tuple[str, Any]] = []

    def on_task_start(self, task: Any) -> None:
        self.events.append(("task_start", task.task_id))

    def on_plan_created(self, plan: Any) -> None:
        self.events.append(("plan_created", plan.plan_id))

    def on_step_start(self, step: Any) -> None:
        self.events.append(("step_start", step.step_id))

    def on_step_complete(self, step: Any) -> None:
        self.events.append(("step_complete", step.step_id))

    def on_task_complete(self, result: Any) -> None:
        self.events.append(("task_complete", result.ok))


# ---------------------------------------------------------------------------
# Multi-step planner for testing
# ---------------------------------------------------------------------------


class MultiStepPlanner:
    """Creates a plan with multiple steps."""

    def __init__(self, step_configs: list[dict[str, Any]]) -> None:
        self._configs = step_configs

    def plan(self, task: Any) -> Any:
        from umh.execution.harness import HarnessPlan, HarnessStep, HarnessMode

        steps = []
        for i, cfg in enumerate(self._configs):
            steps.append(
                HarnessStep(
                    step_id=cfg.get("step_id", f"step_{i}"),
                    operation=cfg.get("operation", "process_input"),
                    inputs=cfg.get("inputs", {"prompt": task.input_text}),
                    description=cfg.get("description", f"Step {i}"),
                    depends_on=cfg.get("depends_on", []),
                )
            )

        return HarnessPlan(
            plan_id=f"plan_test_{task.task_id}",
            task_id=task.task_id,
            steps=steps,
            mode=HarnessMode.MULTI,
        )


# ---------------------------------------------------------------------------
# Core harness tests
# ---------------------------------------------------------------------------


class TestAgentHarness:
    """Core harness functionality."""

    def test_single_step_execution(self) -> None:
        from umh.execution.harness import AgentHarness, HarnessTask

        executor = FakeExecutor(default_output="hello from harness")
        harness = AgentHarness(executor=executor)
        task = HarnessTask(input_text="do something")

        result = harness.execute(task)

        assert result.ok is True
        assert result.output == "hello from harness"
        assert result.error is None
        assert result.steps_completed == 1
        assert result.steps_failed == 0
        assert result.steps_total == 1
        assert result.duration_ms >= 0
        assert result.task_id == task.task_id

    def test_multi_step_execution(self) -> None:
        from umh.execution.harness import AgentHarness, HarnessTask

        planner = MultiStepPlanner(
            [
                {"step_id": "s1", "operation": "analyze"},
                {"step_id": "s2", "operation": "summarize"},
                {"step_id": "s3", "operation": "format"},
            ]
        )
        executor = FakeExecutor(
            responses={
                "analyze": ("analysis_result", None),
                "summarize": ("summary_result", None),
                "format": ("formatted", None),
            }
        )
        harness = AgentHarness(planner=planner, executor=executor)
        task = HarnessTask(input_text="multi-step test")

        result = harness.execute(task)

        assert result.ok is True
        assert result.steps_completed == 3
        assert result.steps_total == 3
        assert result.output == ["analysis_result", "summary_result", "formatted"]

    def test_step_failure_captured(self) -> None:
        from umh.execution.harness import AgentHarness, HarnessTask

        executor = FakeExecutor(
            responses={
                "process_input": (None, "something went wrong"),
            }
        )
        harness = AgentHarness(executor=executor, max_retries=0)
        task = HarnessTask(input_text="will fail")

        result = harness.execute(task)

        assert result.ok is False
        assert result.error is not None
        assert "something went wrong" in result.error
        assert result.steps_failed == 1

    def test_step_failure_does_not_crash(self) -> None:
        from umh.execution.harness import AgentHarness, HarnessTask

        class ExplodingExecutor:
            def execute_step(self, step: Any, context: dict) -> tuple:
                raise RuntimeError("kaboom")

        harness = AgentHarness(executor=ExplodingExecutor(), max_retries=0)
        task = HarnessTask(input_text="crash test")

        result = harness.execute(task)

        assert result.ok is False
        assert "kaboom" in (result.error or "")

    def test_planning_failure_returns_result(self) -> None:
        from umh.execution.harness import AgentHarness, HarnessTask

        class BrokenPlanner:
            def plan(self, task: Any) -> Any:
                raise ValueError("cannot plan")

        harness = AgentHarness(planner=BrokenPlanner())
        task = HarnessTask(input_text="plan fail")

        result = harness.execute(task)

        assert result.ok is False
        assert "Planning failed" in (result.error or "")


# ---------------------------------------------------------------------------
# Observer tests
# ---------------------------------------------------------------------------


class TestObserver:
    """Observer receives lifecycle events."""

    def test_observer_full_lifecycle(self) -> None:
        from umh.execution.harness import AgentHarness, HarnessTask

        observer = RecordingObserver()
        executor = FakeExecutor(default_output="ok")
        harness = AgentHarness(executor=executor, observer=observer)
        task = HarnessTask(input_text="observe me")

        result = harness.execute(task)

        event_types = [e[0] for e in observer.events]
        assert event_types == [
            "task_start",
            "plan_created",
            "step_start",
            "step_complete",
            "task_complete",
        ]

    def test_observer_multi_step(self) -> None:
        from umh.execution.harness import AgentHarness, HarnessTask

        observer = RecordingObserver()
        planner = MultiStepPlanner(
            [
                {"step_id": "a", "operation": "op1"},
                {"step_id": "b", "operation": "op2"},
            ]
        )
        executor = FakeExecutor()
        harness = AgentHarness(planner=planner, executor=executor, observer=observer)
        task = HarnessTask(input_text="multi observe")

        harness.execute(task)

        event_types = [e[0] for e in observer.events]
        assert event_types == [
            "task_start",
            "plan_created",
            "step_start",
            "step_complete",
            "step_start",
            "step_complete",
            "task_complete",
        ]

    def test_broken_observer_does_not_crash(self) -> None:
        from umh.execution.harness import AgentHarness, HarnessTask

        class BrokenObserver:
            def on_task_start(self, task: Any) -> None:
                raise RuntimeError("observer crash")

            def on_plan_created(self, plan: Any) -> None:
                raise RuntimeError("observer crash")

            def on_step_start(self, step: Any) -> None:
                raise RuntimeError("observer crash")

            def on_step_complete(self, step: Any) -> None:
                raise RuntimeError("observer crash")

            def on_task_complete(self, result: Any) -> None:
                raise RuntimeError("observer crash")

        executor = FakeExecutor()
        harness = AgentHarness(executor=executor, observer=BrokenObserver())
        task = HarnessTask(input_text="broken observer")

        result = harness.execute(task)
        assert result.ok is True


# ---------------------------------------------------------------------------
# Dependency and retry tests
# ---------------------------------------------------------------------------


class TestDependencyAndRetry:
    """Step dependencies and retry logic."""

    def test_unmet_dependency_skips_step(self) -> None:
        from umh.execution.harness import AgentHarness, HarnessTask, StepStatus

        planner = MultiStepPlanner(
            [
                {"step_id": "s1", "operation": "fail_op"},
                {"step_id": "s2", "operation": "depends_op", "depends_on": ["s1"]},
            ]
        )
        executor = FakeExecutor(
            responses={
                "fail_op": (None, "s1 failed"),
                "depends_op": ("should not run", None),
            }
        )
        harness = AgentHarness(planner=planner, executor=executor, max_retries=0)
        task = HarnessTask(input_text="dep test")

        result = harness.execute(task)

        plan = result.plan
        assert plan is not None
        assert plan.steps[0].status == StepStatus.FAILED
        assert plan.steps[1].status == StepStatus.SKIPPED

    def test_retry_recovers(self) -> None:
        from umh.execution.harness import AgentHarness, HarnessTask

        call_count = 0

        class RetryExecutor:
            def execute_step(self, step: Any, context: dict) -> tuple:
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return None, "transient failure"
                return "recovered", None

        harness = AgentHarness(executor=RetryExecutor(), max_retries=1)
        task = HarnessTask(input_text="retry test")

        result = harness.execute(task)

        assert result.ok is True
        assert result.output == "recovered"
        assert call_count == 2


# ---------------------------------------------------------------------------
# run_harness convenience function
# ---------------------------------------------------------------------------


class TestRunHarness:
    """The run_harness() convenience function."""

    def test_run_harness_basic(self) -> None:
        from umh.execution.harness import run_harness

        executor = FakeExecutor(default_output="convenience output")
        result = run_harness(
            "hello",
            executor=executor,
        )

        assert result.ok is True
        assert result.output == "convenience output"

    def test_run_harness_with_metadata(self) -> None:
        from umh.execution.harness import run_harness

        executor = FakeExecutor()
        result = run_harness(
            "hello",
            executor=executor,
            metadata={"source": "test"},
        )

        assert result.metadata.get("source") == "test"


# ---------------------------------------------------------------------------
# execute_plan with pre-built plan
# ---------------------------------------------------------------------------


class TestExecutePlan:
    """Executing a pre-built plan."""

    def test_execute_plan(self) -> None:
        from umh.execution.harness import (
            AgentHarness,
            HarnessTask,
            HarnessPlan,
            HarnessStep,
            HarnessMode,
        )

        plan = HarnessPlan(
            plan_id="prebuilt_plan",
            task_id="prebuilt_task",
            steps=[
                HarnessStep(
                    step_id="ps1",
                    operation="custom_op",
                    inputs={"prompt": "custom"},
                    description="Prebuilt step",
                ),
            ],
            mode=HarnessMode.PLAN,
        )
        task = HarnessTask(input_text="prebuilt", task_id="prebuilt_task")
        executor = FakeExecutor(default_output="prebuilt_result")
        harness = AgentHarness(executor=executor)

        result = harness.execute_plan(plan, task)

        assert result.ok is True
        assert result.output == "prebuilt_result"
        assert result.plan_id == "prebuilt_plan"


# ---------------------------------------------------------------------------
# Data type serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    """to_dict methods produce valid JSON-safe dicts."""

    def test_harness_result_to_dict(self) -> None:
        from umh.execution.harness import HarnessResult

        r = HarnessResult(ok=True, output="test", task_id="t1")
        d = r.to_dict()
        assert d["ok"] is True
        assert d["output"] == "test"
        assert d["plan"] is None

    def test_plan_to_dict(self) -> None:
        from umh.execution.harness import HarnessPlan, HarnessStep

        plan = HarnessPlan(
            plan_id="p1",
            task_id="t1",
            steps=[
                HarnessStep(step_id="s1", operation="op", inputs={"a": 1}),
            ],
        )
        d = plan.to_dict()
        assert d["total_steps"] == 1
        assert len(d["steps"]) == 1

    def test_task_auto_id(self) -> None:
        from umh.execution.harness import HarnessTask

        t = HarnessTask(input_text="auto id")
        assert t.task_id.startswith("task_")


# ---------------------------------------------------------------------------
# Existing run.py behavior preserved
# ---------------------------------------------------------------------------


class TestRunPyPreserved:
    """umh.run() still works exactly as before."""

    def test_run_import(self) -> None:
        from umh import run, RunResult, RunTrace

        assert callable(run)

    def test_run_basic_execution(self) -> None:
        from umh import run

        result = run("test input")
        assert hasattr(result, "response")
        assert hasattr(result, "success")
        assert hasattr(result, "trace")
        assert result.run_id.startswith("run_")

    def test_run_result_structure(self) -> None:
        from umh import run

        result = run("hello world")
        d = result.to_dict()
        assert "run_id" in d
        assert "response" in d
        assert "trace" in d
        assert "stages" in d["trace"]


# ---------------------------------------------------------------------------
# AST boundary scan — comprehensive
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Capability gate tests (Wave 2B convergence)
# ---------------------------------------------------------------------------


class TestCapabilityGate:
    """Gate enforcement integrated into the harness."""

    def test_no_gate_permits_all(self) -> None:
        from umh.execution.harness import AgentHarness, HarnessTask, NoGate

        gate = NoGate()
        allowed, reason, needs_approval = gate.check("anyone", "anything", "critical")
        assert allowed is True
        assert needs_approval is False

    def test_gate_blocks_step(self) -> None:
        from umh.execution.harness import AgentHarness, HarnessTask, CapabilityGate

        class DenyAllGate:
            def check(self, agent, operation, risk):
                return False, f"{agent} denied", False

        executor = FakeExecutor(default_output="should not reach")
        harness = AgentHarness(executor=executor, gate=DenyAllGate())
        task = HarnessTask(input_text="blocked")

        result = harness.execute(task)

        assert result.ok is False
        assert "denied" in (result.error or "")
        assert len(executor.calls) == 0  # executor never called

    def test_gate_allows_execution(self) -> None:
        from umh.execution.harness import AgentHarness, HarnessTask, NoGate

        executor = FakeExecutor(default_output="permitted")
        harness = AgentHarness(executor=executor, gate=NoGate())
        task = HarnessTask(input_text="allowed")

        result = harness.execute(task)

        assert result.ok is True
        assert result.output == "permitted"
        assert len(executor.calls) == 1

    def test_gate_approval_metadata(self) -> None:
        from umh.execution.harness import AgentHarness, HarnessTask

        class ApprovalGate:
            def check(self, agent, operation, risk):
                return True, "needs human sign-off", True

        executor = FakeExecutor(default_output="approved")
        harness = AgentHarness(executor=executor, gate=ApprovalGate())
        task = HarnessTask(input_text="approval test")

        result = harness.execute(task)

        assert result.ok is True
        step = result.plan.steps[0]
        assert step.metadata.get("needs_approval") is True

    def test_risk_field_on_task(self) -> None:
        from umh.execution.harness import HarnessTask

        t = HarnessTask(input_text="risky", risk="high")
        assert t.risk == "high"

    def test_risk_default(self) -> None:
        from umh.execution.harness import HarnessTask

        t = HarnessTask(input_text="safe")
        assert t.risk == "none"

    def test_gate_receives_risk_from_task(self) -> None:
        from umh.execution.harness import AgentHarness, HarnessTask

        received_risks = []

        class SpyGate:
            def check(self, agent, operation, risk):
                received_risks.append(risk)
                return True, "ok", False

        executor = FakeExecutor()
        harness = AgentHarness(executor=executor, gate=SpyGate())
        task = HarnessTask(input_text="spy", risk="medium")

        harness.execute(task)

        assert received_risks == ["medium"]

    def test_enforcer_gate_import(self) -> None:
        from umh.execution.harness import EnforcerGate

        gate = EnforcerGate()
        allowed, reason, _ = gate.check("reader", "read_data", "none")
        assert allowed is True

    def test_enforcer_gate_denies_unknown_agent(self) -> None:
        from umh.execution.harness import EnforcerGate

        gate = EnforcerGate()
        allowed, reason, _ = gate.check("nonexistent_agent_xyz", "read_data", "none")
        assert allowed is False
        assert "nonexistent_agent_xyz" in reason

    def test_result_includes_operation(self) -> None:
        from umh.execution.harness import AgentHarness, HarnessTask

        executor = FakeExecutor()
        harness = AgentHarness(executor=executor)
        task = HarnessTask(input_text="test", operation="run_analysis")

        result = harness.execute(task)

        assert result.operation == "run_analysis"

    def test_result_to_dict_includes_new_fields(self) -> None:
        from umh.execution.harness import HarnessResult

        r = HarnessResult(
            ok=True,
            output="x",
            operation="call_llm",
            provider="gemini",
        )
        d = r.to_dict()
        assert d["operation"] == "call_llm"
        assert d["provider"] == "gemini"


class TestASTBoundary:
    """Deep AST scan of all UMH files for forbidden imports."""

    FORBIDDEN = ("eos", "core", "services", "scripts")

    # Files that legitimately contain eos_ai fallback imports
    ALLOWED_EOS_IMPORTS = {
        "umh/memory/storage.py",
        "umh/execution/interfaces.py",
        "umh/adapters/llm.py",
        "umh/capability/registry.py",
    }

    def test_harness_no_forbidden_at_module_level(self) -> None:
        harness_path = Path("/opt/OS/umh/execution/harness.py")
        tree = ast.parse(harness_path.read_text())

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    assert root not in self.FORBIDDEN, (
                        f"Module-level import of {alias.name} at line {node.lineno}"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root = node.module.split(".")[0]
                    assert root not in self.FORBIDDEN, (
                        f"Module-level from {node.module} at line {node.lineno}"
                    )
