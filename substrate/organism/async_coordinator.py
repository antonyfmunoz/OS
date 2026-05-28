"""Async coordinator execution — event-driven objective lifecycle.

Wraps the synchronous OrganismCoordinator with:
  - Async submit (non-blocking objective intake)
  - Progress tracking
  - Event-driven completion via EventSpine
  - Cancellation
  - Dependency wakeups (advance unblocks downstream)

The advance() method is called from the autonomous tick engine,
progressing all active objectives one step.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from substrate.organism.coordinator import (
    ObjectiveStatus,
    OrganismCoordinator,
)
from substrate.organism.event_spine import EventDomain, EventSpine

logger = logging.getLogger(__name__)


class AsyncObjectiveStatus(str, Enum):
    SUBMITTED = "submitted"
    DECOMPOSED = "decomposed"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AsyncObjective:
    objective_id: str
    title: str
    description: str
    status: AsyncObjectiveStatus = AsyncObjectiveStatus.SUBMITTED
    coordinator_objective_id: str | None = None
    work_units_spec: list[dict[str, Any]] | None = None
    submitted_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "coordinator_objective_id": self.coordinator_objective_id,
            "submitted_at": self.submitted_at,
            "completed_at": self.completed_at,
        }


class AsyncCoordinator:
    """Async wrapper around OrganismCoordinator.

    Objectives are submitted and tracked independently.
    advance() is called each tick to progress them.
    """

    def __init__(
        self,
        coordinator: OrganismCoordinator,
        spine: EventSpine,
    ) -> None:
        self._coordinator = coordinator
        self._spine = spine
        self._objectives: dict[str, AsyncObjective] = {}

    def submit(
        self,
        title: str,
        description: str,
        work_units: list[dict[str, Any]] | None = None,
    ) -> str:
        obj_id = f"async-{uuid4().hex[:8]}"
        obj = AsyncObjective(
            objective_id=obj_id,
            title=title,
            description=description,
            work_units_spec=work_units,
        )
        self._objectives[obj_id] = obj

        self._spine.emit(
            EventDomain.OBJECTIVE,
            "async_objective_submitted",
            "async_coordinator",
            {"objective_id": obj_id, "title": title},
            correlation_id=obj_id,
        )

        return obj_id

    def advance(self) -> list[str]:
        advanced = []
        for obj in list(self._objectives.values()):
            if obj.status == AsyncObjectiveStatus.CANCELLED:
                continue

            if obj.status == AsyncObjectiveStatus.SUBMITTED:
                self._decompose(obj)
                advanced.append(obj.objective_id)

            elif obj.status in {
                AsyncObjectiveStatus.DECOMPOSED,
                AsyncObjectiveStatus.EXECUTING,
            }:
                self._execute_step(obj)
                advanced.append(obj.objective_id)

        return advanced

    def cancel(self, objective_id: str) -> None:
        obj = self._objectives.get(objective_id)
        if obj is None:
            return
        obj.status = AsyncObjectiveStatus.CANCELLED
        obj.completed_at = time.time()

        self._spine.emit(
            EventDomain.OBJECTIVE,
            "async_objective_cancelled",
            "async_coordinator",
            {"objective_id": objective_id},
            correlation_id=objective_id,
        )

    def get(self, objective_id: str) -> AsyncObjective | None:
        return self._objectives.get(objective_id)

    def progress(self, objective_id: str) -> dict[str, Any] | None:
        obj = self._objectives.get(objective_id)
        if obj is None:
            return None

        result: dict[str, Any] = {
            "objective_id": objective_id,
            "status": obj.status.value,
            "completion_rate": 0.0,
        }

        if obj.coordinator_objective_id:
            coord_obj = self._coordinator.get_objective(obj.coordinator_objective_id)
            if coord_obj:
                result["completion_rate"] = coord_obj.completion_rate
                result["work_units_total"] = len(coord_obj.work_units)
                result["work_units_completed"] = sum(
                    1 for wu in coord_obj.work_units
                    if wu.status.value == "completed"
                )

        return result

    def list_active(self) -> list[AsyncObjective]:
        return [
            obj for obj in self._objectives.values()
            if obj.status in {
                AsyncObjectiveStatus.SUBMITTED,
                AsyncObjectiveStatus.DECOMPOSED,
                AsyncObjectiveStatus.EXECUTING,
            }
        ]

    def dag_state(self, objective_id: str) -> dict[str, Any] | None:
        obj = self._objectives.get(objective_id)
        if obj is None:
            return None

        if obj.coordinator_objective_id is None:
            self._decompose(obj)

        if obj.coordinator_objective_id is None:
            return None

        coord_obj = self._coordinator.get_objective(obj.coordinator_objective_id)
        if coord_obj is None:
            return None

        return {
            "objective_id": objective_id,
            "coordinator_id": obj.coordinator_objective_id,
            "status": coord_obj.status.value,
            "completion_rate": coord_obj.completion_rate,
            "work_units": [wu.to_dict() for wu in coord_obj.work_units],
        }

    def _decompose(self, obj: AsyncObjective) -> None:
        try:
            coord_obj = self._coordinator.decompose(
                obj.title, obj.description, obj.work_units_spec,
            )
            obj.coordinator_objective_id = coord_obj.id
            obj.status = AsyncObjectiveStatus.DECOMPOSED

            self._spine.emit(
                EventDomain.OBJECTIVE,
                "async_objective_decomposed",
                "async_coordinator",
                {
                    "objective_id": obj.objective_id,
                    "coordinator_id": coord_obj.id,
                    "work_units": len(coord_obj.work_units),
                },
                correlation_id=obj.objective_id,
            )
        except Exception as exc:
            logger.warning("decompose failed for %s: %s", obj.objective_id, exc)
            obj.status = AsyncObjectiveStatus.FAILED
            obj.completed_at = time.time()

    def _execute_step(self, obj: AsyncObjective) -> None:
        if obj.coordinator_objective_id is None:
            return

        coord_obj = self._coordinator.get_objective(obj.coordinator_objective_id)
        if coord_obj is None:
            obj.status = AsyncObjectiveStatus.FAILED
            obj.completed_at = time.time()
            return

        if coord_obj.is_complete:
            obj.status = AsyncObjectiveStatus.COMPLETED
            obj.completed_at = time.time()
            self._spine.emit(
                EventDomain.OBJECTIVE,
                "async_objective_completed",
                "async_coordinator",
                {
                    "objective_id": obj.objective_id,
                    "completion_rate": coord_obj.completion_rate,
                },
                correlation_id=obj.objective_id,
            )
            return

        if coord_obj.has_failures and coord_obj.completion_rate == 0:
            obj.status = AsyncObjectiveStatus.FAILED
            obj.completed_at = time.time()
            self._spine.emit(
                EventDomain.OBJECTIVE,
                "async_objective_failed",
                "async_coordinator",
                {"objective_id": obj.objective_id},
                correlation_id=obj.objective_id,
            )
            return

        obj.status = AsyncObjectiveStatus.EXECUTING
