"""OrganismCoordinator — hierarchical task decomposition and runtime assignment.

The coordinator is the organism's brain for turning high-level objectives
into executable work. It decomposes objectives into dependency-ordered
work units, assigns each to the best available runtime, manages parallel
execution, and aggregates results.

This is what the AI persona delegates to internally. The user sees one
intelligence; the coordinator sees a graph of runtimes and a DAG of work units.

Patterns absorbed from cortextOS:
  - Lifecycle generation counter (prevents restart race conditions)
  - Pre-fire attempt timestamp (crash-safe idempotent execution)
  - DAG dependency tracking with blocked_by/blocks

UMH substrate subsystem.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from substrate.organism.runtime_graph import (
    RuntimeCapability,
    RuntimeClass,
    RuntimeGraph,
    RuntimeResult,
)

logger = logging.getLogger(__name__)


class WorkUnitStatus(str, Enum):
    PENDING = "pending"
    BLOCKED = "blocked"
    CLAIMED = "claimed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ObjectiveStatus(str, Enum):
    DECOMPOSING = "decomposing"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class WorkUnitType(str, Enum):
    RESEARCH = "research"
    BUILD = "build"
    REVIEW = "review"
    EXECUTE = "execute"
    COORDINATE = "coordinate"


_TYPE_TO_CAPABILITY: dict[WorkUnitType, RuntimeCapability] = {
    WorkUnitType.RESEARCH: RuntimeCapability.RESEARCH,
    WorkUnitType.BUILD: RuntimeCapability.CODE_WRITE,
    WorkUnitType.REVIEW: RuntimeCapability.CODE_REVIEW,
    WorkUnitType.EXECUTE: RuntimeCapability.SHELL,
    WorkUnitType.COORDINATE: RuntimeCapability.REASON,
}


@dataclass
class WorkUnit:
    """A single unit of work in a decomposed objective."""

    id: str = ""
    objective_id: str = ""
    title: str = ""
    description: str = ""
    unit_type: WorkUnitType = WorkUnitType.EXECUTE
    status: WorkUnitStatus = WorkUnitStatus.PENDING
    assigned_runtime: str = ""
    required_capability: RuntimeCapability | None = None
    blocked_by: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    result: str = ""
    error: str = ""
    attempt_count: int = 0
    max_attempts: int = 3
    created_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    generation: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"wu-{uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()
        if self.required_capability is None:
            self.required_capability = _TYPE_TO_CAPABILITY.get(
                self.unit_type,
                RuntimeCapability.REASON,
            )

    @property
    def is_ready(self) -> bool:
        return self.status == WorkUnitStatus.PENDING and not self.blocked_by

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            WorkUnitStatus.COMPLETED,
            WorkUnitStatus.FAILED,
            WorkUnitStatus.CANCELLED,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "objective_id": self.objective_id,
            "title": self.title,
            "unit_type": self.unit_type.value,
            "status": self.status.value,
            "assigned_runtime": self.assigned_runtime,
            "required_capability": self.required_capability.value
            if self.required_capability
            else "",
            "blocked_by": self.blocked_by,
            "blocks": self.blocks,
            "attempt_count": self.attempt_count,
            "generation": self.generation,
            "result": self.result[:200] if self.result else "",
            "error": self.error[:200] if self.error else "",
        }


@dataclass
class Objective:
    """A high-level objective decomposed into work units."""

    id: str = ""
    title: str = ""
    description: str = ""
    status: ObjectiveStatus = ObjectiveStatus.DECOMPOSING
    work_units: list[WorkUnit] = field(default_factory=list)
    created_at: float = 0.0
    completed_at: float = 0.0
    generation: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"obj-{uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    @property
    def completion_rate(self) -> float:
        if not self.work_units:
            return 0.0
        completed = sum(1 for wu in self.work_units if wu.status == WorkUnitStatus.COMPLETED)
        return completed / len(self.work_units)

    @property
    def is_complete(self) -> bool:
        return all(wu.is_terminal for wu in self.work_units)

    @property
    def has_failures(self) -> bool:
        return any(wu.status == WorkUnitStatus.FAILED for wu in self.work_units)

    def ready_units(self) -> list[WorkUnit]:
        return [wu for wu in self.work_units if wu.is_ready]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status.value,
            "completion_rate": round(self.completion_rate, 3),
            "work_units": [wu.to_dict() for wu in self.work_units],
            "generation": self.generation,
        }


_KEYWORD_TYPE_MAP: dict[str, WorkUnitType] = {
    "research": WorkUnitType.RESEARCH,
    "investigate": WorkUnitType.RESEARCH,
    "analyze": WorkUnitType.RESEARCH,
    "find": WorkUnitType.RESEARCH,
    "audit": WorkUnitType.RESEARCH,
    "build": WorkUnitType.BUILD,
    "create": WorkUnitType.BUILD,
    "implement": WorkUnitType.BUILD,
    "write": WorkUnitType.BUILD,
    "add": WorkUnitType.BUILD,
    "fix": WorkUnitType.BUILD,
    "review": WorkUnitType.REVIEW,
    "check": WorkUnitType.REVIEW,
    "verify": WorkUnitType.REVIEW,
    "test": WorkUnitType.REVIEW,
    "run": WorkUnitType.EXECUTE,
    "deploy": WorkUnitType.EXECUTE,
    "execute": WorkUnitType.EXECUTE,
    "start": WorkUnitType.EXECUTE,
}


def _infer_unit_type(text: str) -> WorkUnitType:
    words = text.lower().split()
    for word in words[:5]:
        if word in _KEYWORD_TYPE_MAP:
            return _KEYWORD_TYPE_MAP[word]
    return WorkUnitType.EXECUTE


class OrganismCoordinator:
    """Hierarchical orchestrator for the UMH organism.

    Responsibilities:
      1. Decompose objectives into dependency-ordered work units
      2. Assign each work unit to the best available runtime
      3. Execute work units (respecting dependency ordering)
      4. Handle failures with retry and fallback
      5. Aggregate results back to the objective level
      6. Persist state for crash recovery
    """

    def __init__(
        self,
        graph: RuntimeGraph,
        state_dir: str | Path = "data/umh/coordinator",
    ) -> None:
        self._graph = graph
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._objectives: dict[str, Objective] = {}
        self._generation: int = 0

    @property
    def generation(self) -> int:
        return self._generation

    def decompose(
        self,
        title: str,
        description: str,
        work_units: list[dict[str, Any]] | None = None,
    ) -> Objective:
        """Create an objective and decompose it into work units.

        If work_units is provided, use them directly. Otherwise,
        create a single work unit from the description (the caller
        is responsible for LLM-based decomposition if needed).
        """
        self._generation += 1
        obj = Objective(
            title=title,
            description=description,
            generation=self._generation,
        )

        if work_units:
            for i, wu_spec in enumerate(work_units):
                wu = WorkUnit(
                    objective_id=obj.id,
                    title=wu_spec.get("title", f"Step {i + 1}"),
                    description=wu_spec.get("description", ""),
                    unit_type=WorkUnitType(wu_spec["type"])
                    if "type" in wu_spec
                    else _infer_unit_type(wu_spec.get("title", "")),
                    blocked_by=wu_spec.get("blocked_by", []),
                    generation=self._generation,
                )
                obj.work_units.append(wu)

            self._resolve_blocks(obj)
        else:
            wu = WorkUnit(
                objective_id=obj.id,
                title=title,
                description=description,
                unit_type=_infer_unit_type(title),
                generation=self._generation,
            )
            obj.work_units.append(wu)

        obj.status = ObjectiveStatus.EXECUTING
        self._objectives[obj.id] = obj
        self._persist_objective(obj)

        logger.info(
            "objective decomposed: %s → %d work units",
            obj.id,
            len(obj.work_units),
        )
        return obj

    def _resolve_blocks(self, obj: Objective) -> None:
        """Ensure blocked_by/blocks are symmetrical."""
        id_map = {wu.id: wu for wu in obj.work_units}
        title_map = {wu.title: wu.id for wu in obj.work_units}

        for wu in obj.work_units:
            resolved_deps: list[str] = []
            for dep in wu.blocked_by:
                if dep in id_map:
                    resolved_deps.append(dep)
                elif dep in title_map:
                    resolved_deps.append(title_map[dep])
                else:
                    for idx, candidate in enumerate(obj.work_units):
                        if dep == str(idx):
                            resolved_deps.append(candidate.id)
                            break
            wu.blocked_by = resolved_deps

            for dep_id in wu.blocked_by:
                blocker = id_map.get(dep_id)
                if blocker and wu.id not in blocker.blocks:
                    blocker.blocks.append(wu.id)

        for wu in obj.work_units:
            if wu.blocked_by:
                wu.status = WorkUnitStatus.BLOCKED

    def assign_runtimes(self, objective_id: str) -> dict[str, str]:
        """Assign the best available runtime to each work unit."""
        obj = self._objectives.get(objective_id)
        if not obj:
            return {}

        assignments: dict[str, str] = {}
        for wu in obj.work_units:
            if wu.is_terminal or wu.assigned_runtime:
                continue

            cap = wu.required_capability or RuntimeCapability.REASON
            candidates = self._graph.select(cap)

            if candidates:
                wu.assigned_runtime = candidates[0].runtime_id
                assignments[wu.id] = wu.assigned_runtime
            else:
                logger.warning(
                    "no runtime for work unit %s (cap=%s)",
                    wu.id,
                    cap.value,
                )

        return assignments

    def execute_ready(self, objective_id: str) -> list[dict[str, Any]]:
        """Execute all ready (unblocked) work units for an objective."""
        obj = self._objectives.get(objective_id)
        if not obj:
            return []

        self._unblock_completed(obj)
        ready = obj.ready_units()

        if not ready:
            if obj.is_complete:
                obj.status = (
                    ObjectiveStatus.COMPLETED if not obj.has_failures else ObjectiveStatus.PARTIAL
                )
                obj.completed_at = time.time()
            return []

        results: list[dict[str, Any]] = []
        for wu in ready:
            result = self._execute_work_unit(wu)
            results.append(result)

        self._unblock_completed(obj)

        if obj.is_complete:
            obj.status = (
                ObjectiveStatus.COMPLETED if not obj.has_failures else ObjectiveStatus.PARTIAL
            )
            obj.completed_at = time.time()

        self._persist_objective(obj)
        return results

    def execute_objective(
        self,
        title: str,
        description: str,
        work_units: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Full lifecycle: decompose → assign → execute all → aggregate."""
        obj = self.decompose(title, description, work_units)
        self.assign_runtimes(obj.id)

        all_results: list[dict[str, Any]] = []
        max_rounds = len(obj.work_units) + 2

        for _ in range(max_rounds):
            round_results = self.execute_ready(obj.id)
            if not round_results:
                break
            all_results.extend(round_results)

        return {
            "objective_id": obj.id,
            "status": obj.status.value,
            "completion_rate": round(obj.completion_rate, 3),
            "work_units": len(obj.work_units),
            "results": all_results,
            "generation": obj.generation,
        }

    def _execute_work_unit(self, wu: WorkUnit) -> dict[str, Any]:
        """Execute a single work unit via the RuntimeGraph."""
        wu.status = WorkUnitStatus.RUNNING
        wu.started_at = time.time()
        wu.attempt_count += 1

        self._write_attempt_marker(wu)

        cap = wu.required_capability or RuntimeCapability.REASON
        prompt = f"{wu.title}\n\n{wu.description}" if wu.description else wu.title

        result = self._graph.route_and_execute(prompt, cap)

        if result is not None:
            wu.status = WorkUnitStatus.COMPLETED
            wu.result = result.output
            wu.completed_at = time.time()
            wu.assigned_runtime = result.runtime_id

            return {
                "work_unit_id": wu.id,
                "status": "completed",
                "runtime": result.runtime_id,
                "latency_ms": result.latency_ms,
                "output_length": len(result.output),
            }

        if wu.attempt_count < wu.max_attempts:
            wu.status = WorkUnitStatus.PENDING
            wu.error = f"attempt {wu.attempt_count} failed, retrying"
            return {
                "work_unit_id": wu.id,
                "status": "retry",
                "attempt": wu.attempt_count,
            }

        wu.status = WorkUnitStatus.FAILED
        wu.error = f"exhausted {wu.max_attempts} attempts"
        wu.completed_at = time.time()
        return {
            "work_unit_id": wu.id,
            "status": "failed",
            "error": wu.error,
        }

    def _unblock_completed(self, obj: Objective) -> None:
        """Unblock work units whose dependencies are all completed."""
        completed_ids = {wu.id for wu in obj.work_units if wu.status == WorkUnitStatus.COMPLETED}

        for wu in obj.work_units:
            if wu.status == WorkUnitStatus.BLOCKED:
                remaining = [dep for dep in wu.blocked_by if dep not in completed_ids]
                wu.blocked_by = remaining
                if not remaining:
                    wu.status = WorkUnitStatus.PENDING

    def _write_attempt_marker(self, wu: WorkUnit) -> None:
        """Write pre-fire marker for crash-safe idempotent recovery."""
        marker_path = self._state_dir / "inflight" / f"{wu.id}.json"
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        marker_path.write_text(
            json.dumps(
                {
                    "work_unit_id": wu.id,
                    "objective_id": wu.objective_id,
                    "attempt": wu.attempt_count,
                    "started_at": wu.started_at,
                    "generation": wu.generation,
                },
                indent=2,
            )
        )

    def _persist_objective(self, obj: Objective) -> None:
        """Persist objective state for crash recovery."""
        path = self._state_dir / "objectives" / f"{obj.id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj.to_dict(), indent=2, default=str))

    def get_objective(self, objective_id: str) -> Objective | None:
        return self._objectives.get(objective_id)

    def list_objectives(self) -> list[dict[str, Any]]:
        return [
            {
                "id": obj.id,
                "title": obj.title,
                "status": obj.status.value,
                "completion_rate": round(obj.completion_rate, 3),
                "work_units": len(obj.work_units),
                "generation": obj.generation,
            }
            for obj in self._objectives.values()
        ]

    def status(self) -> dict[str, Any]:
        return {
            "total_objectives": len(self._objectives),
            "generation": self._generation,
            "graph": self._graph.to_dict(),
            "objectives": self.list_objectives(),
        }
