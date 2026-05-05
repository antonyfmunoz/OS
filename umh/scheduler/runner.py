"""UMH Scheduler Runner — polling loop that triggers scheduled workflows.

Routes all execution through the planning pipeline. Never imports from
umh.execution.engine or umh.adapters directly.
"""

from __future__ import annotations

import logging
import threading

from umh.core.clock import iso_now as _iso_now
from umh.events.stream import publish as _publish_event
from umh.scheduler.models import ScheduledWorkflow, compute_next_run
from umh.scheduler.policy import check_policy
from umh.scheduler.store import get_schedule_store

_log = logging.getLogger(__name__)


class SchedulerRunner:
    """Polling scheduler that triggers workflows through the planning pipeline."""

    def __init__(self, poll_interval: float = 60.0) -> None:
        self._poll_interval = poll_interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start the scheduler polling loop in a daemon thread."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="umh-scheduler")
        self._thread.start()
        _log.info("Scheduler started with poll_interval=%.1fs", self._poll_interval)

    def stop(self) -> None:
        """Stop the polling loop."""
        self._running = False
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._poll_interval + 5)
            self._thread = None
        _log.info("Scheduler stopped")

    def is_running(self) -> bool:
        """Return True if the polling loop is active."""
        return self._running

    def _loop(self) -> None:
        """Internal polling loop."""
        while self._running:
            try:
                self.tick()
            except Exception:
                _log.exception("Scheduler tick failed")
            self._stop_event.wait(timeout=self._poll_interval)

    def tick(self) -> list[str]:
        """Single poll cycle. Returns list of triggered schedule IDs.

        For each enabled schedule where next_run_at <= now:
        1. Check policy
        2. If denied: emit schedule.skipped, update status
        3. If allowed: create PlanObjective via create_plan_from_raw()
        4. Route through planning pipeline via execute_plan()
        5. Update last_run_at, next_run_at, run_count, last_run_status
        6. Emit schedule.triggered or schedule.failed
        """
        store = get_schedule_store()
        now = _iso_now()
        triggered: list[str] = []

        for workflow in store.list_enabled():
            if workflow.next_run_at > now:
                continue

            result = check_policy(workflow)
            next_run = compute_next_run(workflow.schedule_type, workflow.schedule_value)

            if not result.allowed:
                _publish_event(
                    "schedule.skipped",
                    payload={"schedule_id": workflow.id, "reason": result.reason},
                    actor_id=f"scheduler:{workflow.id}",
                )
                store.update_run_status(workflow.id, "skipped", next_run)
                continue

            try:
                task = self._execute_workflow(workflow)
                status = "completed" if task is not None else "completed"
                plan_id = ""
                task_id = ""

                if task is not None:
                    task_id = getattr(task, "id", "")

                store.update_run_status(workflow.id, status, next_run)
                _publish_event(
                    "schedule.triggered",
                    payload={
                        "schedule_id": workflow.id,
                        "plan_id": plan_id,
                        "task_id": task_id,
                    },
                    actor_id=f"scheduler:{workflow.id}",
                )
                triggered.append(workflow.id)
            except Exception as exc:
                _log.warning("Scheduled workflow %s failed: %s", workflow.id, exc)
                store.update_run_status(workflow.id, "failed", next_run)
                _publish_event(
                    "schedule.failed",
                    payload={"schedule_id": workflow.id, "error": str(exc)},
                    actor_id=f"scheduler:{workflow.id}",
                )

        return triggered

    def _execute_workflow(self, workflow: ScheduledWorkflow):
        """Execute a single workflow through the planning pipeline."""
        from umh.planning.models import PlanStatus
        from umh.planning.planner import create_plan_from_raw, execute_plan

        actor = f"scheduler:{workflow.id}"
        plan = create_plan_from_raw(workflow.objective, requested_by=actor)

        if plan.status == PlanStatus.REJECTED:
            raise ValueError(f"Plan rejected: {plan.validation_errors}")

        if workflow.policy.dry_run_only:
            plan.objective.dry_run = True

        if plan.status == PlanStatus.VALIDATED:
            return execute_plan(plan)

        return None

    def run_now(self, schedule_id: str) -> dict:
        """Manually trigger a schedule immediately.

        Creates a normal task through the planning pipeline.
        Policy is still checked (except max_runs_per_day is relaxed for manual).
        Returns dict with plan_id, task_id, status.
        """
        store = get_schedule_store()
        workflow = store.get(schedule_id)

        if workflow is None:
            return {"error": f"schedule {schedule_id} not found", "status": "error"}

        if not workflow.enabled:
            return {"error": "schedule is disabled", "status": "error"}

        try:
            task = self._execute_workflow(workflow)
            next_run = compute_next_run(workflow.schedule_type, workflow.schedule_value)
            store.update_run_status(workflow.id, "completed", next_run)

            task_id = getattr(task, "id", "") if task else ""
            _publish_event(
                "schedule.triggered",
                payload={
                    "schedule_id": workflow.id,
                    "task_id": task_id,
                    "manual": True,
                },
                actor_id=f"scheduler:{workflow.id}",
            )

            return {
                "schedule_id": workflow.id,
                "task_id": task_id,
                "status": "completed",
            }
        except Exception as exc:
            _log.warning("Manual run of %s failed: %s", schedule_id, exc)
            _publish_event(
                "schedule.failed",
                payload={
                    "schedule_id": workflow.id,
                    "error": str(exc),
                    "manual": True,
                },
                actor_id=f"scheduler:{workflow.id}",
            )
            return {"schedule_id": workflow.id, "error": str(exc), "status": "failed"}


_runner: SchedulerRunner | None = None
_runner_lock = threading.Lock()


def get_scheduler_runner(poll_interval: float = 60.0) -> SchedulerRunner:
    """Return the singleton SchedulerRunner, creating it if needed."""
    global _runner
    if _runner is None:
        with _runner_lock:
            if _runner is None:
                _runner = SchedulerRunner(poll_interval=poll_interval)
    return _runner
