"""Tests for Phase 5G: Task Event Observability.

Verifies that every publish() call in execute_task() emits the correct
payload fields, that actor_id/execution_id are propagated to step events,
that event ordering is strict, that failed steps emit the right status,
that skipped steps are visible in task state, and that all events are
accessible via GET /events.

All steps use execution_class="llm_call" to avoid the security guard.
"""

import sys
import os

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase5g")

from fastapi.testclient import TestClient

from umh.control.api import app
from umh.control.identity import get_identity_store
from umh.events.stream import get_event_stream, reset_event_stream
from umh.execution.approval import get_approval_store
from umh.orchestrator.engine import reset_orchestrator, start_orchestrator
from umh.orchestrator.task import (
    StepStatus,
    Task,
    TaskStatus,
    TaskStep,
    execute_task,
    reset_tasks,
)

client = TestClient(app)


def _reset():
    get_approval_store().reset()
    get_identity_store().reset()
    reset_event_stream()
    reset_orchestrator()
    reset_tasks()


def _create_identity(name: str = "admin", scopes: list[str] | None = None):
    store = get_identity_store()
    identity, raw_key = store.create_identity(name, scopes or ["admin"])
    return identity, raw_key, {"X-API-Key": raw_key}


def _llm_step(operation: str = "classify_intent", output_key: str = "") -> dict:
    """Return a step dict using execution_class=llm_call to pass security guard."""
    return {
        "operation": operation,
        "inputs_template": {"prompt": "hi", "system_prompt": "", "max_tokens": 100},
        "execution_class": "llm_call",
        "output_key": output_key,
    }


def _failing_step() -> dict:
    """Return a step dict that will fail at execution (unknown op, side_effect class)."""
    return {
        "operation": "unknown_op_that_does_not_exist",
        "inputs_template": {},
        "execution_class": "side_effect",
    }


# ── A. task.started payload ────────────────────────────────────────────────


class TestTaskStartedPayload:
    def test_task_started_has_task_id(self):
        _reset()
        task = Task(steps=[TaskStep(operation="classify_intent", execution_class="llm_call")])
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        started = [e for e in events if e.type == "task.started"]
        assert len(started) == 1, "Exactly one task.started event expected"
        assert started[0].payload["task_id"] == task.id

    def test_task_started_has_step_count(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(operation="classify_intent", execution_class="llm_call"),
                TaskStep(operation="summarize", execution_class="llm_call"),
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        started = [e for e in events if e.type == "task.started"]
        assert len(started) == 1
        assert started[0].payload["step_count"] == 2

    def test_task_started_actor_id_propagated(self):
        _reset()
        task = Task(
            steps=[TaskStep(operation="classify_intent", execution_class="llm_call")],
            issued_by="actor_test_123",
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        started = [e for e in events if e.type == "task.started"]
        assert len(started) == 1
        assert started[0].actor_id == "actor_test_123"


# ── B. task.step.started payload ──────────────────────────────────────────


class TestStepStartedPayload:
    def test_step_started_has_task_id(self):
        _reset()
        task = Task(steps=[TaskStep(operation="classify_intent", execution_class="llm_call")])
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        step_started = [e for e in events if e.type == "task.step.started"]
        assert len(step_started) >= 1
        assert step_started[0].payload["task_id"] == task.id

    def test_step_started_has_step_id(self):
        _reset()
        task = Task(steps=[TaskStep(operation="classify_intent", execution_class="llm_call")])
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        step_started = [e for e in events if e.type == "task.step.started"]
        assert len(step_started) >= 1
        # step_id must match the actual step
        assert step_started[0].payload["step_id"] == task.steps[0].id

    def test_step_started_has_step_index(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(operation="classify_intent", execution_class="llm_call"),
                TaskStep(operation="summarize", execution_class="llm_call"),
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        step_started = [e for e in events if e.type == "task.step.started"]
        assert len(step_started) == 2
        indices = [e.payload["step_index"] for e in step_started]
        assert indices == [0, 1]

    def test_step_started_has_operation(self):
        _reset()
        task = Task(steps=[TaskStep(operation="classify_intent", execution_class="llm_call")])
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        step_started = [e for e in events if e.type == "task.step.started"]
        assert step_started[0].payload["operation"] == "classify_intent"

    def test_step_started_actor_id_propagated(self):
        _reset()
        task = Task(
            steps=[TaskStep(operation="classify_intent", execution_class="llm_call")],
            issued_by="actor_xyz",
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        step_started = [e for e in events if e.type == "task.step.started"]
        assert len(step_started) == 1
        assert step_started[0].actor_id == "actor_xyz"

    def test_step_started_execution_id_set(self):
        _reset()
        task = Task(steps=[TaskStep(operation="classify_intent", execution_class="llm_call")])
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        step_started = [e for e in events if e.type == "task.step.started"]
        assert len(step_started) == 1
        # execution_id must be a non-empty string set by execute_task
        assert step_started[0].execution_id != ""
        assert step_started[0].execution_id.startswith("exec_")

    def test_step_started_execution_id_matches_completed(self):
        """The execution_id on step.started and step.completed must be the same."""
        _reset()
        task = Task(steps=[TaskStep(operation="classify_intent", execution_class="llm_call")])
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        step_started = [e for e in events if e.type == "task.step.started"]
        step_completed = [e for e in events if e.type == "task.step.completed"]
        assert len(step_started) == 1
        assert len(step_completed) == 1
        assert step_started[0].execution_id == step_completed[0].execution_id


# ── C. task.step.completed payload ────────────────────────────────────────


class TestStepCompletedPayload:
    def test_step_completed_has_task_id(self):
        _reset()
        task = Task(steps=[TaskStep(operation="classify_intent", execution_class="llm_call")])
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        step_completed = [e for e in events if e.type == "task.step.completed"]
        assert len(step_completed) >= 1
        assert step_completed[0].payload["task_id"] == task.id

    def test_step_completed_has_step_id(self):
        _reset()
        task = Task(steps=[TaskStep(operation="classify_intent", execution_class="llm_call")])
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        step_completed = [e for e in events if e.type == "task.step.completed"]
        assert step_completed[0].payload["step_id"] == task.steps[0].id

    def test_step_completed_has_step_index(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(operation="classify_intent", execution_class="llm_call"),
                TaskStep(operation="summarize", execution_class="llm_call"),
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        step_completed = [e for e in events if e.type == "task.step.completed"]
        assert len(step_completed) == 2
        indices = [e.payload["step_index"] for e in step_completed]
        assert indices == [0, 1]

    def test_step_completed_status_completed_on_success(self):
        _reset()
        task = Task(steps=[TaskStep(operation="classify_intent", execution_class="llm_call")])
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        step_completed = [e for e in events if e.type == "task.step.completed"]
        assert step_completed[0].payload["status"] == "completed"

    def test_step_completed_actor_id_propagated(self):
        _reset()
        task = Task(
            steps=[TaskStep(operation="classify_intent", execution_class="llm_call")],
            issued_by="actor_abc",
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        step_completed = [e for e in events if e.type == "task.step.completed"]
        assert step_completed[0].actor_id == "actor_abc"

    def test_step_completed_execution_id_set_on_success(self):
        _reset()
        task = Task(steps=[TaskStep(operation="classify_intent", execution_class="llm_call")])
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        step_completed = [e for e in events if e.type == "task.step.completed"]
        assert step_completed[0].execution_id != ""
        assert step_completed[0].execution_id.startswith("exec_")


# ── D. task.completed payload ──────────────────────────────────────────────


class TestTaskCompletedPayload:
    def test_task_completed_has_task_id(self):
        _reset()
        task = Task(steps=[TaskStep(operation="classify_intent", execution_class="llm_call")])
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        completed = [e for e in events if e.type == "task.completed"]
        assert len(completed) == 1
        assert completed[0].payload["task_id"] == task.id

    def test_task_completed_status_completed_on_success(self):
        _reset()
        task = Task(steps=[TaskStep(operation="classify_intent", execution_class="llm_call")])
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        completed = [e for e in events if e.type == "task.completed"]
        assert completed[0].payload["status"] == "completed"

    def test_task_completed_has_steps_completed_on_success(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(operation="classify_intent", execution_class="llm_call"),
                TaskStep(operation="summarize", execution_class="llm_call"),
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        completed = [e for e in events if e.type == "task.completed"]
        assert completed[0].payload["steps_completed"] == 2

    def test_task_completed_actor_id_propagated(self):
        _reset()
        task = Task(
            steps=[TaskStep(operation="classify_intent", execution_class="llm_call")],
            issued_by="actor_done",
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        completed = [e for e in events if e.type == "task.completed"]
        assert completed[0].actor_id == "actor_done"


# ── E. Failure — step.completed with status=failed ────────────────────────


class TestFailedStepEvents:
    def test_failed_step_emits_step_completed_status_failed(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="unknown_op_that_will_fail",
                    inputs_template={},
                    execution_class="side_effect",
                ),
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        step_completed = [e for e in events if e.type == "task.step.completed"]
        assert len(step_completed) == 1
        assert step_completed[0].payload["status"] == "failed"

    def test_failed_step_event_has_correct_step_id(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="unknown_op_that_will_fail",
                    inputs_template={},
                    execution_class="side_effect",
                ),
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        step_completed = [e for e in events if e.type == "task.step.completed"]
        assert step_completed[0].payload["step_id"] == task.steps[0].id

    def test_failed_step_task_completed_has_failed_step_field(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="unknown_op_that_will_fail",
                    inputs_template={},
                    execution_class="side_effect",
                ),
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        task_completed = [e for e in events if e.type == "task.completed"]
        assert len(task_completed) == 1
        assert task_completed[0].payload["status"] == "failed"
        assert "failed_step" in task_completed[0].payload
        assert task_completed[0].payload["failed_step"] == 0

    def test_failed_step_in_middle_has_correct_index(self):
        """Step at index 1 fails — task.completed.failed_step == 1."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="classify_intent",
                    inputs_template={"prompt": "hi", "system_prompt": "", "max_tokens": 100},
                    execution_class="llm_call",
                ),
                TaskStep(
                    operation="unknown_op_that_will_fail",
                    inputs_template={},
                    execution_class="side_effect",
                ),
                TaskStep(
                    operation="summarize",
                    inputs_template={
                        "prompt": "should not run",
                        "system_prompt": "",
                        "max_tokens": 100,
                    },
                    execution_class="llm_call",
                ),
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        task_completed = [e for e in events if e.type == "task.completed"]
        assert task_completed[0].payload["failed_step"] == 1

    def test_failed_step_actor_id_propagated(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="unknown_op_that_will_fail",
                    inputs_template={},
                    execution_class="side_effect",
                ),
            ],
            issued_by="actor_fail",
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        step_completed = [e for e in events if e.type == "task.step.completed"]
        task_completed = [e for e in events if e.type == "task.completed"]
        assert step_completed[0].actor_id == "actor_fail"
        assert task_completed[0].actor_id == "actor_fail"

    def test_failed_step_execution_id_set(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="unknown_op_that_will_fail",
                    inputs_template={},
                    execution_class="side_effect",
                ),
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        step_completed = [e for e in events if e.type == "task.step.completed"]
        assert step_completed[0].execution_id != ""
        assert step_completed[0].execution_id.startswith("exec_")


# ── F. Skipped steps — visible in task state ──────────────────────────────


class TestSkippedSteps:
    def test_skipped_steps_have_skipped_status_in_task(self):
        """Steps after a failure are marked SKIPPED in the task, not emitted as events."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="unknown_op_that_will_fail",
                    inputs_template={},
                    execution_class="side_effect",
                ),
                TaskStep(
                    operation="summarize",
                    inputs_template={
                        "prompt": "should not run",
                        "system_prompt": "",
                        "max_tokens": 100,
                    },
                    execution_class="llm_call",
                ),
                TaskStep(
                    operation="short_response",
                    inputs_template={
                        "prompt": "should not run either",
                        "system_prompt": "",
                        "max_tokens": 100,
                    },
                    execution_class="llm_call",
                ),
            ]
        )
        execute_task(task)
        assert task.steps[1].status == StepStatus.SKIPPED
        assert task.steps[2].status == StepStatus.SKIPPED

    def test_skipped_steps_emit_no_events(self):
        """No task.step.started or task.step.completed for skipped steps."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="unknown_op_that_will_fail",
                    inputs_template={},
                    execution_class="side_effect",
                ),
                TaskStep(
                    operation="summarize",
                    inputs_template={
                        "prompt": "should not run",
                        "system_prompt": "",
                        "max_tokens": 100,
                    },
                    execution_class="llm_call",
                ),
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        # Only 1 step.started and 1 step.completed — from the failed step
        step_started = [e for e in events if e.type == "task.step.started"]
        step_completed = [e for e in events if e.type == "task.step.completed"]
        assert len(step_started) == 1
        assert len(step_completed) == 1

    def test_skipped_step_ids_not_in_step_events(self):
        """Skipped step IDs should not appear in any step event."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="unknown_op_that_will_fail",
                    inputs_template={},
                    execution_class="side_effect",
                ),
                TaskStep(
                    operation="summarize",
                    inputs_template={
                        "prompt": "should not run",
                        "system_prompt": "",
                        "max_tokens": 100,
                    },
                    execution_class="llm_call",
                ),
            ]
        )
        skipped_step_id = task.steps[1].id
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        step_events = [e for e in events if e.type.startswith("task.step.")]
        emitted_step_ids = {e.payload.get("step_id") for e in step_events}
        assert skipped_step_id not in emitted_step_ids


# ── G. Event ordering ─────────────────────────────────────────────────────


class TestEventOrdering:
    def test_task_started_is_first_task_event(self):
        _reset()
        task = Task(steps=[TaskStep(operation="classify_intent", execution_class="llm_call")])
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        task_events = [e for e in events if e.type.startswith("task.")]
        assert task_events[0].type == "task.started"

    def test_task_completed_is_last_task_event(self):
        _reset()
        task = Task(steps=[TaskStep(operation="classify_intent", execution_class="llm_call")])
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        task_events = [e for e in events if e.type.startswith("task.")]
        assert task_events[-1].type == "task.completed"

    def test_step_started_before_step_completed(self):
        _reset()
        task = Task(steps=[TaskStep(operation="classify_intent", execution_class="llm_call")])
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        task_events = [e for e in events if e.type.startswith("task.")]
        types = [e.type for e in task_events]
        started_idx = types.index("task.step.started")
        completed_idx = types.index("task.step.completed")
        assert started_idx < completed_idx

    def test_step_events_between_task_events(self):
        _reset()
        task = Task(steps=[TaskStep(operation="classify_intent", execution_class="llm_call")])
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        task_events = [e for e in events if e.type.startswith("task.")]
        types = [e.type for e in task_events]
        # task.started → task.step.started → task.step.completed → task.completed
        assert types.index("task.started") < types.index("task.step.started")
        assert types.index("task.step.completed") < types.index("task.completed")

    def test_two_step_ordering(self):
        """For two steps: started, s0.start, s0.done, s1.start, s1.done, completed."""
        _reset()
        task = Task(
            steps=[
                TaskStep(operation="classify_intent", execution_class="llm_call"),
                TaskStep(operation="summarize", execution_class="llm_call"),
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        task_events = [e for e in events if e.type.startswith("task.")]
        types = [e.type for e in task_events]
        assert types == [
            "task.started",
            "task.step.started",
            "task.step.completed",
            "task.step.started",
            "task.step.completed",
            "task.completed",
        ]

    def test_failure_ordering(self):
        """Failure path: started, step.started, step.completed(failed), task.completed(failed)."""
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="unknown_op_that_will_fail",
                    inputs_template={},
                    execution_class="side_effect",
                ),
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        task_events = [e for e in events if e.type.startswith("task.")]
        types = [e.type for e in task_events]
        assert types == [
            "task.started",
            "task.step.started",
            "task.step.completed",
            "task.completed",
        ]


# ── H. GET /events API visibility ─────────────────────────────────────────


class TestEventsAPIVisibility:
    def test_task_events_visible_via_api(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        resp = client.post(
            "/tasks",
            json={"steps": [_llm_step("classify_intent", "s1")]},
            headers=headers,
        )
        assert resp.status_code == 200
        task_id = resp.json()["id"]

        events_resp = client.get("/events?limit=200", headers=headers)
        assert events_resp.status_code == 200
        events = events_resp.json()

        task_events = [e for e in events if e["payload"].get("task_id") == task_id]
        types = [e["type"] for e in task_events]
        assert "task.started" in types
        assert "task.step.started" in types
        assert "task.step.completed" in types
        assert "task.completed" in types

    def test_events_api_requires_metrics_read_scope(self):
        _reset()
        _, _, exec_headers = _create_identity("executor", ["execute"])
        resp = client.get("/events", headers=exec_headers)
        assert resp.status_code == 403

    def test_events_api_event_has_all_fields(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        client.post(
            "/tasks",
            json={"steps": [_llm_step("classify_intent")]},
            headers=headers,
        )
        events_resp = client.get("/events?limit=200", headers=headers)
        assert events_resp.status_code == 200
        events = events_resp.json()
        assert len(events) > 0
        for event in events:
            assert "id" in event
            assert "type" in event
            assert "timestamp" in event
            assert "payload" in event
            assert "actor_id" in event
            assert "execution_id" in event

    def test_step_events_have_execution_id_set_in_api(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        resp = client.post(
            "/tasks",
            json={"steps": [_llm_step("classify_intent")]},
            headers=headers,
        )
        task_id = resp.json()["id"]
        events_resp = client.get("/events?limit=200", headers=headers)
        events = events_resp.json()
        step_events = [
            e
            for e in events
            if e["type"].startswith("task.step.") and e["payload"].get("task_id") == task_id
        ]
        for ev in step_events:
            assert ev["execution_id"] != "", f"execution_id empty on {ev['type']}"
            assert ev["execution_id"].startswith("exec_")

    def test_step_events_have_actor_id_set_in_api(self):
        _reset()
        identity, _, headers = _create_identity("actor_user", ["admin"])
        resp = client.post(
            "/tasks",
            json={"steps": [_llm_step("classify_intent")]},
            headers=headers,
        )
        task_id = resp.json()["id"]
        events_resp = client.get("/events?limit=200", headers=headers)
        events = events_resp.json()
        step_events = [
            e
            for e in events
            if e["type"].startswith("task.step.") and e["payload"].get("task_id") == task_id
        ]
        for ev in step_events:
            assert ev["actor_id"] == identity.id, (
                f"actor_id mismatch on {ev['type']}: got {ev['actor_id']!r}"
            )

    def test_failed_task_events_visible_via_api(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        resp = client.post(
            "/tasks",
            json={"steps": [{"operation": "bad_op", "execution_class": "side_effect"}]},
            headers=headers,
        )
        task_id = resp.json()["id"]
        events_resp = client.get("/events?limit=200", headers=headers)
        events = events_resp.json()
        task_events = [e for e in events if e["payload"].get("task_id") == task_id]
        types = [e["type"] for e in task_events]
        assert "task.started" in types
        assert "task.step.started" in types
        assert "task.step.completed" in types
        assert "task.completed" in types
        # verify the failure statuses
        step_completed = [e for e in task_events if e["type"] == "task.step.completed"]
        assert step_completed[0]["payload"]["status"] == "failed"
        task_completed = [e for e in task_events if e["type"] == "task.completed"]
        assert task_completed[0]["payload"]["status"] == "failed"
