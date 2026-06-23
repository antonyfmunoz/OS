"""Task catalog — load and manage C27 self-use certification tasks.

Tasks are defined in data/umh/c27_task_catalog.json and loaded at
runtime. Each task carries its stream, domain, surfaces exercised,
and projection target. Results are recorded per-task.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from substrate.organism.self_use.task_taxonomy import (
    CoherenceDomain,
    StreamType,
    TaskDomain,
)

logger = logging.getLogger(__name__)

DEFAULT_CATALOG_PATH = os.path.join(
    os.environ.get("UMH_ROOT", "/opt/OS"),
    "data",
    "umh",
    "c27_task_catalog.json",
)


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SelfUseTask:
    """A single C27 certification task."""

    task_id: str = field(default_factory=lambda: f"c27-{uuid4().hex[:8]}")
    title: str = ""
    description: str = ""
    stream: StreamType = StreamType.PRODUCTION
    domain: TaskDomain | CoherenceDomain | str = TaskDomain.IMPLEMENTATION
    projection: str = ""
    surfaces: list[str] = field(default_factory=list)
    expected_outcome: str = ""
    status: TaskStatus = TaskStatus.PENDING
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        domain_val = self.domain.value if isinstance(self.domain, Enum) else self.domain
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "stream": self.stream.value,
            "domain": domain_val,
            "projection": self.projection,
            "surfaces": self.surfaces,
            "expected_outcome": self.expected_outcome,
            "status": self.status.value,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SelfUseTask:
        stream = StreamType(data.get("stream", "production"))
        raw_domain = data.get("domain", "implementation")
        domain: TaskDomain | CoherenceDomain | str
        try:
            domain = TaskDomain(raw_domain)
        except ValueError:
            try:
                domain = CoherenceDomain(raw_domain)
            except ValueError:
                domain = raw_domain
        return cls(
            task_id=data.get("task_id", f"c27-{uuid4().hex[:8]}"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            stream=stream,
            domain=domain,
            projection=data.get("projection", ""),
            surfaces=data.get("surfaces", []),
            expected_outcome=data.get("expected_outcome", ""),
            status=TaskStatus(data.get("status", "pending")),
            tags=data.get("tags", []),
        )


@dataclass
class TaskResult:
    """Outcome of executing a self-use task."""

    result_id: str = field(default_factory=lambda: f"cr-{uuid4().hex[:8]}")
    task_id: str = ""
    status: TaskStatus = TaskStatus.COMPLETED
    surfaces_exercised: list[str] = field(default_factory=list)
    coherence_preserved: bool = True
    gap_ids: list[str] = field(default_factory=list)
    notes: str = ""
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "task_id": self.task_id,
            "status": self.status.value,
            "surfaces_exercised": self.surfaces_exercised,
            "coherence_preserved": self.coherence_preserved,
            "gap_ids": self.gap_ids,
            "notes": self.notes,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": round(self.duration_seconds, 2),
        }


class TaskCatalog:
    """Load, query, and manage C27 tasks."""

    def __init__(self, tasks: list[SelfUseTask] | None = None) -> None:
        self._tasks: dict[str, SelfUseTask] = {}
        self._results: dict[str, TaskResult] = {}
        if tasks:
            for t in tasks:
                self._tasks[t.task_id] = t

    @classmethod
    def from_json(cls, path: str | None = None) -> TaskCatalog:
        path = path or DEFAULT_CATALOG_PATH
        if not os.path.exists(path):
            logger.warning("Task catalog not found: %s", path)
            return cls()
        with open(path) as f:
            data = json.load(f)
        tasks_raw = data.get("tasks", data) if isinstance(data, dict) else data
        tasks = [SelfUseTask.from_dict(t) for t in tasks_raw]
        logger.info("Loaded %d C27 tasks from %s", len(tasks), path)
        return cls(tasks)

    @property
    def tasks(self) -> list[SelfUseTask]:
        return list(self._tasks.values())

    def get(self, task_id: str) -> SelfUseTask | None:
        return self._tasks.get(task_id)

    def by_stream(self, stream: StreamType) -> list[SelfUseTask]:
        return [t for t in self._tasks.values() if t.stream == stream]

    def by_projection(self, projection: str) -> list[SelfUseTask]:
        return [t for t in self._tasks.values() if t.projection == projection]

    def by_status(self, status: TaskStatus) -> list[SelfUseTask]:
        return [t for t in self._tasks.values() if t.status == status]

    def pending(self) -> list[SelfUseTask]:
        return self.by_status(TaskStatus.PENDING)

    def record_result(self, result: TaskResult) -> None:
        self._results[result.task_id] = result
        task = self._tasks.get(result.task_id)
        if task:
            task.status = result.status

    def results(self) -> list[TaskResult]:
        return list(self._results.values())

    def completion_rate(self, stream: StreamType | None = None) -> float:
        tasks = self.by_stream(stream) if stream else self.tasks
        if not tasks:
            return 0.0
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        return completed / len(tasks)

    def surface_coverage(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self._results.values():
            for s in r.surfaces_exercised:
                counts[s] = counts.get(s, 0) + 1
        return counts

    def summary(self) -> dict[str, Any]:
        return {
            "total_tasks": len(self._tasks),
            "by_stream": {s.value: len(self.by_stream(s)) for s in StreamType},
            "by_status": {s.value: len(self.by_status(s)) for s in TaskStatus},
            "results_recorded": len(self._results),
            "completion_rate": round(self.completion_rate(), 4),
            "surface_coverage": self.surface_coverage(),
        }
