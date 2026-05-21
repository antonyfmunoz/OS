"""Worker loop — pull-based job execution for remote nodes.

A WorkerLoop polls the JobStore for claimable SUBMITTED jobs,
executes them via the existing command execution system, and
updates job state on completion or failure.

No imports from umh/cells, umh/environments, umh/adapters.
subprocess is NOT used here — execution is delegated to a
caller-provided executor callback.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from umh.core.clock import iso_now as _iso_now
from umh.jobs.models import ExecutionJob, JobStatus
from umh.jobs.store import JobStore

_log = logging.getLogger(__name__)

_DEFAULT_POLL_INTERVAL_S = 5.0


@dataclass
class WorkerStats:
    """Running statistics for a worker loop."""

    jobs_claimed: int = 0
    jobs_succeeded: int = 0
    jobs_failed: int = 0
    polls: int = 0
    errors: int = 0
    last_poll_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "jobs_claimed": self.jobs_claimed,
            "jobs_succeeded": self.jobs_succeeded,
            "jobs_failed": self.jobs_failed,
            "polls": self.polls,
            "errors": self.errors,
            "last_poll_at": self.last_poll_at,
        }


@dataclass
class ExecutionResult:
    """Result of executing a job command."""

    success: bool
    output: dict[str, Any] | None = None
    error: str = ""


class WorkerLoop:
    """Pull-based worker that claims and executes jobs from a shared store.

    The executor callback receives an ExecutionJob and returns an
    ExecutionResult. This keeps subprocess usage out of the worker
    module — the caller decides how to execute.
    """

    def __init__(
        self,
        node_id: str,
        store: JobStore,
        *,
        executor: Callable[[ExecutionJob], ExecutionResult] | None = None,
        poll_interval_s: float = _DEFAULT_POLL_INTERVAL_S,
    ) -> None:
        if not node_id:
            raise ValueError("node_id must be non-empty")

        self._node_id = node_id
        self._store = store
        self._executor = executor
        self._poll_interval_s = poll_interval_s
        self._active = False
        self._current_job: ExecutionJob | None = None
        self._stats = WorkerStats()

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def active(self) -> bool:
        return self._active

    @property
    def current_job(self) -> ExecutionJob | None:
        return self._current_job

    @property
    def stats(self) -> WorkerStats:
        return self._stats

    @property
    def poll_interval_s(self) -> float:
        return self._poll_interval_s

    def start(self) -> None:
        self._active = True

    def stop(self) -> None:
        self._active = False
        self._current_job = None

    def poll_once(self) -> ExecutionJob | None:
        """Single poll cycle: claim a job, execute it, update state.

        Returns the job that was processed, or None if no work was available.
        This is the unit-testable core — the daemon calls this in a loop.
        """
        if not self._active:
            return None

        self._stats.polls += 1
        self._stats.last_poll_at = _iso_now()

        try:
            job = self._store.claim_job(self._node_id)
        except Exception as e:
            _log.debug("Claim error (non-fatal): %s", e)
            self._stats.errors += 1
            return None

        if job is None:
            return None

        self._current_job = job
        self._stats.jobs_claimed += 1
        _log.info("Worker %s claimed job %s", self._node_id, job.job_id)

        self._execute_job(job)
        self._current_job = None
        return job

    def _execute_job(self, job: ExecutionJob) -> None:
        """Execute a job and update its state in the store."""
        if self._executor is None:
            self._store.mark_failed(job.job_id, "no executor configured")
            self._stats.jobs_failed += 1
            return

        try:
            result = self._executor(job)
        except Exception as e:
            _log.warning("Executor error for job %s: %s", job.job_id, e)
            try:
                self._store.mark_failed(job.job_id, str(e))
            except ValueError:
                pass
            self._stats.jobs_failed += 1
            return

        if result.success:
            try:
                self._store.mark_succeeded(job.job_id, result.output)
                self._stats.jobs_succeeded += 1
            except ValueError as e:
                _log.warning("State update error for job %s: %s", job.job_id, e)
                self._stats.errors += 1
        else:
            try:
                self._store.mark_failed(job.job_id, result.error)
                self._stats.jobs_failed += 1
            except ValueError as e:
                _log.warning("State update error for job %s: %s", job.job_id, e)
                self._stats.errors += 1

        if self._store._lock_manager is not None:
            try:
                self._store._lock_manager.release_lock(job.job_id, node_id=self._node_id)
            except Exception:
                pass
