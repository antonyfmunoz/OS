"""UMH Background Worker — polls for pending tasks and executes them.

Simple polling loop. No queues, no Celery, no async. Executes one step
at a time through the existing execute() path. Pauses on approval,
resumes automatically when approval is granted (via orchestrator rules).

Usage:
    python3 -m umh.orchestrator.worker          # run standalone
    from umh.orchestrator.worker import start_worker  # start in background thread
"""

from __future__ import annotations

import logging
import sys
import threading
import time
import uuid

sys.path.insert(0, "/opt/OS")

from umh.core.clock import iso_now as _iso_now
from umh.orchestrator.task import (
    TaskStatus,
    execute_task,
    resume_task,
)
from umh.orchestrator.task_store import get_task_store

_log = logging.getLogger(__name__)

_DEFAULT_POLL_INTERVAL = 2.0


class Worker:
    """Background task worker. Polls for PENDING tasks and executes them."""

    def __init__(self, poll_interval: float = _DEFAULT_POLL_INTERVAL) -> None:
        self._poll_interval = poll_interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._worker_id = f"worker_{uuid.uuid4().hex[:8]}"
        self._started_at = ""
        self._last_heartbeat = ""
        self._current_task_id: str | None = None
        self._tasks_processed = 0
        self._poll_cycles = 0

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._started_at = _iso_now()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="umh-worker")
        self._thread.start()
        _log.info("Worker started (poll_interval=%.1fs)", self._poll_interval)

    def stop(self) -> None:
        self._running = False
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        _log.info("Worker stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    def heartbeat(self) -> dict:
        """Return current worker status as a structured dict."""
        return {
            "worker_id": self._worker_id,
            "started_at": self._started_at,
            "last_heartbeat": self._last_heartbeat,
            "current_task_id": self._current_task_id,
            "tasks_processed": self._tasks_processed,
            "poll_cycles": self._poll_cycles,
            "is_running": self._running,
        }

    def _run_loop(self) -> None:
        while self._running:
            try:
                self._poll_once()
            except Exception as exc:
                _log.error("Worker poll error: %s", exc)

            self._stop_event.wait(timeout=self._poll_interval)

    def poll_once(self) -> int:
        """Run a single poll cycle. Returns number of tasks processed."""
        return self._poll_once()

    def _resolve_goal(self, task) -> "Goal | None":
        """Find the goal associated with a task, if any."""
        goal_id = task.context.get("goal_id", "")
        if not goal_id:
            return None
        from umh.goals.store import get_goal_store

        return get_goal_store().get(goal_id)

    def _compute_age(self, task) -> float:
        """Compute task age in seconds from creation time."""
        from datetime import datetime, timezone

        try:
            created = datetime.fromisoformat(task.created_at)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            return max(0.0, (now - created).total_seconds())
        except (ValueError, TypeError):
            return 0.0

    def _poll_once(self) -> int:
        """Check for PENDING tasks and execute them. Returns count processed."""
        from umh.attention.controls import get_system_controls
        from umh.attention.queue import get_attention_queue
        from umh.attention.scorer import score_task_with_controls
        from umh.goals.models import GoalPriority

        store = get_task_store()
        processed = 0

        self._last_heartbeat = _iso_now()
        self._poll_cycles += 1

        # Score and enqueue PENDING tasks
        queue = get_attention_queue()
        queue.clear()

        pending = store.list_by_status(TaskStatus.PENDING)
        all_tasks = pending  # used for dependency scoring
        for task in pending:
            goal = self._resolve_goal(task)
            goal_priority = goal.priority if goal is not None else GoalPriority.MEDIUM
            age = self._compute_age(task)
            entry, _influence = score_task_with_controls(task, goal_priority, age, all_tasks)
            queue.enqueue(entry)

        # Apply starvation boosts (use 0 as baseline — each entry carries its own age)
        queue.apply_starvation_boost_all(0)

        # Respect max_concurrent_tasks from system controls
        controls = get_system_controls()
        running_count = len(store.list_by_status(TaskStatus.RUNNING))

        # Dequeue by priority
        while running_count < controls.max_concurrent_tasks:
            entry = queue.dequeue()
            if entry is None:
                break

            task_id = entry.task_id

            if not self._running and self._thread is not None:
                break

            claimed = store.claim_task(task_id, worker_id=self._worker_id)
            if not claimed:
                continue

            running_count += 1
            self._current_task_id = task_id
            _log.info("Worker executing task %s (score=%.3f)", task_id, entry.priority_score)

            fresh = store.get(task_id)
            if fresh is None:
                self._current_task_id = None
                continue
            fresh.status = TaskStatus.RUNNING

            result = execute_task(fresh)
            store.save(result)
            processed += 1
            self._tasks_processed += 1
            self._current_task_id = None

            _log.info("Worker task %s → %s", task_id, result.status.value)

        # Recover stuck tasks before checking resumable
        stuck = store.list_stuck_tasks(timeout_seconds=300)
        for task in stuck:
            store.recover_stuck_task(task.id)
            _log.warning("Recovered stuck task %s", task.id)

        resumable = self._find_resumable_tasks(store)
        for task_id, approval_id in resumable:
            if not self._running and self._thread is not None:
                break

            _log.info("Worker resuming task %s (approval=%s)", task_id, approval_id)
            result = resume_task(task_id, approval_id)
            if result is not None:
                store.save(result)
                processed += 1
                _log.info("Worker resumed task %s → %s", task_id, result.status.value)

        return processed

    def _find_resumable_tasks(self, store) -> list[tuple[str, str]]:
        """Find PAUSED tasks whose approval has been granted."""
        from umh.execution.approval import ApprovalStatus, get_approval_store

        paused = store.list_by_status(TaskStatus.PAUSED)
        resumable = []

        approval_store = get_approval_store()
        for task in paused:
            if not task.paused_approval_id:
                continue
            approval = approval_store.get(task.paused_approval_id)
            if approval is not None and approval.status == ApprovalStatus.APPROVED:
                resumable.append((task.id, task.paused_approval_id))

        return resumable


_worker: Worker | None = None
_worker_lock = threading.Lock()


def get_worker() -> Worker:
    global _worker
    if _worker is None:
        with _worker_lock:
            if _worker is None:
                _worker = Worker()
    return _worker


def start_worker(poll_interval: float = _DEFAULT_POLL_INTERVAL) -> Worker:
    global _worker
    with _worker_lock:
        if _worker is None:
            _worker = Worker(poll_interval=poll_interval)
        if not _worker.is_running:
            _worker.start()
    return _worker


def stop_worker() -> None:
    global _worker
    with _worker_lock:
        if _worker is not None:
            _worker.stop()
            _worker = None


def reset_worker() -> None:
    stop_worker()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

    from umh.orchestrator.engine import start_orchestrator

    start_orchestrator()

    print("UMH Worker starting...")
    worker = start_worker()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        stop_worker()
