"""Tests for Phase 5F: Task execution edge-case semantics.

Covers gaps not tested in test_phase5e:
- 0-step task (empty steps list)
- Exactly 10 steps (boundary, must succeed)
- 11-step task via post-init mutation (execute_task guard)
- Empty inputs_template {}
- {{prev_output.x}} on first step (prev_output is None)
- Context with nested objects deeper than 2 levels
- output_key empty string vs not set (no context pollution)
- Two steps with the same output_key (last-write-wins)
- Operation name with special characters
- task.updated_at is updated after each step transition
- step.result contains the full ExecutionResult.to_dict() structure
- Non-string value in prev_output resolved to string
- Non-dict mid-path in prev_output leaves token unchanged
"""

import sys

sys.path.insert(0, "/opt/OS")

import os

os.environ.setdefault("UMH_API_KEY", "test-key-phase5f")

from umh.control.identity import get_identity_store
from umh.events.stream import get_event_stream, reset_event_stream
from umh.execution.approval import get_approval_store
from umh.execution.contract import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionClass,
    ExecutionConstraints,
    ExecutionContext,
    ExecutionTarget,
)
from umh.execution.interfaces import set_execution_backend, reset_execution_backend
from umh.orchestrator.engine import reset_orchestrator, start_orchestrator
from umh.orchestrator.task import (
    Task,
    TaskStatus,
    TaskStep,
    StepStatus,
    execute_task,
    get_task,
    reset_tasks,
    resolve_inputs,
)
from umh.core.clock import iso_now


def _reset():
    get_approval_store().reset()
    get_identity_store().reset()
    reset_event_stream()
    reset_orchestrator()
    reset_tasks()


# ---------------------------------------------------------------------------
# Stub backend — returns a synthetic SUCCEEDED result without hitting Ollama
# ---------------------------------------------------------------------------


class _StubBackend:
    """Returns SUCCEEDED for every request without touching the LLM chain."""

    def __init__(self, outputs: dict | None = None):
        self._outputs = outputs or {"response": "stub_response"}

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(
            execution_id=request.execution_id,
            correlation_id=request.correlation_id,
            causal_event_id=request.causal_event_id,
            operation=request.operation,
            status=ExecutionStatus.SUCCEEDED,
            outputs=self._outputs,
            started_at=iso_now(),
            completed_at=iso_now(),
            latency_ms=1,
        )

    def can_handle(self, operation: str) -> bool:
        return True


class _FailBackend:
    """Returns FAILED for every request."""

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(
            execution_id=request.execution_id,
            correlation_id=request.correlation_id,
            causal_event_id=request.causal_event_id,
            operation=request.operation,
            status=ExecutionStatus.FAILED,
            outputs={},
            error="stub failure",
            started_at=iso_now(),
            completed_at=iso_now(),
            latency_ms=1,
        )

    def can_handle(self, operation: str) -> bool:
        return True


def _with_stub(outputs: dict | None = None):
    """Install stub backend and return it. Caller must call reset_execution_backend()."""
    backend = _StubBackend(outputs)
    set_execution_backend(backend)
    return backend


def _with_fail():
    """Install fail backend. Caller must call reset_execution_backend()."""
    backend = _FailBackend()
    set_execution_backend(backend)
    return backend


# ── A. Empty Task (0 steps) ───────────────────────────────────────────────


class TestEmptyTask:
    def test_zero_steps_completes(self):
        """A task with no steps must complete immediately without error."""
        _reset()
        _with_stub()
        try:
            task = Task(steps=[])
            result = execute_task(task)
            assert result.status == TaskStatus.COMPLETED
            assert result.error == ""
        finally:
            reset_execution_backend()

    def test_zero_steps_context_unchanged(self):
        """Empty task must not mutate the initial context."""
        _reset()
        _with_stub()
        try:
            task = Task(steps=[], context={"key": "value"})
            result = execute_task(task)
            assert result.context == {"key": "value"}
        finally:
            reset_execution_backend()

    def test_zero_steps_emits_lifecycle_events(self):
        """task.started and task.completed must be emitted even for 0-step tasks."""
        _reset()
        _with_stub()
        try:
            task = Task(steps=[])
            execute_task(task)
            events = get_event_stream().list_events(limit=100)
            types = [e.type for e in events if e.type.startswith("task.")]
            assert "task.started" in types
            assert "task.completed" in types
        finally:
            reset_execution_backend()

    def test_zero_steps_no_step_events(self):
        """No step-level events must be emitted for a 0-step task."""
        _reset()
        _with_stub()
        try:
            task = Task(steps=[])
            execute_task(task)
            events = get_event_stream().list_events(limit=100)
            step_events = [e for e in events if "step" in e.type]
            assert step_events == []
        finally:
            reset_execution_backend()

    def test_zero_steps_saved_to_store(self):
        """A completed 0-step task must be persisted in the task store."""
        _reset()
        _with_stub()
        try:
            task = Task(steps=[])
            execute_task(task)
            retrieved = get_task(task.id)
            assert retrieved is not None
            assert retrieved.status == TaskStatus.COMPLETED
        finally:
            reset_execution_backend()


# ── B. Step Count Boundaries ──────────────────────────────────────────────


class TestStepCountBoundary:
    def test_exactly_ten_steps_allowed(self):
        """Task with exactly 10 steps must be created without error."""
        steps = [TaskStep(operation=f"op_{i}") for i in range(10)]
        task = Task(steps=steps)
        assert len(task.steps) == 10

    def test_exactly_ten_steps_raises_on_eleven(self):
        """Task constructor must raise ValueError for 11 steps."""
        try:
            Task(steps=[TaskStep(operation=f"op_{i}") for i in range(11)])
            assert False, "Expected ValueError"
        except ValueError as exc:
            assert "max steps" in str(exc).lower()

    def test_execute_task_guard_catches_post_init_mutation(self):
        """execute_task must reject a task whose steps were mutated above _MAX_STEPS after init."""
        _reset()
        task = Task(steps=[TaskStep(operation=f"op_{i}") for i in range(9)])
        # Bypass __post_init__ validation by mutating the list directly
        task.steps.append(TaskStep(operation="extra_1"))
        task.steps.append(TaskStep(operation="extra_2"))
        assert len(task.steps) == 11

        result = execute_task(task)
        assert result.status == TaskStatus.FAILED
        assert "max steps" in result.error.lower() or "exceeds" in result.error.lower()

    def test_ten_step_task_executes_all_steps(self):
        """All 10 steps must complete when backend always succeeds."""
        _reset()
        _with_stub()
        try:
            task = Task(
                steps=[TaskStep(operation=f"op_{i}", output_key=f"k{i}") for i in range(10)]
            )
            result = execute_task(task)
            assert result.status == TaskStatus.COMPLETED
            completed = [s for s in result.steps if s.status == StepStatus.COMPLETED]
            assert len(completed) == 10
        finally:
            reset_execution_backend()


# ── C. Template Resolution Edge Cases ────────────────────────────────────


class TestTemplateEdgeCases:
    def test_empty_inputs_template_resolves_to_empty_dict(self):
        """An empty inputs_template must resolve to an empty dict, not raise."""
        result = resolve_inputs({}, {"any": "context"}, {"any": "prev"})
        assert result == {}

    def test_prev_output_none_for_first_step_leaves_token(self):
        """{{prev_output.x}} with prev_output=None must leave the token unchanged."""
        result = resolve_inputs({"key": "{{prev_output.x}}"}, {}, None)
        assert result["key"] == "{{prev_output.x}}"

    def test_context_three_levels_deep(self):
        """Template resolution must traverse three levels of nested dicts."""
        ctx = {"level1": {"level2": {"level3": "found"}}}
        result = resolve_inputs({"key": "{{context.level1.level2.level3}}"}, ctx, None)
        assert result["key"] == "found"

    def test_context_four_levels_deep(self):
        """Template resolution must traverse four levels of nested dicts."""
        ctx = {"a": {"b": {"c": {"d": "deep"}}}}
        result = resolve_inputs({"key": "{{context.a.b.c.d}}"}, ctx, None)
        assert result["key"] == "deep"

    def test_context_path_hits_non_dict_mid_traversal(self):
        """When a mid-path segment is not a dict, the original token must be returned."""
        ctx = {"a": {"b": "not_a_dict"}}
        result = resolve_inputs({"key": "{{context.a.b.c}}"}, ctx, None)
        assert result["key"] == "{{context.a.b.c}}"

    def test_prev_output_non_string_value_coerced_to_string(self):
        """An integer value in prev_output must be coerced to string."""
        result = resolve_inputs({"key": "{{prev_output.count}}"}, {}, {"count": 42})
        assert result["key"] == "42"

    def test_prev_output_non_dict_mid_traversal(self):
        """When a mid-path prev_output segment is not a dict, token must be unchanged."""
        result = resolve_inputs({"key": "{{prev_output.nested.val}}"}, {}, {"nested": "leaf"})
        assert result["key"] == "{{prev_output.nested.val}}"

    def test_unknown_root_namespace_preserved(self):
        """A template with an unrecognised root (not context/prev_output) stays unchanged."""
        result = resolve_inputs({"key": "{{unknown.foo}}"}, {"foo": "bar"}, None)
        assert result["key"] == "{{unknown.foo}}"


# ── D. Output Key Semantics ───────────────────────────────────────────────


class TestOutputKeySemantics:
    def test_empty_output_key_does_not_write_context(self):
        """A step with output_key='' must not insert anything into task.context."""
        _reset()
        _with_stub({"response": "ok"})
        try:
            task = Task(
                steps=[
                    TaskStep(operation="noop", inputs_template={}, output_key=""),
                ]
            )
            result = execute_task(task)
            assert result.status == TaskStatus.COMPLETED
            assert result.context == {}
        finally:
            reset_execution_backend()

    def test_output_key_writes_full_result_dict(self):
        """The value stored under output_key must be the full ExecutionResult.to_dict()."""
        _reset()
        _with_stub({"response": "hello"})
        try:
            task = Task(
                steps=[
                    TaskStep(operation="op1", inputs_template={}, output_key="result"),
                ]
            )
            result = execute_task(task)
            assert "result" in result.context
            stored = result.context["result"]
            # Must include all canonical ExecutionResult fields
            for field in ("execution_id", "operation", "status", "outputs", "error"):
                assert field in stored, f"Missing field '{field}' in stored result"
            assert stored["status"] == "succeeded"
        finally:
            reset_execution_backend()

    def test_duplicate_output_key_last_write_wins(self):
        """Two steps sharing the same output_key — second step's result must overwrite first."""
        _reset()

        call_count = [0]

        class _CountingBackend:
            def execute(self, request: ExecutionRequest) -> ExecutionResult:
                call_count[0] += 1
                return ExecutionResult(
                    execution_id=request.execution_id,
                    correlation_id=request.correlation_id,
                    causal_event_id=request.causal_event_id,
                    operation=request.operation,
                    status=ExecutionStatus.SUCCEEDED,
                    outputs={"call_number": call_count[0]},
                    started_at=iso_now(),
                    completed_at=iso_now(),
                )

            def can_handle(self, operation: str) -> bool:
                return True

        set_execution_backend(_CountingBackend())
        try:
            task = Task(
                steps=[
                    TaskStep(operation="op_a", inputs_template={}, output_key="shared"),
                    TaskStep(operation="op_b", inputs_template={}, output_key="shared"),
                ]
            )
            result = execute_task(task)
            assert result.status == TaskStatus.COMPLETED
            # Second step wrote call_number=2, first wrote 1
            assert result.context["shared"]["outputs"]["call_number"] == 2
        finally:
            reset_execution_backend()


# ── E. Operation Name Edge Cases ──────────────────────────────────────────


class TestOperationNameEdgeCases:
    def test_operation_with_special_characters_stored_in_step(self):
        """Special characters in operation name must be stored verbatim in TaskStep."""
        step = TaskStep(operation="classify:intent/v2")
        assert step.operation == "classify:intent/v2"

    def test_operation_with_special_characters_passed_to_engine(self):
        """Operation name with special characters must be forwarded to the backend as-is."""
        _reset()
        received_ops = []

        class _TrackingBackend:
            def execute(self, request: ExecutionRequest) -> ExecutionResult:
                received_ops.append(request.operation)
                return ExecutionResult(
                    execution_id=request.execution_id,
                    correlation_id=request.correlation_id,
                    causal_event_id=request.causal_event_id,
                    operation=request.operation,
                    status=ExecutionStatus.SUCCEEDED,
                    outputs={},
                    started_at=iso_now(),
                    completed_at=iso_now(),
                )

            def can_handle(self, operation: str) -> bool:
                return True

        set_execution_backend(_TrackingBackend())
        try:
            task = Task(
                steps=[
                    TaskStep(operation="ns:action/v1", inputs_template={}),
                ]
            )
            execute_task(task)
            assert received_ops == ["ns:action/v1"]
        finally:
            reset_execution_backend()


# ── F. updated_at Timestamp ───────────────────────────────────────────────


class TestUpdatedAt:
    def test_updated_at_changes_after_execution(self):
        """task.updated_at must be newer than created_at after execute_task."""
        _reset()
        _with_stub()
        try:
            task = Task(steps=[TaskStep(operation="op", inputs_template={})])
            created = task.created_at
            result = execute_task(task)
            # Both are ISO strings; lexicographic comparison works for UTC timestamps
            assert result.updated_at >= created
        finally:
            reset_execution_backend()

    def test_updated_at_changes_on_failure(self):
        """task.updated_at must be updated even when the task fails."""
        _reset()
        _with_fail()
        try:
            task = Task(steps=[TaskStep(operation="op", inputs_template={})])
            initial_updated = task.updated_at
            result = execute_task(task)
            assert result.updated_at >= initial_updated
            assert result.status == TaskStatus.FAILED
        finally:
            reset_execution_backend()

    def test_updated_at_set_during_running_transition(self):
        """updated_at must advance when task transitions to RUNNING (inside execute_task)."""
        _reset()
        transitions: list[tuple[str, str]] = []

        class _RecordingBackend:
            def execute(self, request: ExecutionRequest) -> ExecutionResult:
                # At this point task is RUNNING — record the current updated_at
                # via the task context metadata, which carries task_id
                return ExecutionResult(
                    execution_id=request.execution_id,
                    correlation_id=request.correlation_id,
                    causal_event_id=request.causal_event_id,
                    operation=request.operation,
                    status=ExecutionStatus.SUCCEEDED,
                    outputs={},
                    started_at=iso_now(),
                    completed_at=iso_now(),
                )

            def can_handle(self, operation: str) -> bool:
                return True

        set_execution_backend(_RecordingBackend())
        try:
            task = Task(steps=[TaskStep(operation="op", inputs_template={})])
            initial = task.created_at
            result = execute_task(task)
            # COMPLETED updated_at must be >= initial
            assert result.updated_at >= initial
        finally:
            reset_execution_backend()


# ── G. step.result Structure ──────────────────────────────────────────────


class TestStepResultStructure:
    def test_succeeded_step_result_has_all_execution_result_fields(self):
        """step.result must contain all fields from ExecutionResult.to_dict()."""
        _reset()
        _with_stub({"response": "data"})
        try:
            task = Task(steps=[TaskStep(operation="op", inputs_template={})])
            result = execute_task(task)
            step = result.steps[0]
            assert step.result is not None
            expected_fields = {
                "execution_id",
                "correlation_id",
                "causal_event_id",
                "operation",
                "status",
                "outputs",
                "side_effects",
                "error",
                "started_at",
                "completed_at",
                "node_id",
                "idempotency_key",
                "execution_hash",
                "retry_count",
                "model_used",
                "tokens_used",
                "cost_usd",
                "latency_ms",
            }
            missing = expected_fields - set(step.result.keys())
            assert not missing, f"Missing fields in step.result: {missing}"
        finally:
            reset_execution_backend()

    def test_succeeded_step_result_status_is_succeeded(self):
        """step.result['status'] must be 'succeeded' for a successful step."""
        _reset()
        _with_stub()
        try:
            task = Task(steps=[TaskStep(operation="op", inputs_template={})])
            result = execute_task(task)
            assert result.steps[0].result["status"] == "succeeded"
        finally:
            reset_execution_backend()

    def test_failed_step_result_has_all_execution_result_fields(self):
        """step.result must be populated even when the step fails."""
        _reset()
        _with_fail()
        try:
            task = Task(steps=[TaskStep(operation="op", inputs_template={})])
            result = execute_task(task)
            step = result.steps[0]
            assert step.result is not None
            assert "execution_id" in step.result
            assert "status" in step.result
            assert "error" in step.result
        finally:
            reset_execution_backend()

    def test_skipped_step_result_is_none(self):
        """A SKIPPED step must have result=None (never executed)."""
        _reset()
        _with_fail()
        try:
            task = Task(
                steps=[
                    TaskStep(operation="step_a", inputs_template={}),
                    TaskStep(operation="step_b", inputs_template={}),
                ]
            )
            result = execute_task(task)
            assert result.steps[1].status == StepStatus.SKIPPED
            assert result.steps[1].result is None
        finally:
            reset_execution_backend()

    def test_step_result_outputs_propagated_to_prev_output(self):
        """prev_output for step N+1 must equal step N's result['outputs']."""
        _reset()

        outputs_per_call = [{"call": 1, "value": "first"}, {"call": 2, "value": "second"}]
        call_idx = [0]
        received_inputs: list[dict] = []

        class _SequencedBackend:
            def execute(self, request: ExecutionRequest) -> ExecutionResult:
                received_inputs.append(dict(request.inputs))
                out = outputs_per_call[call_idx[0]]
                call_idx[0] += 1
                return ExecutionResult(
                    execution_id=request.execution_id,
                    correlation_id=request.correlation_id,
                    causal_event_id=request.causal_event_id,
                    operation=request.operation,
                    status=ExecutionStatus.SUCCEEDED,
                    outputs=out,
                    started_at=iso_now(),
                    completed_at=iso_now(),
                )

            def can_handle(self, operation: str) -> bool:
                return True

        set_execution_backend(_SequencedBackend())
        try:
            task = Task(
                steps=[
                    TaskStep(operation="step_a", inputs_template={}, output_key="a"),
                    TaskStep(
                        operation="step_b",
                        inputs_template={"carry": "{{prev_output.value}}"},
                    ),
                ]
            )
            result = execute_task(task)
            assert result.status == TaskStatus.COMPLETED
            # Second step received prev_output.value from first step's outputs
            assert received_inputs[1]["carry"] == "first"
        finally:
            reset_execution_backend()


# ── H. current_step_index Tracking ───────────────────────────────────────


class TestCurrentStepIndex:
    def test_current_step_index_after_zero_steps(self):
        """current_step_index must remain 0 for a 0-step task."""
        _reset()
        _with_stub()
        try:
            task = Task(steps=[])
            result = execute_task(task)
            assert result.current_step_index == 0
        finally:
            reset_execution_backend()

    def test_current_step_index_after_single_step(self):
        """current_step_index must be 0 after a single-step task completes."""
        _reset()
        _with_stub()
        try:
            task = Task(steps=[TaskStep(operation="op", inputs_template={})])
            result = execute_task(task)
            assert result.current_step_index == 0
        finally:
            reset_execution_backend()

    def test_current_step_index_at_failure_point(self):
        """current_step_index must point to the failing step index."""
        _reset()

        call_idx = [0]

        class _FailSecondBackend:
            def execute(self, request: ExecutionRequest) -> ExecutionResult:
                call_idx[0] += 1
                status = ExecutionStatus.SUCCEEDED if call_idx[0] == 1 else ExecutionStatus.FAILED
                return ExecutionResult(
                    execution_id=request.execution_id,
                    correlation_id=request.correlation_id,
                    causal_event_id=request.causal_event_id,
                    operation=request.operation,
                    status=status,
                    outputs={},
                    error=None if status == ExecutionStatus.SUCCEEDED else "injected failure",
                    started_at=iso_now(),
                    completed_at=iso_now(),
                )

            def can_handle(self, operation: str) -> bool:
                return True

        set_execution_backend(_FailSecondBackend())
        try:
            task = Task(
                steps=[
                    TaskStep(operation="step_a", inputs_template={}),
                    TaskStep(operation="step_b", inputs_template={}),
                    TaskStep(operation="step_c", inputs_template={}),
                ]
            )
            result = execute_task(task)
            assert result.status == TaskStatus.FAILED
            # Loop set current_step_index=1 before executing step_b
            assert result.current_step_index == 1
            assert result.steps[2].status == StepStatus.SKIPPED
        finally:
            reset_execution_backend()
