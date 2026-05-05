"""Job lifecycle state machine — validated status transitions.

Transition rules:
  CREATED    -> SUBMITTED
  SUBMITTED  -> RUNNING, FAILED, CANCELLED
  RUNNING    -> SUCCEEDED, FAILED, TIMEOUT, CANCELLED, ORPHANED
  FAILED     -> SUBMITTED  (retry if attempts < max_attempts)
  TIMEOUT    -> SUBMITTED  (retry if attempts < max_attempts)
  ORPHANED   -> SUBMITTED  (retry if attempts < max_attempts)

Terminal states: SUCCEEDED, CANCELLED, and FAILED/TIMEOUT/ORPHANED
when attempts >= max_attempts.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

from umh.core.clock import iso_now as _iso_now
from umh.jobs.models import ExecutionJob, JobStatus

_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.CREATED: {JobStatus.SUBMITTED},
    JobStatus.SUBMITTED: {JobStatus.RUNNING, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.RUNNING: {
        JobStatus.SUCCEEDED,
        JobStatus.FAILED,
        JobStatus.TIMEOUT,
        JobStatus.CANCELLED,
        JobStatus.ORPHANED,
    },
    JobStatus.FAILED: {JobStatus.SUBMITTED},
    JobStatus.TIMEOUT: {JobStatus.SUBMITTED},
    JobStatus.ORPHANED: {JobStatus.SUBMITTED},
    JobStatus.SUCCEEDED: set(),
    JobStatus.CANCELLED: set(),
}

_ALWAYS_TERMINAL = {JobStatus.SUCCEEDED, JobStatus.CANCELLED}
_RETRYABLE = {JobStatus.FAILED, JobStatus.TIMEOUT, JobStatus.ORPHANED}


def can_transition(from_status: JobStatus, to_status: JobStatus) -> bool:
    return to_status in _TRANSITIONS.get(from_status, set())


def is_terminal(status: JobStatus) -> bool:
    if status in _ALWAYS_TERMINAL:
        return True
    return False


def is_terminal_for_job(job: ExecutionJob) -> bool:
    if job.status in _ALWAYS_TERMINAL:
        return True
    if job.status in _RETRYABLE and job.attempts >= job.max_attempts:
        return True
    return False


def should_retry(job: ExecutionJob) -> bool:
    if job.status not in _RETRYABLE:
        return False
    return job.attempts < job.max_attempts


def transition(
    job: ExecutionJob,
    new_status: JobStatus,
    *,
    now: str = "",
    reason: str = "",
) -> ExecutionJob:
    """Transition a job to a new status. Raises ValueError on invalid transition."""
    if job.status in _RETRYABLE and new_status == JobStatus.SUBMITTED:
        if job.attempts >= job.max_attempts:
            raise ValueError(
                f"Cannot retry job {job.job_id}: "
                f"attempts ({job.attempts}) >= max_attempts ({job.max_attempts})"
            )

    if not can_transition(job.status, new_status):
        raise ValueError(
            f"Invalid transition: {job.status.value} -> {new_status.value} for job {job.job_id}"
        )

    ts = now or _iso_now()

    job.status = new_status

    if new_status == JobStatus.SUBMITTED:
        job.submitted_at = ts
        job.attempts += 1
    elif new_status == JobStatus.RUNNING:
        job.started_at = ts
    elif new_status in (
        JobStatus.SUCCEEDED,
        JobStatus.FAILED,
        JobStatus.TIMEOUT,
        JobStatus.CANCELLED,
        JobStatus.ORPHANED,
    ):
        job.finished_at = ts

    if reason:
        job.error = reason

    return job
