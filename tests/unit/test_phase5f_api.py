"""Tests for Phase 5F: /tasks API hardening edge cases.

Covers:
- Empty steps list → 400
- Empty operation in any step → 400
- Invalid execution_class → 400
- GET /tasks list endpoint
- Response includes full step results and context
"""

import sys
import os

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase5f")

from fastapi.testclient import TestClient

from umh.control.api import app
from umh.control.identity import get_identity_store
from umh.events.stream import reset_event_stream
from umh.execution.approval import get_approval_store
from umh.orchestrator.engine import reset_orchestrator
from umh.orchestrator.task import reset_tasks

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


# ── A. Empty Steps ────────────────────────────────────────────────


class TestEmptySteps:
    def test_empty_steps_returns_400(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        resp = client.post("/tasks", json={"steps": []}, headers=headers)
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_empty_steps_unauthenticated_still_401(self):
        """Auth check fires before body validation."""
        _reset()
        resp = client.post("/tasks", json={"steps": []})
        assert resp.status_code == 401


# ── B. Empty Operation ────────────────────────────────────────────


class TestEmptyOperation:
    def test_empty_operation_returns_400(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        resp = client.post(
            "/tasks",
            json={"steps": [{"operation": ""}]},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "operation" in resp.json()["detail"].lower()

    def test_whitespace_operation_returns_400(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        resp = client.post(
            "/tasks",
            json={"steps": [{"operation": "   "}]},
            headers=headers,
        )
        assert resp.status_code == 400

    def test_empty_operation_in_second_step_returns_400(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        resp = client.post(
            "/tasks",
            json={
                "steps": [
                    {"operation": "classify_intent"},
                    {"operation": ""},
                ]
            },
            headers=headers,
        )
        assert resp.status_code == 400

    def test_valid_operation_passes(self):
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
        assert resp.status_code == 200


# ── C. Invalid execution_class ────────────────────────────────────


class TestInvalidExecutionClass:
    def test_invalid_execution_class_returns_400(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        resp = client.post(
            "/tasks",
            json={
                "steps": [
                    {
                        "operation": "classify_intent",
                        "execution_class": "not_a_real_class",
                    }
                ]
            },
            headers=headers,
        )
        assert resp.status_code == 400
        assert "execution_class" in resp.json()["detail"].lower()

    def test_valid_execution_classes_accepted(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        for ec in ("llm_call", "pure", "side_effect", "transport"):
            resp = client.post(
                "/tasks",
                json={
                    "steps": [
                        {
                            "operation": "classify_intent",
                            "inputs_template": {
                                "prompt": "hi",
                                "system_prompt": "",
                                "max_tokens": 100,
                            },
                            "execution_class": ec,
                        }
                    ]
                },
                headers=headers,
            )
            # pure / llm_call succeed, side_effect / transport may fail at execution
            # but must not return 400 for class validation
            assert resp.status_code != 400, f"execution_class={ec!r} wrongly rejected"

    def test_invalid_class_in_second_step_returns_400(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        resp = client.post(
            "/tasks",
            json={
                "steps": [
                    {"operation": "classify_intent", "execution_class": "llm_call"},
                    {"operation": "summarize", "execution_class": "garbage"},
                ]
            },
            headers=headers,
        )
        assert resp.status_code == 400


# ── D. GET /tasks list endpoint ───────────────────────────────────


class TestListTasksEndpoint:
    def test_list_tasks_requires_auth(self):
        _reset()
        resp = client.get("/tasks")
        assert resp.status_code == 401

    def test_list_tasks_requires_execute_scope(self):
        _reset()
        _, _, headers = _create_identity("viewer", ["metrics:read"])
        resp = client.get("/tasks", headers=headers)
        assert resp.status_code == 403

    def test_list_tasks_empty_initially(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        resp = client.get("/tasks", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_tasks_returns_completed_task(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        client.post(
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
        resp = client.get("/tasks", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "completed"

    def test_list_tasks_accumulates_multiple(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        for _ in range(3):
            client.post(
                "/tasks",
                json={
                    "steps": [
                        {
                            "operation": "classify_intent",
                            "inputs_template": {
                                "prompt": "hi",
                                "system_prompt": "",
                                "max_tokens": 100,
                            },
                        }
                    ]
                },
                headers=headers,
            )
        resp = client.get("/tasks", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_list_tasks_includes_failed_tasks(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        client.post(
            "/tasks",
            json={
                "steps": [
                    {
                        "operation": "bad_op",
                        "execution_class": "side_effect",
                    }
                ]
            },
            headers=headers,
        )
        resp = client.get("/tasks", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "failed"


# ── E. Response completeness ──────────────────────────────────────


class TestResponseCompleteness:
    def test_response_includes_step_results(self):
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
                    }
                ]
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # step result dict is populated after execution
        step = data["steps"][0]
        assert step["result"] is not None
        assert "status" in step["result"]

    def test_response_includes_context_after_output_key(self):
        _reset()
        _, _, headers = _create_identity("admin", ["admin"])
        resp = client.post(
            "/tasks",
            json={
                "steps": [
                    {
                        "operation": "classify_intent",
                        "inputs_template": {"prompt": "hi", "system_prompt": "", "max_tokens": 100},
                        "output_key": "my_output",
                    }
                ]
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "my_output" in data["context"]

    def test_response_includes_issued_by(self):
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
        assert resp.status_code == 200
        assert resp.json()["issued_by"] == identity.id

    def test_response_includes_timestamps(self):
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
        assert resp.status_code == 200
        data = resp.json()
        assert data["created_at"] != ""
        assert data["updated_at"] != ""

    def test_multi_step_response_all_steps_present(self):
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
        assert len(data["steps"]) == 2
        for step in data["steps"]:
            assert step["status"] == "completed"
            assert step["result"] is not None
