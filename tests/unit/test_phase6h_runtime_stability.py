"""Phase 6H Runtime Stability Tests — comprehensive stability and recovery scenarios.

Verifies:
- Tasks survive in-memory dict clearing (store persistence)
- Worker crash recovery: clean restart, pickup after restart, stuck detection
- Retry flow: new task creation, step preservation, chain, cancel-then-retry
- Concurrent load: sequential processing, enqueue during execution, volume
- Edge cases: empty state, step limits, invalid state transitions
- API under load: rapid requests, missing tasks, metrics consistency
"""

import sys
import os

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase6h")
os.environ["UMH_TASK_BACKEND"] = "memory"

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from umh.control.api import app
from umh.control.identity import get_identity_store
from umh.events.stream import reset_event_stream
from umh.execution.approval import get_approval_store
from umh.orchestrator import task as task_module
from umh.orchestrator.engine import reset_orchestrator, start_orchestrator
from umh.orchestrator.task import (
    Task,
    TaskStatus,
    TaskStep,
    StepStatus,
    cancel_task,
    enqueue_task,
    execute_task,
    get_task,
    list_tasks,
    reset_tasks,
    retry_task,
)
from umh.orchestrator.task_store import (
    InMemoryTaskBackend,
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


def _make_task(
    step_count: int = 1,
    status: TaskStatus = TaskStatus.PENDING,
    issued_by: str = "test",
) -> Task:
    """Create a task with N steps for testing."""
    steps = [
        TaskStep(
            operation=f"op_{i}",
            inputs_template={"prompt": f"test_{i}"},
        )
        for i in range(step_count)
    ]
    task = Task(steps=steps, issued_by=issued_by)
    task.status = status
    return task


# ── Restart Recovery ──────────────────────────────────────────────────


class TestRestartRecovery:
    """Verify tasks persist in the store even when the in-memory dict is cleared."""

    def setup_method(self):
        _reset()
        start_orchestrator()

    def test_tasks_survive_memory_clear(self):
        task = _make_task()
        enqueue_task(task)
        task_id = task.id

        # Clear in-memory dict, simulating a process restart
        with task_module._tasks_lock:
            task_module._tasks.clear()

        # get_task falls back to store
        recovered = get_task(task_id)
        assert recovered is not None
        assert recovered.id == task_id
        assert recovered.status == TaskStatus.PENDING

    def test_paused_task_survives_restart(self):
        task = _make_task()
        task.status = TaskStatus.PAUSED
        task.paused_approval_id = "approval_test_123"
        task.paused_step_index = 0
        task.paused_reason = "needs approval"

        # Save directly to store via enqueue (sets to PENDING first, so save manually)
        from umh.orchestrator.task_store import get_task_store

        store = get_task_store()
        store.save(task)

        # Also save to in-memory dict so _save_task wrote it
        with task_module._tasks_lock:
            task_module._tasks[task.id] = task

        # Clear in-memory dict
        with task_module._tasks_lock:
            task_module._tasks.clear()

        recovered = get_task(task.id)
        assert recovered is not None
        assert recovered.status == TaskStatus.PAUSED
        assert recovered.paused_approval_id == "approval_test_123"

    def test_completed_task_survives(self):
        task = _make_task()
        result = execute_task(task)
        task_id = result.id

        # Clear in-memory dict
        with task_module._tasks_lock:
            task_module._tasks.clear()

        recovered = get_task(task_id)
        assert recovered is not None
        assert recovered.status == TaskStatus.COMPLETED

    def test_multiple_tasks_survive(self):
        task_ids = []
        for i in range(5):
            task = _make_task(issued_by=f"user_{i}")
            enqueue_task(task)
            task_ids.append(task.id)

        # Clear in-memory dict
        with task_module._tasks_lock:
            task_module._tasks.clear()

        # list_tasks falls back to store
        all_tasks = list_tasks()
        recovered_ids = {t.id for t in all_tasks}
        assert len(all_tasks) >= 5
        for tid in task_ids:
            assert tid in recovered_ids


# ── Worker Crash Recovery ─────────────────────────────────────────────


class TestWorkerCrashRecovery:
    """Verify worker handles restarts, stuck tasks, and recovery correctly."""

    def setup_method(self):
        _reset()
        start_orchestrator()

    def test_worker_restarts_cleanly(self):
        w = Worker(poll_interval=10.0)
        w.start()
        assert w.is_running is True
        w.stop()
        assert w.is_running is False

        # Start again — no errors
        w2 = Worker(poll_interval=10.0)
        w2.start()
        assert w2.is_running is True
        w2.stop()
        assert w2.is_running is False

    def test_worker_picks_up_after_restart(self):
        store = reset_task_store(backend=InMemoryTaskBackend())

        # First task
        t1 = _make_task()
        store.save(t1)

        w1 = Worker()
        processed = w1.poll_once()
        assert processed >= 1

        # Simulate restart
        w1.stop()

        # Second task
        t2 = _make_task()
        store.save(t2)

        w2 = Worker()
        processed2 = w2.poll_once()
        assert processed2 >= 1

        # Both tasks should be processed
        result1 = store.get(t1.id)
        result2 = store.get(t2.id)
        assert result1 is not None
        assert result2 is not None
        # t1 was claimed and executed by w1, should not be PENDING
        assert result1.status != TaskStatus.PENDING
        # t2 was claimed and executed by w2, should not be PENDING
        assert result2.status != TaskStatus.PENDING

    def test_stuck_task_detected(self):
        backend = InMemoryTaskBackend()
        store = reset_task_store(backend=backend)

        task = _make_task()
        backend.save(task)
        backend.claim_task(task.id, worker_id="dead_worker")

        # Backdate claimed_at to simulate stuck task
        past = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        backend._claimed_at[task.id] = past

        w = Worker()
        w.poll_once()

        recovered = backend.get(task.id)
        assert recovered is not None
        assert recovered.status == TaskStatus.FAILED
        assert "stuck" in recovered.error

    def test_no_duplicate_after_recovery(self):
        backend = InMemoryTaskBackend()
        store = reset_task_store(backend=backend)

        task = _make_task()
        backend.save(task)
        backend.claim_task(task.id, worker_id="dead_worker")

        past = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        backend._claimed_at[task.id] = past

        w = Worker()
        # First poll recovers the stuck task
        w.poll_once()
        assert backend.get(task.id).status == TaskStatus.FAILED

        # Second poll should NOT re-process it (it's FAILED, not PENDING)
        initial_processed = w._tasks_processed
        w.poll_once()
        assert w._tasks_processed == initial_processed


# ── Retry Flow ────────────────────────────────────────────────────────


class TestRetryFlow:
    """Verify retry creates new tasks with correct state and chains work."""

    def setup_method(self):
        _reset()
        start_orchestrator()

    def test_retry_creates_new_task(self):
        task = _make_task()
        task.status = TaskStatus.FAILED
        task.error = "step 0 (op_0) failed: test"
        from umh.orchestrator.task_store import get_task_store

        store = get_task_store()
        store.save(task)
        with task_module._tasks_lock:
            task_module._tasks[task.id] = task

        new_task = retry_task(task.id)
        assert new_task is not None
        assert new_task.id != task.id
        assert new_task.status == TaskStatus.PENDING
        assert new_task.context.get("retried_from") == task.id

    def test_retry_preserves_steps(self):
        task = _make_task(step_count=3)
        task.status = TaskStatus.FAILED
        task.error = "step failed"
        # Mark some steps as completed/failed
        task.steps[0].status = StepStatus.COMPLETED
        task.steps[1].status = StepStatus.FAILED
        task.steps[2].status = StepStatus.SKIPPED

        from umh.orchestrator.task_store import get_task_store

        store = get_task_store()
        store.save(task)
        with task_module._tasks_lock:
            task_module._tasks[task.id] = task

        new_task = retry_task(task.id)
        assert new_task is not None
        assert len(new_task.steps) == 3

        # All steps in the new task should be fresh (PENDING)
        for step in new_task.steps:
            assert step.status == StepStatus.PENDING
            assert step.result is None

        # Operations should match
        for i in range(3):
            assert new_task.steps[i].operation == task.steps[i].operation

    def test_retry_chain(self):
        # First task fails
        task1 = _make_task()
        task1.status = TaskStatus.FAILED
        task1.error = "fail 1"
        from umh.orchestrator.task_store import get_task_store

        store = get_task_store()
        store.save(task1)
        with task_module._tasks_lock:
            task_module._tasks[task1.id] = task1

        # Retry creates task2
        task2 = retry_task(task1.id)
        assert task2 is not None
        assert task2.context["retried_from"] == task1.id

        # task2 also fails
        task2.status = TaskStatus.FAILED
        task2.error = "fail 2"
        store.save(task2)
        with task_module._tasks_lock:
            task_module._tasks[task2.id] = task2

        # Retry creates task3
        task3 = retry_task(task2.id)
        assert task3 is not None
        assert task3.context["retried_from"] == task2.id

        # All three are distinct
        assert len({task1.id, task2.id, task3.id}) == 3

    def test_cancel_then_retry_rejected(self):
        task = _make_task()
        enqueue_task(task)

        result = cancel_task(task.id)
        assert result is not None
        assert result.status == TaskStatus.CANCELLED

        # Retry should be rejected — only FAILED can retry
        new_task = retry_task(task.id)
        assert new_task is None


# ── Concurrent Load ───────────────────────────────────────────────────


class TestConcurrentLoad:
    """Verify system handles volume and sequential processing correctly."""

    def setup_method(self):
        _reset()
        start_orchestrator()

    def test_many_tasks_sequential(self):
        backend = InMemoryTaskBackend()
        store = reset_task_store(backend=backend)

        for i in range(10):
            t = _make_task(issued_by=f"user_{i}")
            backend.save(t)

        w = Worker()
        total_processed = 0
        # Poll multiple times to process all tasks
        for _ in range(15):
            total_processed += w.poll_once()

        # All 10 should have been processed
        assert total_processed >= 10
        pending = backend.list_by_status(TaskStatus.PENDING)
        assert len(pending) == 0

    def test_enqueue_during_execution(self):
        backend = InMemoryTaskBackend()
        store = reset_task_store(backend=backend)

        # Enqueue 3 tasks
        for i in range(3):
            t = _make_task()
            backend.save(t)

        w = Worker()
        w.poll_once()

        # Enqueue more while previous batch was just processed
        for i in range(3):
            t = _make_task()
            backend.save(t)

        w.poll_once()

        # No crashes, and all should be processed
        pending = backend.list_by_status(TaskStatus.PENDING)
        assert len(pending) == 0

    def test_task_store_handles_volume(self):
        backend = InMemoryTaskBackend()
        store = reset_task_store(backend=backend)

        # Save 50 tasks with varied statuses
        for i in range(50):
            t = _make_task()
            if i % 5 == 0:
                t.status = TaskStatus.COMPLETED
            elif i % 5 == 1:
                t.status = TaskStatus.FAILED
            elif i % 5 == 2:
                t.status = TaskStatus.PAUSED
            elif i % 5 == 3:
                t.status = TaskStatus.CANCELLED
            # else PENDING
            backend.save(t)

        all_tasks = backend.list_all()
        assert len(all_tasks) == 50

        completed = backend.list_by_status(TaskStatus.COMPLETED)
        assert len(completed) == 10

        failed = backend.list_by_status(TaskStatus.FAILED)
        assert len(failed) == 10

        paused = backend.list_by_status(TaskStatus.PAUSED)
        assert len(paused) == 10

        cancelled = backend.list_by_status(TaskStatus.CANCELLED)
        assert len(cancelled) == 10

        pending = backend.list_by_status(TaskStatus.PENDING)
        assert len(pending) == 10


# ── Edge Cases ────────────────────────────────────────────────────────


class TestEdgeCases:
    """Boundary conditions and invalid state transitions."""

    def setup_method(self):
        _reset()
        start_orchestrator()

    def test_empty_state(self):
        tasks = list_tasks()
        assert tasks == []

        # Metrics should work with zero data
        from umh.control.api import _task_metrics

        m = _task_metrics()
        assert m["total_tasks"] == 0
        assert isinstance(m["tasks_by_status"], dict)
        assert isinstance(m["recent_tasks"], list)
        assert len(m["recent_tasks"]) == 0

    def test_task_with_no_steps_rejected(self):
        """The API rejects empty steps; the Task dataclass allows it but is degenerate."""
        # API-level rejection (the primary guard)
        _, _, headers = _create_identity()
        resp = client.post(
            "/tasks",
            json={"steps": [], "context": {}},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_task_with_max_steps(self):
        """Creating a Task with exactly 10 steps works."""
        steps = [TaskStep(operation=f"op_{i}", inputs_template={"p": str(i)}) for i in range(10)]
        task = Task(steps=steps)
        assert len(task.steps) == 10
        assert task.status == TaskStatus.PENDING

    def test_task_over_max_steps(self):
        """Creating a Task with 11 steps raises ValueError."""
        steps = [TaskStep(operation=f"op_{i}", inputs_template={"p": str(i)}) for i in range(11)]
        try:
            Task(steps=steps)
            assert False, "Expected ValueError for >10 steps"
        except ValueError as e:
            assert "max steps" in str(e).lower()

    def test_cancel_completed_rejected(self):
        task = _make_task()
        result = execute_task(task)
        assert result.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)

        if result.status == TaskStatus.COMPLETED:
            cancelled = cancel_task(result.id)
            assert cancelled is None

    def test_cancel_failed_rejected(self):
        task = _make_task()
        task.status = TaskStatus.FAILED
        task.error = "test error"
        from umh.orchestrator.task_store import get_task_store

        store = get_task_store()
        store.save(task)
        with task_module._tasks_lock:
            task_module._tasks[task.id] = task

        cancelled = cancel_task(task.id)
        assert cancelled is None

    def test_resume_non_paused_returns_none(self):
        """resume_task on a completed task returns None."""
        from umh.orchestrator.task import resume_task

        task = _make_task()
        result = execute_task(task)

        resumed = resume_task(result.id, "fake_approval")
        assert resumed is None


# ── API Under Load ────────────────────────────────────────────────────


class TestAPIUnderLoad:
    """Verify API handles rapid requests and edge cases."""

    def setup_method(self):
        _reset()
        start_orchestrator()
        self._identity, self._key, self._headers = _create_identity()

    def test_api_handles_rapid_requests(self):
        """Send 10 rapid POST /run requests, all return valid responses."""
        responses = []
        for i in range(10):
            resp = client.post(
                "/run",
                json={"objective": f"rapid test {i}", "dry_run": True},
                headers=self._headers,
            )
            responses.append(resp)

        for resp in responses:
            assert resp.status_code == 200
            data = resp.json()
            assert "plan_id" in data
            assert "status" in data

    def test_api_handles_missing_tasks(self):
        """GET /tasks/nonexistent returns 404."""
        resp = client.get("/tasks/nonexistent_task_id", headers=self._headers)
        assert resp.status_code == 404

    def test_api_metrics_consistent(self):
        """Metrics fields are always present even with zero data."""
        resp = client.get("/metrics", headers=self._headers)
        assert resp.status_code == 200
        data = resp.json()

        # Core metric sections must be present
        assert "tasks" in data
        assert "total_tasks" in data["tasks"]
        assert "tasks_by_status" in data["tasks"]
        assert "paused_tasks" in data["tasks"]
        assert "recent_tasks" in data["tasks"]

        # All status keys present in tasks_by_status
        for status in ["pending", "running", "completed", "failed", "paused", "cancelled"]:
            assert status in data["tasks"]["tasks_by_status"]
