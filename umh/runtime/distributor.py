"""Distributor — control plane job assignment for pull-based execution.

The Distributor does NOT push jobs to nodes. It submits jobs into the
store in SUBMITTED state, optionally with a preferred node_id hint.
Workers pull jobs via claim_job(). The distributor tracks assignment
outcomes for observability.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import logging
from typing import Any

from umh.jobs.lifecycle import transition
from umh.jobs.models import ExecutionJob, JobStatus
from umh.jobs.store import JobStore

_log = logging.getLogger(__name__)


class Distributor:
    """Control plane: submits jobs for workers to claim.

    Does not force assignment — respects the pull model.
    """

    def __init__(self, store: JobStore) -> None:
        self._store = store
        self._submitted: list[str] = []
        self._assigned: list[str] = []

    @property
    def submitted_count(self) -> int:
        return len(self._submitted)

    @property
    def assigned_count(self) -> int:
        return len(self._assigned)

    def submit_job(
        self,
        task_id: str,
        *,
        preferred_node_id: str = "",
        command: list[str] | None = None,
        timeout_seconds: int = 60,
        max_attempts: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionJob:
        """Create and submit a job to the store for workers to claim.

        If preferred_node_id is set, it's stored in metadata as a hint
        but does NOT restrict which worker can claim the job.
        """
        meta = metadata or {}
        if preferred_node_id:
            meta["preferred_node_id"] = preferred_node_id

        job = self._store.create_job(
            task_id=task_id,
            node_id=preferred_node_id or "",
            command=command,
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
            metadata=meta,
        )
        transition(job, JobStatus.SUBMITTED, reason="submitted by distributor")
        self._store.update_job(job)
        self._submitted.append(job.job_id)
        _log.info("Distributor submitted job %s (task=%s)", job.job_id, task_id)
        return job

    def get_assignment_status(self, job_id: str) -> dict[str, Any]:
        """Check current status of a submitted job."""
        job = self._store.get_job(job_id)
        if job is None:
            return {"job_id": job_id, "status": "not_found"}
        return {
            "job_id": job_id,
            "status": job.status.value,
            "node_id": job.node_id,
            "assigned": job.status != JobStatus.SUBMITTED,
        }

    def list_pending(self) -> list[ExecutionJob]:
        """List jobs waiting to be claimed."""
        return self._store.list_jobs(status=JobStatus.SUBMITTED)

    def list_running(self) -> list[ExecutionJob]:
        """List jobs currently being executed."""
        return self._store.list_jobs(status=JobStatus.RUNNING)
