"""Job persistence — durable file-backed storage with atomic writes.

Writes one JSON file per job. Uses write-to-temp-then-rename for
crash safety. Corrupted files are skipped with a warning, never fatal.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from umh.jobs.models import ExecutionJob, JobStatus

_log = logging.getLogger(__name__)

_DEFAULT_JOBS_DIR = "/opt/OS/.umh/jobs"


@runtime_checkable
class JobPersistenceBackend(Protocol):
    """Interface for job persistence backends."""

    def save_job(self, job: ExecutionJob) -> None: ...

    def load_job(self, job_id: str) -> ExecutionJob | None: ...

    def load_all_jobs(self) -> list[ExecutionJob]: ...

    def delete_job(self, job_id: str) -> bool: ...


class FileJobPersistenceBackend:
    """JSON file-backed persistence. One file per job, atomic writes."""

    def __init__(self, directory: str = _DEFAULT_JOBS_DIR) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)

    @property
    def directory(self) -> Path:
        return self._dir

    def save_job(self, job: ExecutionJob) -> None:
        data = job.to_dict()
        content = json.dumps(data, indent=2, default=str)
        target = self._job_path(job.job_id)

        fd, tmp_path = tempfile.mkstemp(dir=str(self._dir), suffix=".tmp", prefix=".job_")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, str(target))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def load_job(self, job_id: str) -> ExecutionJob | None:
        path = self._job_path(job_id)
        if not path.exists():
            return None
        return self._load_from_file(path)

    def load_all_jobs(self) -> list[ExecutionJob]:
        jobs: list[ExecutionJob] = []
        if not self._dir.exists():
            return jobs
        for path in sorted(self._dir.glob("*.json")):
            job = self._load_from_file(path)
            if job is not None:
                jobs.append(job)
        return jobs

    def delete_job(self, job_id: str) -> bool:
        path = self._job_path(job_id)
        try:
            path.unlink()
            return True
        except FileNotFoundError:
            return False

    def _job_path(self, job_id: str) -> Path:
        safe_id = job_id.replace("/", "_").replace("..", "_")
        return self._dir / f"{safe_id}.json"

    def _load_from_file(self, path: Path) -> ExecutionJob | None:
        try:
            content = path.read_text()
            data = json.loads(content)
            return _dict_to_job(data)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            _log.warning("Skipping corrupted job file %s: %s", path, e)
            return None
        except Exception as e:
            _log.warning("Failed to read job file %s: %s", path, e)
            return None


def _dict_to_job(data: dict[str, Any]) -> ExecutionJob:
    """Reconstruct an ExecutionJob from a dict. Bypasses __post_init__ timestamp."""
    return ExecutionJob(
        job_id=data["job_id"],
        task_id=data["task_id"],
        node_id=data["node_id"],
        status=JobStatus(data["status"]),
        command=data.get("command"),
        created_at=data.get("created_at", ""),
        submitted_at=data.get("submitted_at", ""),
        started_at=data.get("started_at", ""),
        finished_at=data.get("finished_at", ""),
        last_poll_at=data.get("last_poll_at", ""),
        timeout_seconds=data.get("timeout_seconds", 60),
        attempts=data.get("attempts", 0),
        max_attempts=data.get("max_attempts", 1),
        result=data.get("result"),
        error=data.get("error", ""),
        metadata=data.get("metadata", {}),
    )
