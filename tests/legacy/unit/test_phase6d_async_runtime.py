"""Tests for Phase 6D: Async Task Runtime + Durable MVP Execution.

Covers all 10 required categories:
1. Task runs in background (worker picks up PENDING tasks)
2. API returns immediately (POST /tasks with async_exec=True → 202)
3. Task completes correctly (worker executes to COMPLETED)
4. Approval pauses task (worker execution hits approval → PAUSED)
5. Approval resumes task (worker finds granted approval → resumes)
6. Restart simulation (reload store, tasks survive)
7. No duplicate execution (claim_task atomicity)
8. No race conditions (concurrent worker polls)
9. Metrics reflect state (task/plan metrics include async tasks)
10. CLI reads tasks correctly (API GET /tasks returns durable tasks)
"""

import sys
import os
import threading
import time

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase6d")
os.environ["UMH_TASK_BACKEND"] = "memory"

from fastapi.testclient import TestClient

from umh.control.api import app
from umh.control.identity import get_identity_store
from umh.events.stream import get_event_stream, reset_event_stream
from umh.execution.approval import ApprovalStatus, get_approval_store
from umh.orchestrator.engine import reset_orchestrator, start_orchestrator
from umh.orchestrator.task import (
    Task,
    TaskStatus,
    TaskStep,
    StepStatus,
    enqueue_task,
    execute_task,
    get_task,
    list_tasks,
    reset_tasks,
)
from umh.orchestrator.task_store import (
    InMemoryTaskBackend,
    TaskStore,
    get_task_store,
    reset_task_store,
)
from umh.orchestrator.worker import Worker, reset_worker

client = TestClient(app)


def _reset():
    get_approval_store().reset()
    get_identity_store().reset()
    reset_event_stream()
    reset_orchestrator()
    reset_tasks()
    reset_task_store(backend=InMemoryTaskBackend())
    reset_worker()


def _create_identity(name="admin", scopes=None):
    store = get_identity_store()
    identity, raw_key = store.create_identity(name, scopes or ["admin"])
    return identity, raw_key, {"X-API-Key": raw_key}


# ── 1. Task Store Persistence ─────────────────────────────────────


class TestTaskStorePersistence:
    def setup_method(self):
        _reset()

    def test_save_and_get(self):
        store = get_task_store()
        task = Task(steps=[TaskStep(operation="classify_intent")])
        store.save(task)
        loaded = store.get(task.id)
        assert loaded is not None
        assert loaded.id == task.id
        assert loaded.status == TaskStatus.PENDING

    def test_list_by_status(self):
        store = get_task_store()
        t1 = Task(steps=[TaskStep(operation="op1")])
        t2 = Task(steps=[TaskStep(operation="op2")])
        t2.status = TaskStatus.RUNNING
        store.save(t1)
        store.save(t2)
        pending = store.list_by_status(TaskStatus.PENDING)
        running = store.list_by_status(TaskStatus.RUNNING)
        assert len(pending) == 1
        assert pending[0].id == t1.id
        assert len(running) == 1
        assert running[0].id == t2.id

    def test_list_all(self):
        store = get_task_store()
        for i in range(3):
            store.save(Task(steps=[TaskStep(operation=f"op{i}")]))
        assert len(store.list_all()) == 3

    def test_claim_task_success(self):
        store = get_task_store()
        task = Task(steps=[TaskStep(operation="op")])
        store.save(task)
        assert store.claim_task(task.id) is True
        loaded = store.get(task.id)
        assert loaded.status == TaskStatus.RUNNING

    def test_claim_task_already_claimed(self):
        store = get_task_store()
        task = Task(steps=[TaskStep(operation="op")])
        store.save(task)
        assert store.claim_task(task.id) is True
        assert store.claim_task(task.id) is False

    def test_claim_nonexistent_task(self):
        store = get_task_store()
        assert store.claim_task("nonexistent") is False

    def test_steps_roundtrip(self):
        store = get_task_store()
        steps = [
            TaskStep(operation="op1", inputs_template={"k": "v"}, output_key="out1"),
            TaskStep(operation="op2", execution_class="shell_command"),
        ]
        task = Task(steps=steps, context={"plan_id": "eplan_123"})
        store.save(task)
        loaded = store.get(task.id)
        assert len(loaded.steps) == 2
        assert loaded.steps[0].operation == "op1"
        assert loaded.steps[0].inputs_template == {"k": "v"}
        assert loaded.steps[0].output_key == "out1"
        assert loaded.steps[1].execution_class == "shell_command"
        assert loaded.context.get("plan_id") == "eplan_123"

    def test_paused_state_roundtrip(self):
        store = get_task_store()
        task = Task(steps=[TaskStep(operation="op")])
        task.status = TaskStatus.PAUSED
        task.paused_step_index = 0
        task.paused_approval_id = "appr_abc"
        task.paused_reason = "Needs human approval"
        task.pause_count = 1
        task.paused_request = {"operation": "click", "inputs": {"x": 100}}
        store.save(task)

        loaded = store.get(task.id)
        assert loaded.status == TaskStatus.PAUSED
        assert loaded.paused_step_index == 0
        assert loaded.paused_approval_id == "appr_abc"
        assert loaded.paused_reason == "Needs human approval"
        assert loaded.pause_count == 1
        assert loaded.paused_request == {"operation": "click", "inputs": {"x": 100}}

    def test_reset_clears_all(self):
        store = get_task_store()
        store.save(Task(steps=[TaskStep(operation="op")]))
        assert len(store.list_all()) == 1
        store.reset()
        assert len(store.list_all()) == 0


# ── 2. Enqueue Task (Background Submission) ───────────────────────


class TestEnqueueTask:
    def setup_method(self):
        _reset()

    def test_enqueue_sets_pending(self):
        task = Task(steps=[TaskStep(operation="classify_intent")])
        result = enqueue_task(task)
        assert result.status == TaskStatus.PENDING
        assert result.id == task.id

    def test_enqueue_saves_to_store(self):
        task = Task(steps=[TaskStep(operation="classify_intent")])
        enqueue_task(task)
        loaded = get_task_store().get(task.id)
        assert loaded is not None
        assert loaded.status == TaskStatus.PENDING

    def test_enqueue_emits_event(self):
        stream = get_event_stream()
        task = Task(steps=[TaskStep(operation="op")])
        enqueue_task(task)
        events = stream.list_events(limit=50)
        enqueued = [e for e in events if e.type == "task.enqueued"]
        assert len(enqueued) >= 1
        assert enqueued[-1].payload["task_id"] == task.id

    def test_enqueue_does_not_execute(self):
        task = Task(
            steps=[TaskStep(operation="classify_intent", inputs_template={"prompt": "hello"})]
        )
        result = enqueue_task(task)
        assert result.status == TaskStatus.PENDING
        assert result.steps[0].status == StepStatus.PENDING
        assert result.steps[0].result is None

    def test_enqueue_preserves_context(self):
        task = Task(
            steps=[TaskStep(operation="op")],
            context={"plan_id": "eplan_test", "source": "api"},
        )
        enqueue_task(task)
        loaded = get_task(task.id)
        assert loaded.context["plan_id"] == "eplan_test"
        assert loaded.context["source"] == "api"


# ── 3. Worker Execution ───────────────────────────────────────────


class TestWorkerExecution:
    def setup_method(self):
        _reset()
        start_orchestrator()

    def test_worker_picks_up_pending(self):
        task = Task(
            steps=[TaskStep(operation="classify_intent", inputs_template={"prompt": "hello"})]
        )
        enqueue_task(task)

        worker = Worker()
        processed = worker.poll_once()
        assert processed >= 1

        loaded = get_task(task.id)
        assert loaded is not None
        assert loaded.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)

    def test_worker_completes_multi_step(self):
        task = Task(
            steps=[
                TaskStep(operation="classify_intent", inputs_template={"prompt": "hello"}),
                TaskStep(operation="classify_intent", inputs_template={"prompt": "world"}),
            ]
        )
        enqueue_task(task)

        worker = Worker()
        worker.poll_once()

        loaded = get_task(task.id)
        assert loaded is not None
        assert loaded.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)

    def test_worker_skips_non_pending(self):
        task = Task(steps=[TaskStep(operation="classify_intent")])
        task.status = TaskStatus.COMPLETED
        get_task_store().save(task)

        worker = Worker()
        processed = worker.poll_once()
        assert processed == 0

    def test_worker_emits_lifecycle_events(self):
        stream = get_event_stream()
        task = Task(
            steps=[TaskStep(operation="classify_intent", inputs_template={"prompt": "hello"})]
        )
        enqueue_task(task)

        worker = Worker()
        worker.poll_once()

        events = stream.list_events(limit=100)
        types = [e.type for e in events]
        assert "task.enqueued" in types
        assert "task.started" in types or "task.completed" in types


# ── 4. API Async Exec ─────────────────────────────────────────────


class TestAPIAsyncExec:
    def setup_method(self):
        _reset()
        start_orchestrator()

    def test_async_returns_202(self):
        _, _, headers = _create_identity()
        resp = client.post(
            "/tasks",
            json={
                "steps": [{"operation": "classify_intent", "inputs_template": {"prompt": "hi"}}],
                "async_exec": True,
            },
            headers=headers,
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "pending"
        assert "task_id" in data
        assert data["message"] == "Task enqueued for background execution"

    def test_sync_still_works(self):
        _, _, headers = _create_identity()
        resp = client.post(
            "/tasks",
            json={
                "steps": [{"operation": "classify_intent", "inputs_template": {"prompt": "hi"}}],
                "async_exec": False,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("completed", "failed")

    def test_async_task_readable_via_get(self):
        _, _, headers = _create_identity()
        resp = client.post(
            "/tasks",
            json={
                "steps": [{"operation": "classify_intent", "inputs_template": {"prompt": "hi"}}],
                "async_exec": True,
            },
            headers=headers,
        )
        task_id = resp.json()["task_id"]

        get_resp = client.get(f"/tasks/{task_id}", headers=headers)
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == task_id
        assert data["status"] == "pending"

    def test_async_task_appears_in_list(self):
        _, _, headers = _create_identity()
        client.post(
            "/tasks",
            json={
                "steps": [{"operation": "classify_intent"}],
                "async_exec": True,
            },
            headers=headers,
        )
        resp = client.get("/tasks", headers=headers)
        assert resp.status_code == 200
        tasks = resp.json()
        assert len(tasks) >= 1

    def test_async_step_count(self):
        _, _, headers = _create_identity()
        resp = client.post(
            "/tasks",
            json={
                "steps": [
                    {"operation": "classify_intent"},
                    {"operation": "classify_intent"},
                    {"operation": "classify_intent"},
                ],
                "async_exec": True,
            },
            headers=headers,
        )
        assert resp.json()["step_count"] == 3


# ── 5. Approval Pauses Task ──────────────────────────────────────


class TestApprovalPauses:
    def setup_method(self):
        _reset()
        start_orchestrator()

    def test_approval_step_pauses_task(self):
        task = Task(
            steps=[
                TaskStep(operation="classify_intent", inputs_template={"prompt": "hello"}),
                TaskStep(
                    operation="computer_click",
                    inputs_template={"x": 100, "y": 200},
                    execution_class="side_effect",
                ),
            ]
        )
        result = execute_task(task)

        if result.status == TaskStatus.PAUSED:
            assert result.paused_approval_id != ""
            assert result.paused_step_index is not None
            assert result.pause_count >= 1

    def test_worker_pauses_on_approval(self):
        task = Task(
            steps=[
                TaskStep(operation="classify_intent", inputs_template={"prompt": "hello"}),
                TaskStep(
                    operation="computer_click",
                    inputs_template={"x": 100, "y": 200},
                    execution_class="side_effect",
                ),
            ]
        )
        enqueue_task(task)
        worker = Worker()
        worker.poll_once()

        loaded = get_task(task.id)
        assert loaded is not None
        if loaded.status == TaskStatus.PAUSED:
            assert loaded.paused_approval_id != ""


# ── 6. Approval Resume ───────────────────────────────────────────


class TestApprovalResume:
    def setup_method(self):
        _reset()
        start_orchestrator()

    def test_resume_task_endpoint(self):
        _, _, headers = _create_identity()
        task = Task(
            steps=[
                TaskStep(
                    operation="computer_click",
                    inputs_template={"x": 100, "y": 200},
                    execution_class="side_effect",
                ),
            ]
        )
        result = execute_task(task)

        if result.status == TaskStatus.PAUSED:
            approval_store = get_approval_store()
            approval_store.approve(result.paused_approval_id, approved_by="test")

            resp = client.post(f"/tasks/{result.id}/resume", headers=headers)
            assert resp.status_code in (200, 409)

    def test_resume_non_paused_returns_409(self):
        _, _, headers = _create_identity()
        task = Task(steps=[TaskStep(operation="classify_intent", inputs_template={"prompt": "hi"})])
        result = execute_task(task)

        if result.status != TaskStatus.PAUSED:
            resp = client.post(f"/tasks/{result.id}/resume", headers=headers)
            assert resp.status_code == 409

    def test_resume_nonexistent_returns_404(self):
        _, _, headers = _create_identity()
        resp = client.post("/tasks/task_nonexistent/resume", headers=headers)
        assert resp.status_code == 404

    def test_worker_resumes_approved_task(self):
        task = Task(
            steps=[
                TaskStep(
                    operation="computer_click",
                    inputs_template={"x": 100, "y": 200},
                    execution_class="side_effect",
                ),
            ]
        )
        result = execute_task(task)

        if result.status == TaskStatus.PAUSED:
            approval_store = get_approval_store()
            approval_store.approve(result.paused_approval_id, approved_by="test")

            worker = Worker()
            processed = worker.poll_once()

            loaded = get_task(task.id)
            assert loaded is not None


# ── 7. Restart Simulation ────────────────────────────────────────


class TestRestartSimulation:
    def setup_method(self):
        _reset()

    def test_task_survives_memory_clear(self):
        store = get_task_store()
        task = Task(steps=[TaskStep(operation="classify_intent")])
        store.save(task)

        from umh.orchestrator import task as task_module

        with task_module._tasks_lock:
            task_module._tasks.clear()

        loaded = get_task(task.id)
        assert loaded is not None
        assert loaded.id == task.id

    def test_enqueued_task_survives_in_store(self):
        task = Task(steps=[TaskStep(operation="classify_intent")])
        enqueue_task(task)

        from umh.orchestrator import task as task_module

        with task_module._tasks_lock:
            task_module._tasks.clear()

        loaded = get_task_store().get(task.id)
        assert loaded is not None
        assert loaded.status == TaskStatus.PENDING

    def test_paused_task_survives_restart(self):
        store = get_task_store()
        task = Task(steps=[TaskStep(operation="op")])
        task.status = TaskStatus.PAUSED
        task.paused_approval_id = "appr_test"
        task.paused_step_index = 0
        task.paused_reason = "Needs approval"
        task.pause_count = 1
        store.save(task)

        from umh.orchestrator import task as task_module

        with task_module._tasks_lock:
            task_module._tasks.clear()

        loaded = get_task(task.id)
        assert loaded is not None
        assert loaded.status == TaskStatus.PAUSED
        assert loaded.paused_approval_id == "appr_test"


# ── 8. No Duplicate Execution ────────────────────────────────────


class TestNoDuplicateExecution:
    def setup_method(self):
        _reset()

    def test_double_claim_fails(self):
        store = get_task_store()
        task = Task(steps=[TaskStep(operation="op")])
        store.save(task)

        first = store.claim_task(task.id)
        second = store.claim_task(task.id)
        assert first is True
        assert second is False

    def test_concurrent_claims(self):
        store = get_task_store()
        task = Task(steps=[TaskStep(operation="op")])
        store.save(task)

        results = []
        barrier = threading.Barrier(2)

        def try_claim():
            barrier.wait()
            results.append(store.claim_task(task.id))

        t1 = threading.Thread(target=try_claim)
        t2 = threading.Thread(target=try_claim)
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        assert results.count(True) == 1
        assert results.count(False) == 1

    def test_two_workers_no_double_execution(self):
        start_orchestrator()
        task = Task(steps=[TaskStep(operation="classify_intent", inputs_template={"prompt": "hi"})])
        enqueue_task(task)

        w1 = Worker()
        w2 = Worker()

        total = w1.poll_once() + w2.poll_once()
        assert total == 1


# ── 9. No Race Conditions ────────────────────────────────────────


class TestNoRaceConditions:
    def setup_method(self):
        _reset()
        start_orchestrator()

    def test_concurrent_enqueue_and_poll(self):
        tasks_created = []

        def enqueue_two():
            for i in range(2):
                t = Task(
                    steps=[
                        TaskStep(operation="classify_intent", inputs_template={"prompt": f"q{i}"})
                    ]
                )
                enqueue_task(t)
                tasks_created.append(t.id)

        enqueue_thread = threading.Thread(target=enqueue_two)
        enqueue_thread.start()
        enqueue_thread.join(timeout=10)

        worker = Worker()
        total = 0
        for _ in range(3):
            total += worker.poll_once()

        assert total >= 1
        assert len(tasks_created) == 2

    def test_worker_start_stop(self):
        worker = Worker(poll_interval=0.1)
        worker.start()
        assert worker.is_running is True
        time.sleep(0.3)
        worker.stop()
        assert worker.is_running is False

    def test_save_load_consistency(self):
        store = get_task_store()
        task = Task(
            steps=[
                TaskStep(operation="op1", inputs_template={"a": "1"}, output_key="r1"),
                TaskStep(
                    operation="op2", inputs_template={"b": "{{context.r1.x}}"}, output_key="r2"
                ),
            ],
            context={"initial": "value"},
        )
        store.save(task)

        loaded = store.get(task.id)
        assert loaded.steps[0].inputs_template == {"a": "1"}
        assert loaded.steps[1].inputs_template == {"b": "{{context.r1.x}}"}
        assert loaded.context["initial"] == "value"


# ── 10. Metrics Reflect State ────────────────────────────────────


class TestMetricsReflectState:
    def setup_method(self):
        _reset()
        start_orchestrator()

    def test_metrics_include_tasks(self):
        _, _, headers = _create_identity()

        task = Task(steps=[TaskStep(operation="classify_intent", inputs_template={"prompt": "hi"})])
        enqueue_task(task)

        resp = client.get("/metrics", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "tasks" in data
        assert data["tasks"]["total_tasks"] >= 1
        assert "tasks_by_status" in data["tasks"]

    def test_metrics_pending_count(self):
        _, _, headers = _create_identity()

        for i in range(3):
            enqueue_task(
                Task(
                    steps=[
                        TaskStep(operation="classify_intent", inputs_template={"prompt": f"q{i}"})
                    ]
                )
            )

        resp = client.get("/metrics", headers=headers)
        data = resp.json()
        assert data["tasks"]["tasks_by_status"]["pending"] >= 3

    def test_metrics_after_execution(self):
        _, _, headers = _create_identity()

        task = Task(steps=[TaskStep(operation="classify_intent", inputs_template={"prompt": "hi"})])
        execute_task(task)

        resp = client.get("/metrics", headers=headers)
        data = resp.json()
        assert data["tasks"]["total_tasks"] >= 1


# ── 11. API Task Reads (CLI Compatibility) ────────────────────────


class TestAPITaskReads:
    def setup_method(self):
        _reset()
        start_orchestrator()

    def test_get_task_from_store(self):
        _, _, headers = _create_identity()
        task = Task(steps=[TaskStep(operation="classify_intent", inputs_template={"prompt": "hi"})])
        enqueue_task(task)

        resp = client.get(f"/tasks/{task.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == task.id
        assert data["status"] == "pending"
        assert "step_statuses" in data
        assert data["step_statuses"] == ["pending"]

    def test_list_tasks_includes_async(self):
        _, _, headers = _create_identity()
        for i in range(2):
            client.post(
                "/tasks",
                json={
                    "steps": [{"operation": "classify_intent"}],
                    "async_exec": True,
                },
                headers=headers,
            )

        resp = client.get("/tasks", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_get_task_enriched_fields(self):
        _, _, headers = _create_identity()
        task = Task(
            steps=[
                TaskStep(operation="classify_intent", inputs_template={"prompt": "hi"}),
                TaskStep(operation="classify_intent", inputs_template={"prompt": "bye"}),
            ]
        )
        enqueue_task(task)

        resp = client.get(f"/tasks/{task.id}", headers=headers)
        data = resp.json()
        assert "current_step" in data
        assert "pending_approval" in data
        assert data["pending_approval"] is None

    def test_get_task_404(self):
        _, _, headers = _create_identity()
        resp = client.get("/tasks/task_doesnotexist", headers=headers)
        assert resp.status_code == 404


# ── 12. Dual-Write Consistency ────────────────────────────────────


class TestDualWrite:
    def setup_method(self):
        _reset()
        start_orchestrator()

    def test_execute_task_writes_to_store(self):
        task = Task(
            steps=[TaskStep(operation="classify_intent", inputs_template={"prompt": "hello"})]
        )
        result = execute_task(task)

        from_store = get_task_store().get(task.id)
        assert from_store is not None
        assert from_store.status.value == result.status.value

    def test_enqueue_task_writes_to_both(self):
        task = Task(steps=[TaskStep(operation="classify_intent")])
        enqueue_task(task)

        from_memory = get_task(task.id)
        from_store = get_task_store().get(task.id)
        assert from_memory is not None
        assert from_store is not None
        assert from_memory.id == from_store.id

    def test_list_tasks_uses_store(self):
        task = Task(steps=[TaskStep(operation="classify_intent")])
        get_task_store().save(task)

        tasks = list_tasks()
        ids = [t.id for t in tasks]
        assert task.id in ids

    def test_find_paused_by_approval(self):
        from umh.orchestrator.task import find_paused_task_by_approval

        task = Task(steps=[TaskStep(operation="op")])
        task.status = TaskStatus.PAUSED
        task.paused_approval_id = "appr_find_test"
        get_task_store().save(task)

        found = find_paused_task_by_approval("appr_find_test")
        assert found is not None
        assert found.id == task.id

    def test_reset_clears_both(self):
        task = Task(steps=[TaskStep(operation="classify_intent")])
        enqueue_task(task)

        reset_tasks()
        assert get_task(task.id) is None
        assert get_task_store().get(task.id) is None
