"""Mission — bridge between user conversation and organism execution.

The AI persona (instance-configured name) is the single human-facing
intelligence. Internally, it decomposes user intent into missions, which
become objectives in the organism coordinator. Results flow back through
this module to become user-facing answers.

Flow:
  user message → AI persona → mission_from_user_intent() → Objective
  Objective → coordinator.execute_objective() → MissionResult
  MissionResult → synthesize_mission_result() → AI response

This module is intentionally thin. It translates between the conversational
layer and the execution substrate. Business logic lives in the coordinator;
intelligence lives in the model router; this module is the seam.

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
    WorkUnitType,
)

logger = logging.getLogger(__name__)


class MissionStatus(str, Enum):
    PENDING = "pending"
    DECOMPOSING = "decomposing"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


_OBJECTIVE_TO_MISSION: dict[str, MissionStatus] = {
    ObjectiveStatus.DECOMPOSING.value: MissionStatus.DECOMPOSING,
    ObjectiveStatus.EXECUTING.value: MissionStatus.EXECUTING,
    ObjectiveStatus.COMPLETED.value: MissionStatus.COMPLETED,
    ObjectiveStatus.FAILED.value: MissionStatus.FAILED,
    ObjectiveStatus.PARTIAL.value: MissionStatus.PARTIAL,
}


@dataclass
class MissionResult:
    """The organism's answer to a mission."""

    mission_id: str
    status: MissionStatus
    summary: str = ""
    outputs: list[str] = field(default_factory=list)
    objective_id: str = ""
    completion_rate: float = 0.0
    duration_ms: int = 0
    runtimes_used: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "status": self.status.value,
            "summary": self.summary,
            "outputs": self.outputs,
            "objective_id": self.objective_id,
            "completion_rate": round(self.completion_rate, 3),
            "duration_ms": self.duration_ms,
            "runtimes_used": self.runtimes_used,
        }


@dataclass
class Mission:
    """A mission from the user to the organism."""

    id: str = ""
    user_intent: str = ""
    title: str = ""
    description: str = ""
    work_units: list[dict[str, Any]] = field(default_factory=list)
    status: MissionStatus = MissionStatus.PENDING
    objective_id: str = ""
    created_at: float = 0.0
    completed_at: float = 0.0
    result: MissionResult | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"mission-{uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_intent": self.user_intent[:200],
            "title": self.title,
            "status": self.status.value,
            "objective_id": self.objective_id,
            "work_units": len(self.work_units),
            "result": self.result.to_dict() if self.result else None,
        }


_INTENT_KEYWORDS: dict[str, WorkUnitType] = {
    "research": WorkUnitType.RESEARCH,
    "investigate": WorkUnitType.RESEARCH,
    "analyze": WorkUnitType.RESEARCH,
    "find": WorkUnitType.RESEARCH,
    "audit": WorkUnitType.RESEARCH,
    "build": WorkUnitType.BUILD,
    "create": WorkUnitType.BUILD,
    "implement": WorkUnitType.BUILD,
    "write": WorkUnitType.BUILD,
    "fix": WorkUnitType.BUILD,
    "review": WorkUnitType.REVIEW,
    "check": WorkUnitType.REVIEW,
    "verify": WorkUnitType.REVIEW,
    "run": WorkUnitType.EXECUTE,
    "deploy": WorkUnitType.EXECUTE,
    "execute": WorkUnitType.EXECUTE,
}


def mission_from_user_intent(
    user_intent: str,
    title: str = "",
    work_units: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Mission:
    """Convert a user's intent string into a Mission.

    If work_units are provided, use them directly (caller has already
    decomposed). Otherwise, create a single work unit from the intent —
    the coordinator handles further decomposition if needed.
    """
    if not title:
        title = user_intent.split("\n")[0][:120].strip()

    mission = Mission(
        user_intent=user_intent,
        title=title,
        description=user_intent,
        work_units=work_units or [],
        metadata=metadata or {},
    )

    if not mission.work_units:
        unit_type = WorkUnitType.EXECUTE
        words = user_intent.lower().split()
        for word in words[:5]:
            if word in _INTENT_KEYWORDS:
                unit_type = _INTENT_KEYWORDS[word]
                break

        mission.work_units = [
            {
                "title": title,
                "description": user_intent,
                "type": unit_type.value,
            }
        ]

    return mission


def execute_mission(
    mission: Mission,
    coordinator: OrganismCoordinator,
) -> MissionResult:
    """Execute a Mission through the organism coordinator.

    Returns a MissionResult with synthesized outputs.
    """
    mission.status = MissionStatus.EXECUTING
    start = time.monotonic_ns()

    result = coordinator.execute_objective(
        title=mission.title,
        description=mission.description,
        work_units=mission.work_units if mission.work_units else None,
    )

    elapsed_ms = (time.monotonic_ns() - start) // 1_000_000

    mission.objective_id = result.get("objective_id", "")
    obj_status = result.get("status", "failed")
    mission.status = _OBJECTIVE_TO_MISSION.get(obj_status, MissionStatus.FAILED)
    mission.completed_at = time.time()

    mission_result = synthesize_mission_result(mission, result, elapsed_ms)
    mission.result = mission_result

    logger.info(
        "mission %s completed: status=%s rate=%.1f%% in %dms",
        mission.id,
        mission_result.status.value,
        mission_result.completion_rate * 100,
        elapsed_ms,
    )

    return mission_result


def synthesize_mission_result(
    mission: Mission,
    coordinator_result: dict[str, Any],
    duration_ms: int = 0,
) -> MissionResult:
    """Convert coordinator execution results into a user-facing MissionResult."""
    runtimes_used: list[str] = []

    for wu_result in coordinator_result.get("results", []):
        if wu_result.get("status") == "completed":
            runtime = wu_result.get("runtime", "")
            if runtime and runtime not in runtimes_used:
                runtimes_used.append(runtime)

    obj_status = coordinator_result.get("status", "failed")
    status = _OBJECTIVE_TO_MISSION.get(obj_status, MissionStatus.FAILED)
    completion_rate = coordinator_result.get("completion_rate", 0.0)

    total_units = coordinator_result.get("work_units", 0)
    completed_units = sum(
        1 for r in coordinator_result.get("results", []) if r.get("status") == "completed"
    )

    if status == MissionStatus.COMPLETED:
        summary = f"Completed {completed_units}/{total_units} work units"
    elif status == MissionStatus.PARTIAL:
        summary = f"Partially completed: {completed_units}/{total_units} work units succeeded"
    else:
        summary = f"Failed: {completed_units}/{total_units} work units completed"

    return MissionResult(
        mission_id=mission.id,
        status=status,
        summary=summary,
        outputs=[],
        objective_id=mission.objective_id,
        completion_rate=completion_rate,
        duration_ms=duration_ms,
        runtimes_used=runtimes_used,
    )
