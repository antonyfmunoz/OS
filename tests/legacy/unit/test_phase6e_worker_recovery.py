"""Tests for Phase 6E Agent 3: Worker Heartbeat + Stuck Task Recovery.

Verifies:
- Worker heartbeat returns correct dict structure
- started_at set after start()
- last_heartbeat / poll_cycles update on poll
- tasks_processed increments
- worker_id uniqueness
- claim_task records worker_id and claimed_at
- Double claim fails
- list_stuck_tasks finds expired tasks
- recover_stuck_task marks FAILED with error message
- Worker recovers stuck tasks during poll
"""

import sys
import os

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase6e")
os.environ["UMH_TASK_BACKEND"] = "memory"

from datetime import datetime, timedelta, timezone

from umh.orchestrator.task import Task, TaskStatus, TaskStep, reset_tasks
from umh.orchestrator.task_store import (
    InMemoryTaskBackend,
    TaskStore,
    reset_task_store,
)
from umh.orchestrator.worker import Worker, reset_worker


def _make_task(status: TaskStatus = TaskStatus.PENDING) -> Task:
    """Create a minimal task for testing."""
    task = Task(
        steps=[TaskStep(operation="classify_intent", inputs_template={"prompt": "test"})],
        issued_by="test",
    )
    task.status = status
    return task


class TestWorkerHeartbeat:
    def setup_method(self):
        reset_worker()
        reset_tasks()
        reset_task_store(backend=InMemoryTaskBackend())

    def test_heartbeat_returns_dict(self):
        w = Worker()
        hb = w.heartbeat()
        assert isinstance(hb, dict)
        assert "worker_id" in hb
        assert "started_at" in hb
        assert "last_heartbeat" in hb
        assert "current_task_id" in hb
        assert "tasks_processed" in hb
        assert "poll_cycles" in hb
        assert "is_running" in hb

    def test_started_at_set_after_start(self):
        w = Worker(poll_interval=10.0)
        assert w._started_at == ""
        w.start()
        assert w._started_at != ""
        hb = w.heartbeat()
        assert hb["started_at"] != ""
        assert hb["is_running"] is True
        w.stop()

    def test_last_heartbeat_updates_on_poll(self):
        w = Worker()
        assert w._last_heartbeat == ""
        w.poll_once()
        assert w._last_heartbeat != ""

    def test_poll_cycles_increment(self):
        w = Worker()
        assert w._poll_cycles == 0
        w.poll_once()
        assert w._poll_cycles == 1
        w.poll_once()
        assert w._poll_cycles == 2

    def test_tasks_processed_increments(self):
        store = reset_task_store(backend=InMemoryTaskBackend())
        task = _make_task()
        store.save(task)

        w = Worker()
        assert w._tasks_processed == 0
        w.poll_once()
        assert w._tasks_processed == 1

    def test_worker_id_is_unique(self):
        w1 = Worker()
        w2 = Worker()
        assert w1._worker_id != w2._worker_id
        assert w1._worker_id.startswith("worker_")
        assert w2._worker_id.startswith("worker_")


class TestTaskLease:
    def setup_method(self):
        reset_worker()
        reset_tasks()
        self.backend = InMemoryTaskBackend()
        reset_task_store(backend=self.backend)

    def test_claim_task_records_worker_id(self):
        task = _make_task()
        self.backend.save(task)
        result = self.backend.claim_task(task.id, worker_id="worker_abc123")
        assert result is True
        assert self.backend._claimed_by[task.id] == "worker_abc123"

    def test_claimed_at_set(self):
        task = _make_task()
        self.backend.save(task)
        self.backend.claim_task(task.id, worker_id="w1")
        assert task.id in self.backend._claimed_at
        assert self.backend._claimed_at[task.id] != ""

    def test_second_claim_fails(self):
        task = _make_task()
        self.backend.save(task)
        assert self.backend.claim_task(task.id, worker_id="w1") is True
        assert self.backend.claim_task(task.id, worker_id="w2") is False

    def test_list_stuck_tasks_finds_expired(self):
        task = _make_task()
        self.backend.save(task)
        self.backend.claim_task(task.id, worker_id="w1")

        # Manually backdate claimed_at to simulate expiry
        past = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()
        self.backend._claimed_at[task.id] = past

        stuck = self.backend.list_stuck_tasks(timeout_seconds=300)
        assert len(stuck) == 1
        assert stuck[0].id == task.id

    def test_list_stuck_tasks_ignores_fresh(self):
        task = _make_task()
        self.backend.save(task)
        self.backend.claim_task(task.id, worker_id="w1")
        # claimed_at is just now, so not stuck
        stuck = self.backend.list_stuck_tasks(timeout_seconds=300)
        assert len(stuck) == 0

    def test_recover_stuck_task_marks_failed(self):
        task = _make_task()
        self.backend.save(task)
        self.backend.claim_task(task.id, worker_id="w1")

        result = self.backend.recover_stuck_task(task.id)
        assert result is True
        assert task.status == TaskStatus.FAILED
        assert task.error == "stuck: worker lease expired"

    def test_recover_non_running_task_returns_false(self):
        task = _make_task(status=TaskStatus.COMPLETED)
        self.backend.save(task)
        result = self.backend.recover_stuck_task(task.id)
        assert result is False


class TestStuckRecovery:
    def setup_method(self):
        reset_worker()
        reset_tasks()
        self.backend = InMemoryTaskBackend()
        reset_task_store(backend=self.backend)

    def test_worker_recovers_stuck_task_on_poll(self):
        store = reset_task_store(backend=self.backend)

        # Create a task that looks stuck: RUNNING with old claimed_at
        task = _make_task()
        self.backend.save(task)
        self.backend.claim_task(task.id, worker_id="dead_worker")

        # Backdate claimed_at
        past = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()
        self.backend._claimed_at[task.id] = past

        w = Worker()
        w.poll_once()

        # Task should now be FAILED
        recovered = self.backend.get(task.id)
        assert recovered is not None
        assert recovered.status == TaskStatus.FAILED
        assert recovered.error == "stuck: worker lease expired"

    def test_recovered_task_has_error_message(self):
        task = _make_task()
        self.backend.save(task)
        self.backend.claim_task(task.id, worker_id="dead_worker")

        past = (datetime.now(timezone.utc) - timedelta(seconds=400)).isoformat()
        self.backend._claimed_at[task.id] = past

        self.backend.recover_stuck_task(task.id)
        assert task.error == "stuck: worker lease expired"


class TestWorkerMetrics:
    def setup_method(self):
        reset_worker()

    def test_get_worker_metrics_no_worker(self):
        from umh.execution.metrics import get_worker_metrics

        m = get_worker_metrics()
        assert m["is_running"] is False

    def test_get_worker_metrics_with_worker(self):
        from umh.execution.metrics import get_worker_metrics
        from umh.orchestrator.worker import start_worker

        w = start_worker(poll_interval=10.0)
        m = get_worker_metrics()
        assert m["is_running"] is True
        assert m["worker_id"] != ""
        w.stop()
