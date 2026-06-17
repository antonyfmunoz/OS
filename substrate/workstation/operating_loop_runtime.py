"""Operating Loop Runtime — visibility layer over existing execution systems.

Answers: "Can every active loop be visible?"

This is NOT an execution engine. Planning, assignment, execution, review,
and merge already belong to MetaIDEProjectionLoopRuntime, AgentFleetRuntime,
ComputeFabricRuntime, and GovernedWorkRuntime.

This runtime provides: loop tracking, loop lineage, loop state, loop visibility.

Campaign 4.1. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


class OperatingLoopStage(str, Enum):
    INTENT = "intent"
    PLAN = "plan"
    ASSIGN = "assign"
    EXECUTE = "execute"
    REVIEW = "review"
    APPROVE = "approve"
    LEARN = "learn"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class OperatingLoopTransition:
    from_stage: OperatingLoopStage
    to_stage: OperatingLoopStage
    timestamp: float = 0.0
    subsystem: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_stage": self.from_stage.value,
            "to_stage": self.to_stage.value,
            "timestamp": self.timestamp,
            "subsystem": self.subsystem,
            "metadata": self.metadata,
        }


@dataclass
class OperatingLoop:
    loop_id: str = ""
    intent_text: str = ""
    intent_id: str = ""
    current_stage: OperatingLoopStage = OperatingLoopStage.INTENT
    work_ids: list[str] = field(default_factory=list)
    execution_ids: list[str] = field(default_factory=list)
    approval_ids: list[str] = field(default_factory=list)
    build_request_id: str = ""
    plan_id: str = ""
    lineage: list[OperatingLoopTransition] = field(default_factory=list)
    outcome: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    created_at: float = 0.0
    completed_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.loop_id:
            self.loop_id = f"oloop-{uuid4().hex[:8]}"
        if self.created_at == 0.0:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "loop_id": self.loop_id,
            "intent_text": self.intent_text,
            "intent_id": self.intent_id,
            "current_stage": self.current_stage.value,
            "work_ids": self.work_ids,
            "execution_ids": self.execution_ids,
            "approval_ids": self.approval_ids,
            "build_request_id": self.build_request_id,
            "plan_id": self.plan_id,
            "lineage": [t.to_dict() for t in self.lineage],
            "outcome": self.outcome,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


@dataclass
class OperatingLoopSnapshot:
    active_loops: int = 0
    by_stage: dict[str, int] = field(default_factory=dict)
    completed_count: int = 0
    failed_count: int = 0
    avg_duration_seconds: float = 0.0
    recent_completions: list[dict[str, Any]] = field(default_factory=list)
    lineage_health: dict[str, Any] = field(default_factory=dict)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_loops": self.active_loops,
            "by_stage": self.by_stage,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "avg_duration_seconds": self.avg_duration_seconds,
            "recent_completions": self.recent_completions,
            "lineage_health": self.lineage_health,
            "generated_at": self.generated_at,
        }


# ── Helpers ───────────────────────────────────────────────────────────────

_TERMINAL_STAGES = {OperatingLoopStage.COMPLETE, OperatingLoopStage.FAILED}


def _safe_call(obj: Any, method: str, *args: Any, **kwargs: Any) -> Any:
    if obj is None:
        return None
    fn = getattr(obj, method, None)
    if fn is None:
        return None
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        logger.debug("OperatingLoop: %s.%s() failed: %s", type(obj).__name__, method, exc)
        return None


# ── Runtime ───────────────────────────────────────────────────────────────


class OperatingLoopRuntime:
    """Visibility layer over active execution loops.

    All tracking is in-memory. Observation queries compose existing subsystems.
    """

    def __init__(
        self,
        intent_runtime: Any | None = None,
        build_loop: Any | None = None,
        governed_work: Any | None = None,
        agent_fleet: Any | None = None,
        compute_fabric: Any | None = None,
        execution_graph: Any | None = None,
        learning_loop: Any | None = None,
        awareness: Any | None = None,
    ) -> None:
        self._intent = intent_runtime
        self._build_loop = build_loop
        self._governed = governed_work
        self._fleet = agent_fleet
        self._fabric = compute_fabric
        self._graph = execution_graph
        self._learning = learning_loop
        self._awareness = awareness
        self._loops: dict[str, OperatingLoop] = {}

    # ── Track ─────────────────────────────────────────────────────────

    def track(self, intent_text: str, intent_id: str = "") -> OperatingLoop:
        loop = OperatingLoop(
            intent_text=intent_text,
            intent_id=intent_id,
            current_stage=OperatingLoopStage.INTENT,
        )
        loop.lineage.append(OperatingLoopTransition(
            from_stage=OperatingLoopStage.INTENT,
            to_stage=OperatingLoopStage.INTENT,
            subsystem="operator",
            metadata={"action": "tracked"},
        ))
        self._loops[loop.loop_id] = loop
        return loop

    def record_transition(
        self,
        loop_id: str,
        to_stage: OperatingLoopStage,
        subsystem: str,
        metadata: dict[str, Any] | None = None,
    ) -> OperatingLoop:
        loop = self._loops.get(loop_id)
        if loop is None:
            return OperatingLoop(loop_id=loop_id, error="Loop not found")

        transition = OperatingLoopTransition(
            from_stage=loop.current_stage,
            to_stage=to_stage,
            subsystem=subsystem,
            metadata=metadata or {},
        )
        loop.lineage.append(transition)
        loop.current_stage = to_stage

        if to_stage in _TERMINAL_STAGES:
            loop.completed_at = time.time()
            if to_stage == OperatingLoopStage.FAILED:
                loop.error = (metadata or {}).get("error", "Unknown failure")

        return loop

    # ── Observe ───────────────────────────────────────────────────────

    def active_loops(self) -> list[OperatingLoop]:
        return [
            loop for loop in self._loops.values()
            if loop.current_stage not in _TERMINAL_STAGES
        ]

    def completed_loops(self, limit: int = 20) -> list[OperatingLoop]:
        completed = [
            loop for loop in self._loops.values()
            if loop.current_stage in _TERMINAL_STAGES
        ]
        completed.sort(key=lambda l: l.completed_at, reverse=True)
        return completed[:limit]

    def get(self, loop_id: str) -> OperatingLoop | None:
        return self._loops.get(loop_id)

    def trace(self, loop_id: str) -> list[OperatingLoopTransition]:
        loop = self._loops.get(loop_id)
        if loop is None:
            return []
        return list(loop.lineage)

    def snapshot(self) -> OperatingLoopSnapshot:
        active = [l for l in self._loops.values() if l.current_stage not in _TERMINAL_STAGES]
        completed = [l for l in self._loops.values() if l.current_stage == OperatingLoopStage.COMPLETE]
        failed = [l for l in self._loops.values() if l.current_stage == OperatingLoopStage.FAILED]

        by_stage: dict[str, int] = {}
        for loop in self._loops.values():
            stage = loop.current_stage.value
            by_stage[stage] = by_stage.get(stage, 0) + 1

        durations = [
            l.completed_at - l.created_at
            for l in completed
            if l.completed_at > 0 and l.created_at > 0
        ]
        avg_dur = sum(durations) / len(durations) if durations else 0.0

        recent = sorted(completed, key=lambda l: l.completed_at, reverse=True)[:5]

        lineage_health = _safe_call(self._graph, "audit_completeness")
        if not isinstance(lineage_health, dict):
            lineage_health = {}

        return OperatingLoopSnapshot(
            active_loops=len(active),
            by_stage=by_stage,
            completed_count=len(completed),
            failed_count=len(failed),
            avg_duration_seconds=round(avg_dur, 2),
            recent_completions=[l.to_dict() for l in recent],
            lineage_health=lineage_health,
            generated_at=time.time(),
        )

    # ── Correlate ─────────────────────────────────────────────────────

    def correlate_intent(self, intent_id: str) -> OperatingLoop | None:
        for loop in self._loops.values():
            if loop.intent_id == intent_id:
                return loop
        return None

    def lineage_for(self, loop_id: str) -> dict[str, Any]:
        loop = self._loops.get(loop_id)
        if loop is None:
            return {"error": "Loop not found"}
        if not loop.intent_id:
            return {"loop_id": loop_id, "lineage": [], "note": "No intent_id to trace"}

        result = _safe_call(self._graph, "trace_from_intent", loop.intent_id)
        if isinstance(result, dict):
            return result
        if isinstance(result, list):
            return {"loop_id": loop_id, "intent_id": loop.intent_id, "graph_nodes": result}
        return {"loop_id": loop_id, "intent_id": loop.intent_id, "lineage": []}
