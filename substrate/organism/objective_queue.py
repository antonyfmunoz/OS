"""Continuous objective queue — intake front door for OrganismCoordinator.

This is NOT a separate task system. It is the intake queue that feeds
into the existing OrganismCoordinator.decompose() → execute_ready()
flow. Objectives enter here, get priority-sorted and dependency-checked,
then dequeue into the coordinator for decomposition and execution.

Lifecycle state machine:
  QUEUED → EXECUTING → COMPLETED | FAILED | CANCELLED
  QUEUED → BLOCKED (waiting on dependency) → QUEUED (unblocked)
  EXECUTING → QUEUED (retry on failure, if retries remain)

Features:
  - Priority scheduling (lower number = higher priority)
  - Dependency ordering (blocked objectives wait for predecessors)
  - Retry policy with configurable max_retries
  - Event emission through EventSpine for observability

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from substrate.organism.event_spine import EventDomain, EventSpine

logger = logging.getLogger(__name__)


class ObjectiveQueueStatus(str, Enum):
    QUEUED = "queued"
    BLOCKED = "blocked"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ObjectiveRequest:
    request_id: str
    title: str
    description: str
    priority: int = 5
    status: ObjectiveQueueStatus = ObjectiveQueueStatus.QUEUED
    depends_on: list[str] = field(default_factory=list)
    max_retries: int = 0
    attempt_count: int = 0
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status.value,
            "depends_on": self.depends_on,
            "max_retries": self.max_retries,
            "attempt_count": self.attempt_count,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class ObjectiveQueue:
    """Intake queue for organism objectives.

    Priority-ordered, dependency-aware. Feeds into
    OrganismCoordinator for decomposition and execution.
    """

    def __init__(self, spine: EventSpine) -> None:
        self._spine = spine
        self._items: dict[str, ObjectiveRequest] = {}

    def enqueue(
        self,
        title: str,
        description: str,
        priority: int = 5,
        depends_on: list[str] | None = None,
        max_retries: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        request_id = f"oq-{uuid4().hex[:8]}"
        item = ObjectiveRequest(
            request_id=request_id,
            title=title,
            description=description,
            priority=priority,
            depends_on=depends_on or [],
            max_retries=max_retries,
            metadata=metadata or {},
        )
        self._items[request_id] = item

        self._spine.emit(
            EventDomain.OBJECTIVE, "objective_enqueued", "objective_queue",
            {"request_id": request_id, "title": title, "priority": priority},
            correlation_id=request_id,
        )

        return request_id

    def peek(self) -> ObjectiveRequest | None:
        candidates = self._ready_candidates()
        return candidates[0] if candidates else None

    def dequeue(self) -> ObjectiveRequest | None:
        candidates = self._ready_candidates()
        if not candidates:
            return None

        item = candidates[0]
        item.status = ObjectiveQueueStatus.EXECUTING
        item.started_at = time.time()
        item.attempt_count += 1

        self._spine.emit(
            EventDomain.OBJECTIVE, "objective_dequeued", "objective_queue",
            {"request_id": item.request_id, "title": item.title,
             "attempt": item.attempt_count},
            correlation_id=item.request_id,
        )

        return item

    def complete(
        self,
        request_id: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        item = self._items.get(request_id)
        if item is None:
            return

        item.status = ObjectiveQueueStatus.COMPLETED
        item.result = result
        item.completed_at = time.time()

        self._spine.emit(
            EventDomain.OBJECTIVE, "objective_completed", "objective_queue",
            {"request_id": request_id, "title": item.title},
            correlation_id=request_id,
        )

    def fail(self, request_id: str, error: str = "") -> None:
        item = self._items.get(request_id)
        if item is None:
            return

        item.error = error

        if item.attempt_count < item.max_retries:
            item.status = ObjectiveQueueStatus.QUEUED
            item.started_at = None
            self._spine.emit(
                EventDomain.OBJECTIVE, "objective_retrying", "objective_queue",
                {"request_id": request_id, "attempt": item.attempt_count,
                 "max_retries": item.max_retries, "error": error[:200]},
                correlation_id=request_id,
            )
        else:
            item.status = ObjectiveQueueStatus.FAILED
            item.completed_at = time.time()
            self._spine.emit(
                EventDomain.OBJECTIVE, "objective_failed", "objective_queue",
                {"request_id": request_id, "title": item.title,
                 "attempts": item.attempt_count, "error": error[:200]},
                correlation_id=request_id,
            )

    def cancel(self, request_id: str) -> None:
        item = self._items.get(request_id)
        if item is None:
            return
        item.status = ObjectiveQueueStatus.CANCELLED
        item.completed_at = time.time()

        self._spine.emit(
            EventDomain.OBJECTIVE, "objective_cancelled", "objective_queue",
            {"request_id": request_id, "title": item.title},
            correlation_id=request_id,
        )

    def get(self, request_id: str) -> ObjectiveRequest | None:
        return self._items.get(request_id)

    def depth(self) -> int:
        return sum(
            1 for item in self._items.values()
            if item.status in {ObjectiveQueueStatus.QUEUED, ObjectiveQueueStatus.BLOCKED}
        )

    def list_by_status(self, status: ObjectiveQueueStatus) -> list[ObjectiveRequest]:
        return [item for item in self._items.values() if item.status == status]

    def _ready_candidates(self) -> list[ObjectiveRequest]:
        candidates = []
        for item in self._items.values():
            if item.status != ObjectiveQueueStatus.QUEUED:
                continue
            if self._is_blocked(item):
                continue
            candidates.append(item)

        candidates.sort(key=lambda x: (x.priority, x.created_at))
        return candidates

    def _is_blocked(self, item: ObjectiveRequest) -> bool:
        for dep_id in item.depends_on:
            dep = self._items.get(dep_id)
            if dep is None:
                continue
            if dep.status != ObjectiveQueueStatus.COMPLETED:
                return True
        return False
