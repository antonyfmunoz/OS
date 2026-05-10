"""Tests for Phase 5F: Approval Flow in Multi-Step Tasks.

Verifies the current behavior when an approval-requiring step appears inside
a Task executed via execute_task().

BLOCKER DOCUMENTED BELOW — read before adding pause/resume logic.

──────────────────────────────────────────────────────────────────────
BLOCKER: Task-level pause/resume is NOT supported.

When a task step triggers REQUIRES_APPROVAL (e.g. computer_click without
an approval_id), execute() returns ExecutionResult(status=REJECTED).
execute_task() treats any non-SUCCEEDED status as a hard stop:

    if result.status != ExecutionStatus.SUCCEEDED:
        step.status = StepStatus.FAILED          # step is permanently failed
        task.status = TaskStatus.FAILED           # task is permanently failed
        remaining steps → StepStatus.SKIPPED
        return task                               # no way to resume

The orchestrator's builtin:replay_on_approval rule fires ONLY at the
individual ExecutionRequest level. It re-executes the single request that
was stored via orchestrator.store_pending_request(). That replay is
invisible to the Task; the Task has already returned FAILED with remaining
steps SKIPPED.

Can the current architecture support "pause task, approve, resume"?
NO — not without structural additions:

    1. Task-level pause state: TaskStatus needs a PAUSED/AWAITING_APPROVAL
       variant. execute_task() must detect REQUIRES_APPROVAL (via
       result.outputs.get("requires_approval")) and break out of the loop
       without marking the task FAILED.

    2. Task step retry: After the approval is granted and the step re-runs
       via the orchestrator replay, execute_task() must be able to re-enter
       at the failed step index (task.current_step_index) rather than
       starting from step 0.

    3. Approval → task linkage: The pending_request stored by the orchestrator
       is keyed on execution_id, not on task_id. The task needs to store the
       approval_id so the resume path can find it.

Is it safe to add now?
    DEFER. It requires changing:
      - TaskStatus enum (new PAUSED state)
      - execute_task() control flow (detect REQUIRES_APPROVAL, not just !SUCCEEDED)
      - Orchestrator replay action (notify task store on completion)
      - execute_task() re-entry path (resume from current_step_index)
    These are medium-risk changes that touch confirmed-working components.
    Add only after the approval flow itself is stable and fully tested.
──────────────────────────────────────────────────────────────────────

Test coverage:
  A. Task with a side_effect/computer step requiring approval → FAILED
  B. Step status FAILED, remaining steps SKIPPED
  C. Approval request created and visible in store
  D. Error message contains "approval" or the operation name
  E. Step result outputs contain requires_approval=True
  F. Task with all llm_call steps succeeds (guard not involved)
"""

import sys
import os

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase5f-approval")
os.environ.setdefault("UMH_APPROVAL_BACKEND", "memory")

from umh.events.stream import get_event_stream, reset_event_stream
from umh.execution.approval import get_approval_store, reset_approval_store
from umh.orchestrator.engine import reset_orchestrator
from umh.orchestrator.task import (
    Task,
    TaskStatus,
    TaskStep,
    StepStatus,
    execute_task,
    reset_tasks,
)


def _reset() -> None:
    reset_approval_store()
    reset_event_stream()
    reset_orchestrator()
    reset_tasks()


# ── A. Task fails deterministically on approval-requiring step ────


class TestApprovalRequiredBlocksTask:
    def test_task_status_is_paused_when_guard_requires_approval(self):
        """A task containing a computer_click step returns PAUSED (Phase 5G)."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="computer_click",
                    inputs_template={"x": 100, "y": 200},
                    execution_class="side_effect",
                )
            ]
        )
        result = execute_task(task)
        assert result.status == TaskStatus.PAUSED

    def test_approval_requiring_step_status_is_waiting_approval(self):
        """The step that triggered approval shows status=WAITING_APPROVAL (Phase 5G)."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="computer_click",
                    inputs_template={"x": 10, "y": 20},
                    execution_class="side_effect",
                )
            ]
        )
        result = execute_task(task)
        assert result.steps[0].status == StepStatus.WAITING_APPROVAL

    def test_remaining_steps_pending_after_approval_block(self):
        """Steps after the approval-blocked step remain PENDING (Phase 5G)."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="computer_click",
                    inputs_template={"x": 10, "y": 20},
                    execution_class="side_effect",
                ),
                TaskStep(
                    operation="summarize",
                    inputs_template={
                        "prompt": "should not run",
                        "system_prompt": "",
                        "max_tokens": 100,
                    },
                ),
                TaskStep(
                    operation="classify_intent",
                    inputs_template={
                        "prompt": "also pending",
                        "system_prompt": "",
                        "max_tokens": 100,
                    },
                ),
            ]
        )
        result = execute_task(task)
        assert result.status == TaskStatus.PAUSED
        assert result.steps[0].status == StepStatus.WAITING_APPROVAL
        assert result.steps[1].status == StepStatus.PENDING
        assert result.steps[2].status == StepStatus.PENDING

    def test_middle_step_approval_pauses_leaving_later_pending(self):
        """First step succeeds; middle step triggers approval; last step is PENDING (Phase 5G)."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="classify_intent",
                    inputs_template={"prompt": "hello", "system_prompt": "", "max_tokens": 100},
                    output_key="step1",
                ),
                TaskStep(
                    operation="computer_click",
                    inputs_template={"x": 50, "y": 60},
                    execution_class="side_effect",
                ),
                TaskStep(
                    operation="summarize",
                    inputs_template={
                        "prompt": "not yet reached",
                        "system_prompt": "",
                        "max_tokens": 100,
                    },
                ),
            ]
        )
        result = execute_task(task)
        assert result.status == TaskStatus.PAUSED
        assert result.steps[0].status == StepStatus.COMPLETED
        assert result.steps[1].status == StepStatus.WAITING_APPROVAL
        assert result.steps[2].status == StepStatus.PENDING


# ── B. Approval created in store ──────────────────────────────────


class TestApprovalCreatedInStore:
    def test_approval_request_created_in_store(self):
        """The approval store holds a pending request after the task fails."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="computer_click",
                    inputs_template={"x": 10, "y": 20},
                    execution_class="side_effect",
                )
            ]
        )
        execute_task(task)
        store = get_approval_store()
        pending = store.list_pending()
        assert len(pending) == 1

    def test_approval_request_operation_matches_step(self):
        """The approval request has the correct operation name."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="computer_click",
                    inputs_template={"x": 10, "y": 20},
                    execution_class="side_effect",
                )
            ]
        )
        execute_task(task)
        store = get_approval_store()
        pending = store.list_pending()
        assert pending[0].operation == "computer_click"

    def test_approval_id_present_in_step_result_outputs(self):
        """The step result outputs contain requires_approval=True and a valid approval_id."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="computer_click",
                    inputs_template={"x": 10, "y": 20},
                    execution_class="side_effect",
                )
            ]
        )
        result = execute_task(task)
        outputs = result.steps[0].result.get("outputs", {})
        assert outputs.get("requires_approval") is True
        approval_id = outputs.get("approval_id", "")
        assert approval_id.startswith("approval_")

    def test_approval_id_in_store_matches_step_result(self):
        """The approval_id in the step result resolves to the stored pending request."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="computer_click",
                    inputs_template={"x": 10, "y": 20},
                    execution_class="side_effect",
                )
            ]
        )
        result = execute_task(task)
        outputs = result.steps[0].result.get("outputs", {})
        approval_id = outputs.get("approval_id")

        store = get_approval_store()
        req = store.get(approval_id)
        assert req is not None
        assert req.operation == "computer_click"

    def test_two_approval_requiring_steps_create_one_approval(self):
        """Only the first blocked step creates an approval; the second is SKIPPED."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="computer_click",
                    inputs_template={"x": 1, "y": 2},
                    execution_class="side_effect",
                ),
                TaskStep(
                    operation="computer_type",
                    inputs_template={"text": "hello"},
                    execution_class="side_effect",
                ),
            ]
        )
        execute_task(task)
        store = get_approval_store()
        pending = store.list_pending()
        # First step blocked → one approval; second step was SKIPPED before it ran
        assert len(pending) == 1


# ── C. Error message contains useful information ──────────────────


class TestApprovalErrorMessage:
    def test_paused_reason_contains_info(self):
        """paused_reason has approval context (Phase 5G replaces task.error)."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="computer_click",
                    inputs_template={"x": 10, "y": 20},
                    execution_class="side_effect",
                )
            ]
        )
        result = execute_task(task)
        assert result.paused_reason != ""

    def test_paused_reason_mentions_approval(self):
        """paused_reason contains 'approval' or 'requires' (Phase 5G)."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="computer_click",
                    inputs_template={"x": 10, "y": 20},
                    execution_class="side_effect",
                )
            ]
        )
        result = execute_task(task)
        reason = result.paused_reason.lower()
        assert "approval" in reason or "requires" in reason

    def test_step_result_error_mentions_approval(self):
        """step.result['error'] contains 'approval'."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="computer_click",
                    inputs_template={"x": 10, "y": 20},
                    execution_class="side_effect",
                )
            ]
        )
        result = execute_task(task)
        step_error = result.steps[0].result.get("error", "")
        assert "approval" in step_error.lower()


# ── D. Pure llm_call task is unaffected by the guard ─────────────


class TestLLMCallTaskUnaffected:
    def test_single_llm_call_step_succeeds(self):
        """A task with execution_class=llm_call (default) succeeds — guard skipped."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="classify_intent",
                    inputs_template={"prompt": "hello", "system_prompt": "", "max_tokens": 100},
                )
            ]
        )
        result = execute_task(task)
        assert result.status == TaskStatus.COMPLETED
        assert result.steps[0].status == StepStatus.COMPLETED

    def test_multi_llm_call_task_succeeds(self):
        """A task with multiple llm_call steps completes fully — no approval needed."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="classify_intent",
                    inputs_template={"prompt": "hello", "system_prompt": "", "max_tokens": 100},
                    output_key="s1",
                ),
                TaskStep(
                    operation="summarize",
                    inputs_template={"prompt": "world", "system_prompt": "", "max_tokens": 100},
                    output_key="s2",
                ),
            ]
        )
        result = execute_task(task)
        assert result.status == TaskStatus.COMPLETED
        assert result.steps[0].status == StepStatus.COMPLETED
        assert result.steps[1].status == StepStatus.COMPLETED
        assert "s1" in result.context
        assert "s2" in result.context

    def test_no_approvals_created_for_llm_task(self):
        """llm_call tasks never touch the approval store."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="classify_intent",
                    inputs_template={"prompt": "hello", "system_prompt": "", "max_tokens": 100},
                ),
                TaskStep(
                    operation="summarize",
                    inputs_template={"prompt": "world", "system_prompt": "", "max_tokens": 100},
                ),
            ]
        )
        execute_task(task)
        store = get_approval_store()
        assert store.list_pending() == []


# ── E. Events are emitted correctly even when blocked ────────────


class TestApprovalBlockedTaskEvents:
    def test_task_started_event_emitted(self):
        """task.started event fires even when the task will fail on approval."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="computer_click",
                    inputs_template={"x": 10, "y": 20},
                    execution_class="side_effect",
                )
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        started = [e for e in events if e.type == "task.started"]
        assert len(started) == 1
        assert started[0].payload["task_id"] == task.id

    def test_task_paused_event_emitted_on_approval_block(self):
        """task.paused event fires when step requires approval (Phase 5G)."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="computer_click",
                    inputs_template={"x": 10, "y": 20},
                    execution_class="side_effect",
                )
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        paused = [e for e in events if e.type == "task.paused"]
        assert len(paused) == 1
        assert paused[0].payload["task_id"] == task.id
        assert "approval_id" in paused[0].payload

    def test_approval_created_event_emitted(self):
        """approval.created event is published when the step is blocked."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="computer_click",
                    inputs_template={"x": 10, "y": 20},
                    execution_class="side_effect",
                )
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        approval_events = [e for e in events if e.type == "approval.created"]
        assert len(approval_events) == 1
        assert approval_events[0].payload["operation"] == "computer_click"
