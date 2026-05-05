"""Job models — lifecycle-tracked distributed execution units.

An ExecutionJob tracks a unit of work from creation through submission,
execution, and completion (or failure/timeout/orphan). JobResult
captures the output of a completed job.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any

from umh.core.clock import iso_now as _iso_now


def _gen_job_id() -> str:
    import uuid

    return f"job_{uuid.uuid4().hex[:12]}"


@unique
class JobStatus(str, Enum):
    CREATED = "created"
    SUBMITTED = "submitted"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    ORPHANED = "orphaned"


@dataclass
class ExecutionJob:
    """Lifecycle-tracked execution unit."""

    job_id: str
    task_id: str
    node_id: str
    status: JobStatus = JobStatus.CREATED
    command: list[str] | None = None
    created_at: str = ""
    submitted_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    last_poll_at: str = ""
    timeout_seconds: int = 60
    attempts: int = 0
    max_attempts: int = 1
    result: dict[str, Any] | None = None
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = _iso_now()
        if self.command is not None and not isinstance(self.command, list):
            raise TypeError("command must be a list of strings")

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "task_id": self.task_id,
            "node_id": self.node_id,
            "status": self.status.value,
            "command": self.command,
            "created_at": self.created_at,
            "submitted_at": self.submitted_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "last_poll_at": self.last_poll_at,
            "timeout_seconds": self.timeout_seconds,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class JobResult:
    """Output of a completed job."""

    job_id: str
    status: JobStatus
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    duration_ms: int | None = None
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "metadata": self.metadata,
        }
