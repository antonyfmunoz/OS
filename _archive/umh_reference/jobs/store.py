"""Job store — CRUD + lifecycle-validated status updates with optional persistence.

All status mutations go through lifecycle.transition() to enforce
the state machine. No direct status assignment. When a persistence
backend is provided, all writes are durably persisted after valid
transitions. Job claiming is atomic under the store lock.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import threading
from typing import Any

from umh.jobs.lifecycle import transition
from umh.jobs.models import ExecutionJob, JobResult, JobStatus, _gen_job_id


class JobStore:
    """Job store with optional durable persistence backend and atomic job claiming."""

    def __init__(
        self,
        persistence: Any | None = None,
        lock_manager: Any | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, ExecutionJob] = {}
        self._persistence = persistence
        self._lock_manager = lock_manager

        if self._persistence is not None:
            self._rehydrate()

    def _rehydrate(self) -> None:
        """Load persisted jobs into memory on init."""
        try:
            jobs = self._persistence.load_all_jobs()
            with self._lock:
                for job in jobs:
                    self._jobs[job.job_id] = job
        except Exception:
            pass

    def _persist(self, job: ExecutionJob) -> None:
        """Persist job to backend if available. Non-fatal on error."""
        if self._persistence is None:
            return
        try:
            self._persistence.save_job(job)
        except Exception:
            pass

    def create_job(
        self,
        task_id: str,
        node_id: str,
        *,
        command: list[str] | None = None,
        timeout_seconds: int = 60,
        max_attempts: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionJob:
        job = ExecutionJob(
            job_id=_gen_job_id(),
            task_id=task_id,
            node_id=node_id,
            command=command,
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
            metadata=metadata or {},
        )
        with self._lock:
            self._jobs[job.job_id] = job
        self._persist(job)
        return job

    def get_job(self, job_id: str) -> ExecutionJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update_job(self, job: ExecutionJob) -> None:
        with self._lock:
            self._jobs[job.job_id] = job
        self._persist(job)

    def list_jobs(
        self,
        *,
        status: JobStatus | None = None,
        node_id: str | None = None,
    ) -> list[ExecutionJob]:
        with self._lock:
            jobs = list(self._jobs.values())
        if status is not None:
            jobs = [j for j in jobs if j.status == status]
        if node_id is not None:
            jobs = [j for j in jobs if j.node_id == node_id]
        return jobs

    def mark_submitted(self, job_id: str) -> ExecutionJob:
        return self._transition(job_id, JobStatus.SUBMITTED)

    def mark_running(self, job_id: str) -> ExecutionJob:
        return self._transition(job_id, JobStatus.RUNNING)

    def mark_succeeded(self, job_id: str, result: dict[str, Any] | None = None) -> ExecutionJob:
        job = self._transition(job_id, JobStatus.SUCCEEDED)
        if result is not None:
            job.result = result
            self._persist(job)
        return job

    def mark_failed(self, job_id: str, error: str = "") -> ExecutionJob:
        return self._transition(job_id, JobStatus.FAILED, reason=error)

    def mark_timeout(self, job_id: str, error: str = "") -> ExecutionJob:
        return self._transition(job_id, JobStatus.TIMEOUT, reason=error)

    def mark_orphaned(self, job_id: str, reason: str = "") -> ExecutionJob:
        return self._transition(job_id, JobStatus.ORPHANED, reason=reason)

    def cancel_job(self, job_id: str) -> ExecutionJob:
        return self._transition(job_id, JobStatus.CANCELLED)

    def claim_job(
        self,
        node_id: str,
        *,
        ranker: Any | None = None,
    ) -> ExecutionJob | None:
        """Atomically claim the best eligible SUBMITTED job for a node.

        Under the store lock: finds SUBMITTED jobs, ranks them (by ranker
        if provided, else FIFO by submitted_at), acquires a lock (if
        lock_manager is present), transitions to RUNNING, and assigns
        the node_id. Returns None if no eligible job exists.
        """
        with self._lock:
            submitted = [j for j in self._jobs.values() if j.status == JobStatus.SUBMITTED]
            if ranker is not None:
                try:
                    candidates = ranker(submitted)
                except Exception:
                    candidates = sorted(submitted, key=lambda j: j.submitted_at or j.created_at)
            else:
                candidates = sorted(submitted, key=lambda j: j.submitted_at or j.created_at)
            for job in candidates:
                if self._lock_manager is not None:
                    lock = self._lock_manager.acquire_lock(job.job_id, node_id)
                    if lock is None:
                        continue

                try:
                    transition(job, JobStatus.RUNNING, reason=f"claimed by {node_id}")
                except ValueError:
                    if self._lock_manager is not None:
                        self._lock_manager.release_lock(job.job_id, node_id=node_id)
                    continue

                job.node_id = node_id
                break
            else:
                return None

        self._persist(job)
        return job

    def delete_job(self, job_id: str) -> bool:
        with self._lock:
            removed = self._jobs.pop(job_id, None) is not None
        if removed and self._persistence is not None:
            try:
                self._persistence.delete_job(job_id)
            except Exception:
                pass
        return removed

    def clear(self) -> None:
        with self._lock:
            self._jobs.clear()

    def _transition(self, job_id: str, new_status: JobStatus, reason: str = "") -> ExecutionJob:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(f"Job not found: {job_id}")
            transition(job, new_status, reason=reason)
        self._persist(job)
        return job
