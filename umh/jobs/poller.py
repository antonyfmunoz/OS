"""Job poller — polls running/submitted jobs and detects timeouts/orphans.

Non-blocking. Does not call subprocess. Does not import cells/environments.
Accepts all dependencies as constructor parameters.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.jobs.lifecycle import should_retry, transition
from umh.jobs.models import ExecutionJob, JobStatus
from umh.jobs.store import JobStore

_log = logging.getLogger(__name__)


class JobPoller:
    """Polls job state and detects timeouts/orphans."""

    def poll_once(
        self,
        job_store: JobStore,
        remote_client: Any | None = None,
        nodes_by_id: dict[str, Any] | None = None,
        *,
        now: str = "",
    ) -> dict[str, Any]:
        """Poll all non-terminal jobs. Returns summary of updates."""
        ts = now or _iso_now()
        updates: dict[str, Any] = {
            "polled": 0,
            "updated": 0,
            "errors": 0,
        }

        running_jobs = job_store.list_jobs(status=JobStatus.RUNNING)
        submitted_jobs = job_store.list_jobs(status=JobStatus.SUBMITTED)
        all_active = running_jobs + submitted_jobs

        for job in all_active:
            updates["polled"] += 1
            job.last_poll_at = ts

            if remote_client is not None and nodes_by_id is not None:
                node = nodes_by_id.get(job.node_id)
                if node is not None:
                    try:
                        record = remote_client.fetch_result(node, job.task_id)
                        if record is not None:
                            self._apply_remote_result(job_store, job, record)
                            updates["updated"] += 1
                    except Exception as e:
                        _log.debug("Poll error for job %s: %s", job.job_id, e)
                        updates["errors"] += 1

        return updates

    def detect_timeouts(
        self,
        job_store: JobStore,
        *,
        now: datetime | None = None,
    ) -> list[str]:
        """Mark timed-out jobs. Returns list of timed-out job IDs."""
        ref = now or datetime.now(timezone.utc)
        timed_out: list[str] = []

        running = job_store.list_jobs(status=JobStatus.RUNNING)
        submitted = job_store.list_jobs(status=JobStatus.SUBMITTED)

        for job in running + submitted:
            start = job.started_at or job.submitted_at or job.created_at
            if not start:
                continue
            try:
                start_dt = datetime.fromisoformat(start)
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                elapsed = (ref - start_dt).total_seconds()
                if elapsed > job.timeout_seconds:
                    try:
                        if job.status == JobStatus.RUNNING:
                            job_store.mark_timeout(job.job_id, f"timeout after {elapsed:.0f}s")
                        else:
                            job_store.mark_failed(
                                job.job_id, f"timeout waiting to run after {elapsed:.0f}s"
                            )
                        timed_out.append(job.job_id)
                    except ValueError:
                        pass
            except (ValueError, TypeError):
                continue

        return timed_out

    def detect_orphans(
        self,
        job_store: JobStore,
        health_by_node: dict[str, Any] | None = None,
        *,
        now: str = "",
    ) -> list[str]:
        """Mark orphaned jobs whose nodes are OFFLINE. Returns orphaned job IDs."""
        if health_by_node is None:
            return []

        orphaned: list[str] = []
        running = job_store.list_jobs(status=JobStatus.RUNNING)

        for job in running:
            health = health_by_node.get(job.node_id)
            if health is not None and hasattr(health, "state"):
                if health.state.value == "offline":
                    try:
                        job_store.mark_orphaned(job.job_id, f"node {job.node_id} offline")
                        orphaned.append(job.job_id)
                    except ValueError:
                        pass

        return orphaned

    def retry_eligible(self, job_store: JobStore) -> list[ExecutionJob]:
        """List jobs eligible for retry."""
        eligible: list[ExecutionJob] = []
        for status in (JobStatus.FAILED, JobStatus.TIMEOUT, JobStatus.ORPHANED):
            for job in job_store.list_jobs(status=status):
                if should_retry(job):
                    eligible.append(job)
        return eligible

    def retry_job(self, job_store: JobStore, job_id: str) -> ExecutionJob | None:
        """Retry a failed/timed-out/orphaned job by transitioning to SUBMITTED."""
        job = job_store.get_job(job_id)
        if job is None:
            return None
        if not should_retry(job):
            return None
        try:
            transition(job, JobStatus.SUBMITTED)
            job_store.update_job(job)
            return job
        except ValueError:
            return None

    def _apply_remote_result(self, job_store: JobStore, job: ExecutionJob, record: Any) -> None:
        """Apply a RemoteExecutionRecord to a job."""
        status_str = getattr(record, "status", None)
        if status_str is None:
            return
        status_val = status_str.value if hasattr(status_str, "value") else str(status_str)

        if status_val == "succeeded":
            try:
                result = getattr(record, "result", None) or {}
                job_store.mark_succeeded(job.job_id, result)
            except ValueError:
                pass
        elif status_val in ("failed", "unreachable"):
            try:
                error = getattr(record, "error", "") or ""
                job_store.mark_failed(job.job_id, error)
            except ValueError:
                pass
