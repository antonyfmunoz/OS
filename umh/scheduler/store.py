"""UMH Scheduler Store — thread-safe in-memory store for scheduled workflows."""

from __future__ import annotations

import threading

from umh.core.clock import iso_now as _iso_now
from umh.scheduler.models import ScheduledWorkflow


class ScheduleStore:
    """Thread-safe in-memory store for ScheduledWorkflow instances."""

    def __init__(self) -> None:
        self._workflows: dict[str, ScheduledWorkflow] = {}
        self._lock = threading.Lock()

    def create(self, workflow: ScheduledWorkflow) -> ScheduledWorkflow:
        """Store a new workflow. Returns the stored instance."""
        with self._lock:
            self._workflows[workflow.id] = workflow
        return workflow

    def get(self, schedule_id: str) -> ScheduledWorkflow | None:
        """Return a workflow by ID or None if not found."""
        with self._lock:
            return self._workflows.get(schedule_id)

    def list_all(self) -> list[ScheduledWorkflow]:
        """Return all workflows."""
        with self._lock:
            return list(self._workflows.values())

    def list_enabled(self) -> list[ScheduledWorkflow]:
        """Return only enabled workflows."""
        with self._lock:
            return [w for w in self._workflows.values() if w.enabled]

    def enable(self, schedule_id: str) -> ScheduledWorkflow | None:
        """Enable a workflow. Returns updated workflow or None if not found."""
        with self._lock:
            wf = self._workflows.get(schedule_id)
            if wf is None:
                return None
            wf.enabled = True
            wf.updated_at = _iso_now()
            return wf

    def disable(self, schedule_id: str) -> ScheduledWorkflow | None:
        """Disable a workflow. Returns updated workflow or None if not found."""
        with self._lock:
            wf = self._workflows.get(schedule_id)
            if wf is None:
                return None
            wf.enabled = False
            wf.updated_at = _iso_now()
            return wf

    def delete(self, schedule_id: str) -> bool:
        """Remove a workflow. Returns True if it existed."""
        with self._lock:
            return self._workflows.pop(schedule_id, None) is not None

    def update_run_status(self, schedule_id: str, status: str, next_run: str) -> None:
        """Update run tracking fields after a scheduled execution."""
        with self._lock:
            wf = self._workflows.get(schedule_id)
            if wf is None:
                return
            wf.last_run_at = _iso_now()
            wf.last_run_status = status
            wf.next_run_at = next_run
            wf.run_count += 1
            wf.updated_at = wf.last_run_at

    def get_runs_today(self, schedule_id: str) -> int:
        """Return the total run count for a workflow."""
        with self._lock:
            wf = self._workflows.get(schedule_id)
            return wf.run_count if wf else 0


_store: ScheduleStore | None = None
_store_lock = threading.Lock()


def get_schedule_store() -> ScheduleStore:
    """Return the singleton ScheduleStore, creating it if needed."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = ScheduleStore()
    return _store


def reset_schedule_store() -> ScheduleStore:
    """Reset the singleton store. Returns the new instance."""
    global _store
    with _store_lock:
        _store = ScheduleStore()
    return _store
