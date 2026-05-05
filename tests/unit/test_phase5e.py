"""Tests for Phase 5E: Multi-Step Execution Graph.

Verifies:
- Task and TaskStep model
- Template resolution (context, prev_output)
- Sequential step execution
- Context passing between steps
- Failure stops execution and skips remaining
- Events emitted for task lifecycle
- Max steps enforced
- API endpoints (POST /tasks, GET /tasks/{id})
- Task persistence in memory store
"""

import sys
import os

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase5a")

from fastapi.testclient import TestClient

from umh.control.api import app
from umh.control.identity import get_identity_store
from umh.events.stream import get_event_stream, reset_event_stream
from umh.execution.approval import get_approval_store
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

client = TestClient(app)


def _reset():
    get_approval_store().reset()
    get_identity_store().reset()
    reset_event_stream()
    reset_orchestrator()
    reset_tasks()


def _create_identity(name="admin", scopes=None):
    store = get_identity_store()
    identity, raw_key = store.create_identity(name, scopes or ["admin"])
    return identity, raw_key, {"X-API-Key": raw_key}


# ── A. Task Model ─────────────────────────────────────────────────


class TestTaskModel:
    def test_task_creation(self):
        task = Task(steps=[TaskStep(operation="test_op")])
        assert task.id.startswith("task_")
        assert task.status == TaskStatus.PENDING
        assert task.current_step_index == 0
        assert len(task.steps) == 1

    def test_step_creation(self):
        step = TaskStep(operation="classify", inputs_template={"prompt": "hi"}, output_key="cls")
        assert step.id.startswith("step_")
        assert step.operation == "classify"
        assert step.output_key == "cls"
        assert step.status == StepStatus.PENDING

    def test_task_to_dict(self):
        task = Task(steps=[TaskStep(operation="op1"), TaskStep(operation="op2")])
        d = task.to_dict()
        assert d["id"] == task.id
        assert d["status"] == "pending"
        assert len(d["steps"]) == 2
        assert d["steps"][0]["operation"] == "op1"

    def test_step_to_dict(self):
        step = TaskStep(operation="test", output_key="out")
        d = step.to_dict()
        assert d["operation"] == "test"
        assert d["output_key"] == "out"
        assert d["status"] == "pending"

    def test_max_steps_enforced(self):
        try:
            Task(steps=[TaskStep(operation=f"op_{i}") for i in range(11)])
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "max steps" in str(e).lower()

    def test_task_timestamps(self):
        task = Task(steps=[TaskStep(operation="op")])
        assert task.created_at != ""
        assert task.updated_at != ""

    def test_task_context_default_empty(self):
        task = Task(steps=[TaskStep(operation="op")])
        assert task.context == {}


# ── B. Template Resolution ────────────────────────────────────────


class TestTemplateResolution:
    def test_context_reference(self):
        result = resolve_inputs({"key": "{{context.name}}"}, {"name": "Alice"}, None)
        assert result["key"] == "Alice"

    def test_prev_output_reference(self):
        result = resolve_inputs({"key": "{{prev_output.value}}"}, {}, {"value": "42"})
        assert result["key"] == "42"

    def test_nested_context_reference(self):
        result = resolve_inputs(
            {"key": "{{context.step1.result}}"}, {"step1": {"result": "ok"}}, None
        )
        assert result["key"] == "ok"

    def test_no_template_passthrough(self):
        result = resolve_inputs({"key": "plain text"}, {}, None)
        assert result["key"] == "plain text"

    def test_non_string_passthrough(self):
        result = resolve_inputs({"x": 42, "y": True}, {}, None)
        assert result["x"] == 42
        assert result["y"] is True

    def test_missing_context_key_unchanged(self):
        result = resolve_inputs({"key": "{{context.missing}}"}, {}, None)
        assert result["key"] == ""

    def test_missing_prev_output_unchanged(self):
        result = resolve_inputs({"key": "{{prev_output.missing}}"}, {}, None)
        assert result["key"] == "{{prev_output.missing}}"

    def test_nested_dict_resolution(self):
        result = resolve_inputs({"outer": {"inner": "{{context.val}}"}}, {"val": "resolved"}, None)
        assert result["outer"]["inner"] == "resolved"

    def test_multiple_templates_in_string(self):
        result = resolve_inputs(
            {"msg": "Hello {{context.name}}, you are {{context.age}}"},
            {"name": "Bob", "age": "25"},
            None,
        )
        assert result["msg"] == "Hello Bob, you are 25"


# ── C. Single Step Execution ──────────────────────────────────────


class TestSingleStepExecution:
    def test_single_llm_step(self):
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

    def test_single_step_result_stored(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="classify_intent",
                    inputs_template={"prompt": "hello", "system_prompt": "", "max_tokens": 100},
                    output_key="step1",
                )
            ]
        )
        result = execute_task(task)
        assert "step1" in result.context
        assert result.context["step1"]["status"] == "succeeded"


# ── D. Multi-Step Execution ───────────────────────────────────────


class TestMultiStepExecution:
    def test_two_step_task(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="classify_intent",
                    inputs_template={"prompt": "hello", "system_prompt": "", "max_tokens": 100},
                    output_key="step1",
                ),
                TaskStep(
                    operation="summarize",
                    inputs_template={
                        "prompt": "summarize this",
                        "system_prompt": "",
                        "max_tokens": 100,
                    },
                    output_key="step2",
                ),
            ]
        )
        result = execute_task(task)
        assert result.status == TaskStatus.COMPLETED
        assert result.steps[0].status == StepStatus.COMPLETED
        assert result.steps[1].status == StepStatus.COMPLETED
        assert "step1" in result.context
        assert "step2" in result.context

    def test_context_passing_between_steps(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="classify_intent",
                    inputs_template={"prompt": "hello", "system_prompt": "", "max_tokens": 100},
                    output_key="classification",
                ),
                TaskStep(
                    operation="summarize",
                    inputs_template={
                        "prompt": "based on {{context.classification.operation}}: summarize",
                        "system_prompt": "",
                        "max_tokens": 100,
                    },
                ),
            ]
        )
        result = execute_task(task)
        assert result.status == TaskStatus.COMPLETED

    def test_prev_output_passing(self):
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
                    inputs_template={
                        "prompt": "{{prev_output.response}}",
                        "system_prompt": "",
                        "max_tokens": 100,
                    },
                ),
            ]
        )
        result = execute_task(task)
        assert result.status == TaskStatus.COMPLETED

    def test_three_step_task(self):
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
                    inputs_template={"prompt": "step 2", "system_prompt": "", "max_tokens": 100},
                    output_key="s2",
                ),
                TaskStep(
                    operation="short_response",
                    inputs_template={"prompt": "step 3", "system_prompt": "", "max_tokens": 100},
                    output_key="s3",
                ),
            ]
        )
        result = execute_task(task)
        assert result.status == TaskStatus.COMPLETED
        assert len([s for s in result.steps if s.status == StepStatus.COMPLETED]) == 3

    def test_initial_context_available(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="classify_intent",
                    inputs_template={
                        "prompt": "{{context.user_input}}",
                        "system_prompt": "",
                        "max_tokens": 100,
                    },
                )
            ],
            context={"user_input": "hello world"},
        )
        result = execute_task(task)
        assert result.status == TaskStatus.COMPLETED


# ── E. Failure Handling ───────────────────────────────────────────


class TestFailureHandling:
    def test_failure_stops_execution(self):
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
                ),
            ]
        )
        result = execute_task(task)
        assert result.status == TaskStatus.FAILED
        assert result.steps[0].status == StepStatus.FAILED
        assert result.steps[1].status == StepStatus.SKIPPED

    def test_error_message_set(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="bad_op",
                    inputs_template={},
                    execution_class="side_effect",
                ),
            ]
        )
        result = execute_task(task)
        assert result.error != ""
        assert "bad_op" in result.error


# ── F. Events ────────────────────────────────────────────────────


class TestTaskEvents:
    def test_task_started_event(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="classify_intent",
                    inputs_template={"prompt": "hi", "system_prompt": "", "max_tokens": 100},
                )
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        started = [e for e in events if e.type == "task.started"]
        assert len(started) == 1
        assert started[0].payload["task_id"] == task.id

    def test_task_completed_event(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="classify_intent",
                    inputs_template={"prompt": "hi", "system_prompt": "", "max_tokens": 100},
                )
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        completed = [e for e in events if e.type == "task.completed"]
        assert len(completed) == 1
        assert completed[0].payload["status"] == "completed"

    def test_step_events_emitted(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="classify_intent",
                    inputs_template={"prompt": "hi", "system_prompt": "", "max_tokens": 100},
                ),
                TaskStep(
                    operation="summarize",
                    inputs_template={"prompt": "hi", "system_prompt": "", "max_tokens": 100},
                ),
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        step_started = [e for e in events if e.type == "task.step.started"]
        step_completed = [e for e in events if e.type == "task.step.completed"]
        assert len(step_started) == 2
        assert len(step_completed) == 2

    def test_failed_task_emits_completed_event(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(operation="bad_op", inputs_template={}, execution_class="side_effect"),
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        completed = [e for e in events if e.type == "task.completed"]
        assert len(completed) == 1
        assert completed[0].payload["status"] == "failed"

    def test_event_ordering(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="classify_intent",
                    inputs_template={"prompt": "hi", "system_prompt": "", "max_tokens": 100},
                )
            ]
        )
        execute_task(task)
        events = get_event_stream().list_events(limit=200)
        task_events = [e for e in events if e.type.startswith("task.")]
        types = [e.type for e in task_events]
        assert types[0] == "task.started"
        assert "task.step.started" in types
        assert "task.step.completed" in types
        assert types[-1] == "task.completed"


# ── G. Memory Store ──────────────────────────────────────────────


class TestTaskStore:
    def test_task_saved_after_execution(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="classify_intent",
                    inputs_template={"prompt": "hi", "system_prompt": "", "max_tokens": 100},
                )
            ]
        )
        execute_task(task)
        retrieved = get_task(task.id)
        assert retrieved is not None
        assert retrieved.status == TaskStatus.COMPLETED

    def test_failed_task_saved(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(operation="bad_op", inputs_template={}, execution_class="side_effect"),
            ]
        )
        execute_task(task)
        retrieved = get_task(task.id)
        assert retrieved is not None
        assert retrieved.status == TaskStatus.FAILED

    def test_missing_task_returns_none(self):
        _reset()
        assert get_task("nonexistent") is None

    def test_reset_clears_store(self):
        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="classify_intent",
                    inputs_template={"prompt": "hi", "system_prompt": "", "max_tokens": 100},
                )
            ]
        )
        execute_task(task)
        reset_tasks()
        assert get_task(task.id) is None


# ── H. API Endpoints ─────────────────────────────────────────────


class TestTaskAPI:
    def test_create_task_requires_auth(self):
        _reset()
        resp = client.post("/tasks", json={"steps": [{"operation": "test"}]})
        assert resp.status_code == 401

    def test_create_task_requires_execute_scope(self):
        _reset()
        _, _, headers = _create_identity("viewer", ["metrics:read"])
        resp = client.post("/tasks", json={"steps": [{"operation": "test"}]}, headers=headers)
        assert resp.status_code == 403

    def test_create_and_execute_task(self):
        _reset()
        _, _, headers = _create_identity("executor", ["admin"])
        resp = client.post(
            "/tasks",
            json={
                "steps": [
                    {
                        "operation": "classify_intent",
                        "inputs_template": {"prompt": "hi", "system_prompt": "", "max_tokens": 100},
                        "output_key": "s1",
                    }
                ]
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert len(data["steps"]) == 1

    def test_get_task_endpoint(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        resp = client.post(
            "/tasks",
            json={
                "steps": [
                    {
                        "operation": "classify_intent",
                        "inputs_template": {"prompt": "hi", "system_prompt": "", "max_tokens": 100},
                    }
                ]
            },
            headers=headers,
        )
        task_id = resp.json()["id"]
        get_resp = client.get(f"/tasks/{task_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == task_id

    def test_get_task_not_found(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        resp = client.get("/tasks/nonexistent", headers=headers)
        assert resp.status_code == 404

    def test_create_task_max_steps(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        resp = client.post(
            "/tasks",
            json={"steps": [{"operation": f"op_{i}"} for i in range(11)]},
            headers=headers,
        )
        assert resp.status_code == 400

    def test_multi_step_via_api(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        resp = client.post(
            "/tasks",
            json={
                "steps": [
                    {
                        "operation": "classify_intent",
                        "inputs_template": {"prompt": "hi", "system_prompt": "", "max_tokens": 100},
                        "output_key": "s1",
                    },
                    {
                        "operation": "summarize",
                        "inputs_template": {
                            "prompt": "sum",
                            "system_prompt": "",
                            "max_tokens": 100,
                        },
                        "output_key": "s2",
                    },
                ]
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert "s1" in data["context"]
        assert "s2" in data["context"]

    def test_task_with_initial_context(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        resp = client.post(
            "/tasks",
            json={
                "steps": [
                    {
                        "operation": "classify_intent",
                        "inputs_template": {
                            "prompt": "{{context.user_msg}}",
                            "system_prompt": "",
                            "max_tokens": 100,
                        },
                    }
                ],
                "context": {"user_msg": "hello"},
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"


# ── I. Issued By Tracking ────────────────────────────────────────


class TestIssuedBy:
    def test_task_carries_issued_by(self):
        _reset()
        identity, _, headers = _create_identity("actor", ["admin"])
        resp = client.post(
            "/tasks",
            json={
                "steps": [
                    {
                        "operation": "classify_intent",
                        "inputs_template": {"prompt": "hi", "system_prompt": "", "max_tokens": 100},
                    }
                ]
            },
            headers=headers,
        )
        data = resp.json()
        assert data["issued_by"] == identity.id
