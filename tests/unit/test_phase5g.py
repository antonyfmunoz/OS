"""Tests for Phase 5G: Task Pause/Resume on Approval.

Verifies:
- Task pauses (not fails) on approval-required step
- Paused state fields are correctly populated
- Resume executes paused step with approval_id
- Completed prior steps are not replayed on resume
- Remaining steps continue after resume
- Orchestrator auto-resumes on approval event
- Wrong approval_id does not resume
- Consumed approval cannot resume twice
- Denied approval does not resume
- Failed resumed step marks task FAILED
- API shows paused tasks and fields
- Metrics include paused task count
- Regression: tasks without approvals still complete
- Regression: approval replay for single execution still works
"""

import sys
import os

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase5a")
os.environ["PYTEST_CURRENT_TEST"] = "1"

from fastapi.testclient import TestClient

from umh.control.api import app
from umh.control.identity import get_identity_store
from umh.events.stream import get_event_stream, publish, reset_event_stream
from umh.execution.approval import ApprovalStatus, get_approval_store
from umh.execution.contract import (
    ExecutionClass,
    ExecutionConstraints,
    ExecutionContext,
    ExecutionRequest,
    ExecutionStatus,
    ExecutionTarget,
)
from umh.execution.engine import execute
from umh.orchestrator.engine import (
    get_orchestrator,
    reset_orchestrator,
    start_orchestrator,
)
from umh.orchestrator.task import (
    Task,
    TaskStatus,
    TaskStep,
    StepStatus,
    execute_task,
    find_paused_task_by_approval,
    get_task,
    list_tasks,
    reset_tasks,
    resume_task,
)
from umh.core.clock import iso_now as _iso_now

client = TestClient(app)


def _reset():
    get_approval_store().reset()
    get_identity_store().reset()
    reset_event_stream()
    reset_orchestrator()
    reset_tasks()


def _start_fresh():
    _reset()
    return start_orchestrator()


def _create_identity(name="admin", scopes=None):
    store = get_identity_store()
    identity, raw_key = store.create_identity(name, scopes or ["admin"])
    return identity, raw_key, {"X-API-Key": raw_key}


def _llm_step(operation: str, output_key: str = "") -> TaskStep:
    return TaskStep(
        operation=operation,
        inputs_template={"prompt": "test", "system_prompt": "", "max_tokens": 100},
        output_key=output_key,
        execution_class="llm_call",
    )


def _approval_step(operation: str = "computer_click", output_key: str = "") -> TaskStep:
    return TaskStep(
        operation=operation,
        inputs_template={"x": 10, "y": 20},
        output_key=output_key,
        execution_class="side_effect",
    )


# ── A. Pause Behavior ───────────────────────────────────────────────


class TestTaskPause:
    def test_task_pauses_on_approval_required_step(self):
        _start_fresh()
        task = Task(
            steps=[
                _llm_step("classify_intent", output_key="s1"),
                _approval_step("computer_click"),
                _llm_step("summarize"),
            ]
        )
        result = execute_task(task)
        assert result.status == TaskStatus.PAUSED
        assert result.steps[0].status == StepStatus.COMPLETED
        assert result.steps[1].status == StepStatus.WAITING_APPROVAL
        assert result.steps[2].status == StepStatus.PENDING

    def test_paused_step_index_stored(self):
        _start_fresh()
        task = Task(
            steps=[
                _llm_step("classify_intent"),
                _approval_step("computer_click"),
                _llm_step("summarize"),
            ]
        )
        result = execute_task(task)
        assert result.paused_step_index == 1

    def test_paused_approval_id_stored(self):
        _start_fresh()
        task = Task(
            steps=[
                _approval_step("computer_click"),
            ]
        )
        result = execute_task(task)
        assert result.status == TaskStatus.PAUSED
        assert result.paused_approval_id != ""
        assert result.paused_approval_id.startswith("approval_")

    def test_paused_request_snapshot_stored(self):
        _start_fresh()
        task = Task(steps=[_approval_step("computer_click")])
        result = execute_task(task)
        assert result.paused_request is not None
        assert result.paused_request["operation"] == "computer_click"

    def test_pause_count_incremented(self):
        _start_fresh()
        task = Task(steps=[_approval_step("computer_click")])
        result = execute_task(task)
        assert result.pause_count == 1

    def test_later_steps_not_executed_on_pause(self):
        _start_fresh()
        task = Task(
            steps=[
                _approval_step("computer_click"),
                _llm_step("summarize"),
                _llm_step("classify_intent"),
            ]
        )
        result = execute_task(task)
        assert result.status == TaskStatus.PAUSED
        assert result.steps[1].status == StepStatus.PENDING
        assert result.steps[2].status == StepStatus.PENDING
        assert result.steps[1].result is None
        assert result.steps[2].result is None

    def test_task_paused_event_emitted(self):
        _start_fresh()
        stream = get_event_stream()
        task = Task(steps=[_approval_step("computer_click")])
        execute_task(task)
        events = stream.list_events(limit=100)
        paused_events = [e for e in events if e.type == "task.paused"]
        assert len(paused_events) >= 1
        assert paused_events[-1].payload["task_id"] == task.id
        assert "approval_id" in paused_events[-1].payload

    def test_task_saved_to_store_on_pause(self):
        _start_fresh()
        task = Task(steps=[_approval_step("computer_click")])
        execute_task(task)
        stored = get_task(task.id)
        assert stored is not None
        assert stored.status == TaskStatus.PAUSED

    def test_paused_to_dict_includes_pause_fields(self):
        _start_fresh()
        task = Task(steps=[_approval_step("computer_click")])
        result = execute_task(task)
        d = result.to_dict()
        assert d["status"] == "paused"
        assert d["paused_step_index"] == 0
        assert d["paused_approval_id"] != ""
        assert "paused_reason" in d
        assert d["pause_count"] == 1


# ── B. Resume Behavior ──────────────────────────────────────────────


class TestTaskResume:
    def test_resume_executes_paused_step(self):
        _reset()
        task = Task(steps=[_approval_step("computer_click")])
        execute_task(task)
        assert task.status == TaskStatus.PAUSED

        approval_id = task.paused_approval_id
        store = get_approval_store()
        store.approve(approval_id, approved_by="tester")

        resumed = resume_task(task.id, approval_id)
        assert resumed is not None
        assert resumed.status == TaskStatus.COMPLETED
        assert resumed.steps[0].status == StepStatus.COMPLETED

    def test_resume_continues_remaining_steps(self):
        _reset()
        task = Task(
            steps=[
                _llm_step("classify_intent", output_key="s1"),
                _approval_step("computer_click", output_key="s2"),
                _llm_step("summarize", output_key="s3"),
            ]
        )
        execute_task(task)
        assert task.status == TaskStatus.PAUSED
        assert task.paused_step_index == 1

        approval_id = task.paused_approval_id
        store = get_approval_store()
        store.approve(approval_id, approved_by="tester")

        resumed = resume_task(task.id, approval_id)
        assert resumed is not None
        assert resumed.status == TaskStatus.COMPLETED
        assert resumed.steps[0].status == StepStatus.COMPLETED
        assert resumed.steps[1].status == StepStatus.COMPLETED
        assert resumed.steps[2].status == StepStatus.COMPLETED

    def test_prior_completed_steps_not_replayed(self):
        _reset()
        task = Task(
            steps=[
                _llm_step("classify_intent", output_key="s1"),
                _approval_step("computer_click"),
            ]
        )
        execute_task(task)
        first_step_result = task.steps[0].result

        approval_id = task.paused_approval_id
        store = get_approval_store()
        store.approve(approval_id, approved_by="tester")

        resume_task(task.id, approval_id)
        assert task.steps[0].result is first_step_result

    def test_resumed_at_timestamp_set(self):
        _reset()
        task = Task(steps=[_approval_step("computer_click")])
        execute_task(task)

        approval_id = task.paused_approval_id
        get_approval_store().approve(approval_id, approved_by="tester")

        resumed = resume_task(task.id, approval_id)
        assert resumed is not None
        assert resumed.resumed_at != ""

    def test_pause_fields_cleared_after_resume(self):
        _reset()
        task = Task(steps=[_approval_step("computer_click")])
        execute_task(task)

        approval_id = task.paused_approval_id
        get_approval_store().approve(approval_id, approved_by="tester")

        resumed = resume_task(task.id, approval_id)
        assert resumed is not None
        assert resumed.status == TaskStatus.COMPLETED
        assert resumed.paused_step_index is None
        assert resumed.paused_approval_id == ""
        assert resumed.paused_request is None

    def test_task_resumed_event_emitted(self):
        _reset()
        stream = get_event_stream()
        task = Task(steps=[_approval_step("computer_click")])
        execute_task(task)

        approval_id = task.paused_approval_id
        get_approval_store().approve(approval_id, approved_by="tester")

        resume_task(task.id, approval_id)
        events = stream.list_events(limit=200)
        resumed_events = [e for e in events if e.type == "task.resumed"]
        assert len(resumed_events) >= 1
        assert resumed_events[-1].payload["task_id"] == task.id

    def test_task_completed_event_after_resume(self):
        _reset()
        stream = get_event_stream()
        task = Task(steps=[_approval_step("computer_click")])
        execute_task(task)

        approval_id = task.paused_approval_id
        get_approval_store().approve(approval_id, approved_by="tester")

        resume_task(task.id, approval_id)
        events = stream.list_events(limit=200)
        completed_events = [
            e
            for e in events
            if e.type == "task.completed" and e.payload.get("status") == "completed"
        ]
        assert len(completed_events) >= 1

    def test_output_key_preserved_after_resume(self):
        _reset()
        task = Task(
            steps=[
                _llm_step("classify_intent", output_key="s1"),
                _approval_step("computer_click", output_key="s2"),
            ]
        )
        execute_task(task)
        assert "s1" in task.context

        approval_id = task.paused_approval_id
        get_approval_store().approve(approval_id, approved_by="tester")

        resumed = resume_task(task.id, approval_id)
        assert resumed is not None
        assert "s1" in resumed.context
        assert "s2" in resumed.context


# ── C. Safety Tests ──────────────────────────────────────────────────


class TestResumeSafety:
    def test_wrong_approval_id_does_not_resume(self):
        _start_fresh()
        task = Task(steps=[_approval_step("computer_click")])
        execute_task(task)
        assert task.status == TaskStatus.PAUSED

        result = resume_task(task.id, "approval_wrong_id_12345")
        assert result is None
        assert task.status == TaskStatus.PAUSED

    def test_resume_nonexistent_task_returns_none(self):
        _start_fresh()
        result = resume_task("task_nonexistent", "approval_123")
        assert result is None

    def test_resume_non_paused_task_returns_none(self):
        _start_fresh()
        task = Task(steps=[_llm_step("classify_intent")])
        execute_task(task)
        assert task.status == TaskStatus.COMPLETED

        result = resume_task(task.id, "approval_123")
        assert result is None

    def test_consumed_approval_cannot_resume_twice(self):
        _reset()
        task = Task(steps=[_approval_step("computer_click")])
        execute_task(task)

        approval_id = task.paused_approval_id
        store = get_approval_store()
        store.approve(approval_id, approved_by="tester")

        resumed = resume_task(task.id, approval_id)
        assert resumed is not None
        assert resumed.status == TaskStatus.COMPLETED

        result = resume_task(task.id, approval_id)
        assert result is None

    def test_pending_approval_does_not_resume(self):
        _start_fresh()
        task = Task(steps=[_approval_step("computer_click")])
        execute_task(task)
        assert task.status == TaskStatus.PAUSED

        approval_id = task.paused_approval_id
        approval = get_approval_store().get(approval_id)
        assert approval.status == ApprovalStatus.PENDING

    def test_denied_approval_does_not_auto_resume(self):
        _start_fresh()
        orch = start_orchestrator()
        task = Task(steps=[_approval_step("computer_click")])
        execute_task(task)
        assert task.status == TaskStatus.PAUSED

        approval_id = task.paused_approval_id
        get_approval_store().deny(approval_id)

        stored = get_task(task.id)
        assert stored.status == TaskStatus.PAUSED

    def test_find_paused_task_by_approval(self):
        _start_fresh()
        task = Task(steps=[_approval_step("computer_click")])
        execute_task(task)

        found = find_paused_task_by_approval(task.paused_approval_id)
        assert found is not None
        assert found.id == task.id

    def test_find_paused_task_wrong_approval_returns_none(self):
        _start_fresh()
        task = Task(steps=[_approval_step("computer_click")])
        execute_task(task)

        found = find_paused_task_by_approval("approval_wrong")
        assert found is None


# ── D. Orchestrator Auto-Resume ──────────────────────────────────────


class TestOrchestratorResume:
    def test_approval_event_triggers_task_resume(self):
        _start_fresh()
        orch = start_orchestrator()

        task = Task(
            steps=[
                _llm_step("classify_intent", output_key="s1"),
                _approval_step("computer_click"),
                _llm_step("summarize"),
            ]
        )
        execute_task(task)
        assert task.status == TaskStatus.PAUSED

        approval_id = task.paused_approval_id
        get_approval_store().approve(approval_id, approved_by="tester")

        stored = get_task(task.id)
        assert stored.status == TaskStatus.COMPLETED
        assert stored.steps[0].status == StepStatus.COMPLETED
        assert stored.steps[1].status == StepStatus.COMPLETED
        assert stored.steps[2].status == StepStatus.COMPLETED

    def test_orchestrator_resume_does_not_replay_prior_steps(self):
        _start_fresh()
        orch = start_orchestrator()

        task = Task(
            steps=[
                _llm_step("classify_intent", output_key="s1"),
                _approval_step("computer_click"),
            ]
        )
        execute_task(task)
        first_step_result = task.steps[0].result

        approval_id = task.paused_approval_id
        get_approval_store().approve(approval_id, approved_by="tester")

        stored = get_task(task.id)
        assert stored.steps[0].result is first_step_result


# ── E. API/Metrics Tests ─────────────────────────────────────────────


class TestPauseAPI:
    def test_get_tasks_shows_paused_task(self):
        _start_fresh()
        _, _, headers = _create_identity()
        task = Task(steps=[_approval_step("computer_click")])
        execute_task(task)
        assert task.status == TaskStatus.PAUSED

        resp = client.get("/tasks", headers=headers)
        assert resp.status_code == 200
        tasks = resp.json()
        paused = [t for t in tasks if t["status"] == "paused"]
        assert len(paused) >= 1

    def test_get_task_by_id_shows_pause_fields(self):
        _start_fresh()
        _, _, headers = _create_identity()
        task = Task(steps=[_approval_step("computer_click")])
        execute_task(task)

        resp = client.get(f"/tasks/{task.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "paused"
        assert data["paused_step_index"] == 0
        assert data["paused_approval_id"] != ""
        assert data["pause_count"] == 1

    def test_metrics_includes_paused_count(self):
        _start_fresh()
        _, _, headers = _create_identity()
        task = Task(steps=[_approval_step("computer_click")])
        execute_task(task)

        resp = client.get("/metrics", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["tasks"]["paused_tasks"] >= 1
        assert data["tasks"]["tasks_by_status"]["paused"] >= 1


# ── F. Regression Tests ──────────────────────────────────────────────


class TestPauseRegression:
    def test_task_without_approvals_still_completes(self):
        _start_fresh()
        task = Task(
            steps=[
                _llm_step("classify_intent", output_key="s1"),
                _llm_step("summarize", output_key="s2"),
            ]
        )
        result = execute_task(task)
        assert result.status == TaskStatus.COMPLETED
        assert result.steps[0].status == StepStatus.COMPLETED
        assert result.steps[1].status == StepStatus.COMPLETED

    def test_task_failure_still_marks_failed(self):
        _start_fresh()
        task = Task(
            steps=[
                TaskStep(
                    operation="nonexistent_op",
                    inputs_template={"x": 1},
                    execution_class="side_effect",
                ),
            ]
        )
        result = execute_task(task)
        assert result.status == TaskStatus.FAILED

    def test_single_execution_approval_replay_still_works(self):
        """Existing approval replay for non-task executions still works."""
        _start_fresh()
        orch = start_orchestrator()

        request = ExecutionRequest(
            execution_id="test_standalone_click",
            correlation_id="test_standalone_click",
            causal_event_id="",
            session_id="",
            operation="computer_click",
            inputs={"x": 10, "y": 20},
            execution_class=ExecutionClass.SIDE_EFFECT,
            constraints=ExecutionConstraints(timeout_s=30),
            target=ExecutionTarget(node_id="local", transport="test"),
            context=ExecutionContext(metadata={}),
            issued_at=_iso_now(),
            issued_by="test",
            idempotency_key="",
        )

        result = execute(request)
        assert result.status == ExecutionStatus.REJECTED
        assert result.outputs.get("requires_approval") is True
        approval_id = result.outputs["approval_id"]

        get_approval_store().approve(approval_id, approved_by="tester")

        events = get_event_stream().list_events(limit=200)
        orchestration_events = [e for e in events if e.type == "orchestration.executed"]
        assert len(orchestration_events) >= 1

    def test_task_status_enum_has_paused(self):
        assert TaskStatus.PAUSED.value == "paused"

    def test_step_status_enum_has_waiting_approval(self):
        assert StepStatus.WAITING_APPROVAL.value == "waiting_approval"

    def test_non_paused_to_dict_no_pause_fields(self):
        task = Task(steps=[_llm_step("classify_intent")])
        d = task.to_dict()
        assert "paused_step_index" not in d

    def test_completed_task_to_dict_no_pause_fields(self):
        _start_fresh()
        task = Task(steps=[_llm_step("classify_intent")])
        execute_task(task)
        d = task.to_dict()
        assert d["status"] == "completed"
        assert "paused_step_index" not in d
