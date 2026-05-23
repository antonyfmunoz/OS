"""
Task pipeline data model — ordered multi-step execution for tasks.

Decomposes tasks into linear pipelines of typed steps, each bound to an
agent role.  Pipelines persist through the same dual-layer storage used by
TaskStore (in-memory + substrate.storage) and survive process restarts.

Design rules (mirror substrate conventions):
- Additive only — never imported on the hot path.
- Best-effort persistence — flush failures log, never raise.
- Thread-safe singleton store.
- Bounded — oldest completed pipelines pruned first.
- Deterministic enums — no LLM calls for state management.
"""

from __future__ import annotations

import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


# ─── Constants ────────────────────────────────────────────────────────────────

_STORAGE_KEY = "task_pipelines"
_MAX_PIPELINES = 500

_MAX_STEP_RETRIES = 2


def _log(msg: str) -> None:
    print(f"[substrate.task_pipeline] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_pipeline_id() -> str:
    return f"pipe_{uuid.uuid4().hex[:12]}"


def _new_step_id() -> str:
    return f"step_{uuid.uuid4().hex[:12]}"


# ─── Enums ────────────────────────────────────────────────────────────────────


class PipelineStatus(str, Enum):
    """Lifecycle state of a task pipeline."""

    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    WAITING_ON_OPERATOR = "waiting_on_operator"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"


class StepStatus(str, Enum):
    """Lifecycle state of a single pipeline step."""

    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    WAITING_ON_OPERATOR = "waiting_on_operator"
    FAILED = "failed"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class PipelineAgentRole(str, Enum):
    """Lightweight routing tag for pipeline steps.

    Distinct from substrate.roles.AgentRole which is a rich dataclass
    with scopes and handoff targets for live orchestration. This enum
    is metadata for deterministic routing within pipelines.
    """

    PRODUCT = "product"
    BUILDER = "builder"
    CEO = "ceo"
    PORTFOLIO = "portfolio"
    GENERAL = "general"


# ─── PipelineStep ─────────────────────────────────────────────────────────────


@dataclass
class PipelineStep:
    """A single executable step within a TaskPipeline."""

    step_id: str
    title: str
    description: Optional[str]
    agent_role: PipelineAgentRole
    target_hint: Optional[str]
    status: StepStatus
    step_index: int

    execution_started_at: Optional[str] = None
    execution_finished_at: Optional[str] = None
    execution_result: Optional[str] = None
    execution_error: Optional[str] = None
    retry_count: int = 0

    requires_input_prompt: Optional[str] = None
    chosen_target: Optional[str] = None
    routing_reason: Optional[str] = None

    updated_at: str = ""

    # — factory ──────────────────────────────────────────────────────────────

    @classmethod
    def new(
        cls,
        title: str,
        step_index: int,
        agent_role: PipelineAgentRole,
        *,
        description: Optional[str] = None,
        target_hint: Optional[str] = None,
        status: StepStatus = StepStatus.PENDING,
    ) -> "PipelineStep":
        """Create a new PipelineStep with generated ID and current timestamp."""
        return cls(
            step_id=_new_step_id(),
            title=title,
            description=description,
            agent_role=agent_role,
            target_hint=target_hint,
            status=status,
            step_index=step_index,
            updated_at=_utcnow(),
        )

    # — serialization ────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Return a JSON-safe dict."""
        return {
            "step_id": self.step_id,
            "title": self.title,
            "description": self.description,
            "agent_role": self.agent_role.value,
            "target_hint": self.target_hint,
            "status": self.status.value,
            "step_index": self.step_index,
            "execution_started_at": self.execution_started_at,
            "execution_finished_at": self.execution_finished_at,
            "execution_result": self.execution_result,
            "execution_error": self.execution_error,
            "retry_count": self.retry_count,
            "requires_input_prompt": self.requires_input_prompt,
            "chosen_target": self.chosen_target,
            "routing_reason": self.routing_reason,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PipelineStep":
        """Deserialize from a dict with safe defaults."""
        try:
            role = PipelineAgentRole(d.get("agent_role", "general"))
        except ValueError:
            role = PipelineAgentRole.GENERAL

        try:
            status = StepStatus(d.get("status", "pending"))
        except ValueError:
            status = StepStatus.PENDING

        return cls(
            step_id=str(d.get("step_id") or _new_step_id()),
            title=str(d.get("title", "")),
            description=d.get("description"),
            agent_role=role,
            target_hint=d.get("target_hint"),
            status=status,
            step_index=int(d.get("step_index", 0)),
            execution_started_at=d.get("execution_started_at"),
            execution_finished_at=d.get("execution_finished_at"),
            execution_result=d.get("execution_result"),
            execution_error=d.get("execution_error"),
            retry_count=int(d.get("retry_count", 0)),
            requires_input_prompt=d.get("requires_input_prompt"),
            chosen_target=d.get("chosen_target"),
            routing_reason=d.get("routing_reason"),
            updated_at=str(d.get("updated_at") or _utcnow()),
        )


# ─── TaskPipeline ─────────────────────────────────────────────────────────────


@dataclass
class TaskPipeline:
    """An ordered sequence of steps that execute a task."""

    pipeline_id: str
    task_id: str
    title: str
    status: PipelineStatus

    created_at: str
    updated_at: str

    current_step_index: int
    agent_owner: PipelineAgentRole

    day_session_id: Optional[str] = None
    queue_name: Optional[str] = None
    priority: int = 50

    steps: list[PipelineStep] = field(default_factory=list)
    summary: Optional[str] = None

    # — factory ──────────────────────────────────────────────────────────────

    @classmethod
    def new(
        cls,
        task_id: str,
        title: str,
        agent_owner: PipelineAgentRole,
        steps: list[PipelineStep],
        *,
        day_session_id: Optional[str] = None,
        queue_name: Optional[str] = None,
        priority: int = 50,
    ) -> "TaskPipeline":
        """Create a new TaskPipeline with generated ID and current timestamps."""
        now = _utcnow()
        return cls(
            pipeline_id=_new_pipeline_id(),
            task_id=task_id,
            title=title,
            status=PipelineStatus.READY,
            created_at=now,
            updated_at=now,
            current_step_index=0,
            agent_owner=agent_owner,
            day_session_id=day_session_id,
            queue_name=queue_name,
            priority=priority,
            steps=list(steps),
        )

    # — helpers ──────────────────────────────────────────────────────────────

    def current_step(self) -> Optional[PipelineStep]:
        """Return the step at current_step_index, or None if out of bounds."""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def completed_steps(self) -> list[PipelineStep]:
        """Return all steps with COMPLETED status."""
        return [s for s in self.steps if s.status == StepStatus.COMPLETED]

    def failed_steps(self) -> list[PipelineStep]:
        """Return all steps with FAILED status."""
        return [s for s in self.steps if s.status == StepStatus.FAILED]

    def is_terminal(self) -> bool:
        """True if pipeline is in a terminal state (COMPLETED, FAILED)."""
        return self.status in (PipelineStatus.COMPLETED, PipelineStatus.FAILED)

    # — serialization ────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Return a JSON-safe dict."""
        return {
            "pipeline_id": self.pipeline_id,
            "task_id": self.task_id,
            "title": self.title,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "current_step_index": self.current_step_index,
            "agent_owner": self.agent_owner.value,
            "day_session_id": self.day_session_id,
            "queue_name": self.queue_name,
            "priority": self.priority,
            "steps": [s.to_dict() for s in self.steps],
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TaskPipeline":
        """Deserialize from a dict with safe defaults."""
        try:
            status = PipelineStatus(d.get("status", "pending"))
        except ValueError:
            status = PipelineStatus.PENDING

        try:
            agent_owner = PipelineAgentRole(d.get("agent_owner", "general"))
        except ValueError:
            agent_owner = PipelineAgentRole.GENERAL

        raw_steps = d.get("steps", [])
        steps: list[PipelineStep] = []
        for raw in raw_steps:
            if isinstance(raw, dict):
                try:
                    steps.append(PipelineStep.from_dict(raw))
                except Exception:  # noqa: BLE001
                    pass

        return cls(
            pipeline_id=str(d.get("pipeline_id") or _new_pipeline_id()),
            task_id=str(d.get("task_id", "")),
            title=str(d.get("title", "")),
            status=status,
            created_at=str(d.get("created_at") or _utcnow()),
            updated_at=str(d.get("updated_at") or _utcnow()),
            current_step_index=int(d.get("current_step_index", 0)),
            agent_owner=agent_owner,
            day_session_id=d.get("day_session_id"),
            queue_name=d.get("queue_name"),
            priority=int(d.get("priority", 50)),
            steps=steps,
            summary=d.get("summary"),
        )


# ─── Pipeline Store ───────────────────────────────────────────────────────────


class PipelineStore:
    """Durable, thread-safe, singleton store for TaskPipeline records.

    Dual-layer: in-memory dict + substrate.storage.
    Best-effort persistence — flush failures log, never raise.
    Bounded — prunes oldest completed pipelines when count exceeds limit.
    """

    def __init__(self, *, autoload: bool = True) -> None:
        self._lock = threading.RLock()
        self._pipelines: dict[str, TaskPipeline] = {}
        self._loaded = False
        if autoload:
            self._load()

    # — persistence ──────────────────────────────────────────────────────────

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            try:
                from substrate.execution.bridge.storage import get_storage

                raw = get_storage().get(_STORAGE_KEY, default=None)
            except Exception as e:  # noqa: BLE001
                _log(f"load failed ({e}); starting empty")
                raw = None
            if isinstance(raw, dict):
                for key, val in raw.items():
                    if isinstance(val, dict):
                        try:
                            self._pipelines[key] = TaskPipeline.from_dict(val)
                        except Exception as e:  # noqa: BLE001
                            _log(f"skip bad pipeline {key}: {e}")
            self._loaded = True

    def _flush(self) -> None:
        try:
            from substrate.execution.bridge.storage import get_storage

            payload = {pid: p.to_dict() for pid, p in self._pipelines.items()}
            get_storage().put(_STORAGE_KEY, payload)
        except Exception as e:  # noqa: BLE001
            _log(f"flush failed: {e}")

    def _prune_if_needed(self) -> None:
        """Remove oldest completed pipelines if store exceeds limit."""
        if len(self._pipelines) <= _MAX_PIPELINES:
            return
        completed = [
            p for p in self._pipelines.values() if p.status == PipelineStatus.COMPLETED
        ]
        completed.sort(key=lambda p: p.updated_at)
        to_remove = len(self._pipelines) - _MAX_PIPELINES
        for pipeline in completed[:to_remove]:
            del self._pipelines[pipeline.pipeline_id]

    # — public api ───────────────────────────────────────────────────────────

    def get(self, pipeline_id: str) -> Optional[TaskPipeline]:
        """Return a pipeline by ID, or None."""
        with self._lock:
            return self._pipelines.get(pipeline_id)

    def get_by_task_id(self, task_id: str) -> Optional[TaskPipeline]:
        """Return the pipeline linked to a task, or None."""
        with self._lock:
            for p in self._pipelines.values():
                if p.task_id == task_id:
                    return p
            return None

    def put(self, pipeline: TaskPipeline) -> None:
        """Insert or update a pipeline. Flushes to storage."""
        with self._lock:
            pipeline.updated_at = _utcnow()
            self._pipelines[pipeline.pipeline_id] = pipeline
            self._prune_if_needed()
            self._flush()

    def all(self) -> list[TaskPipeline]:
        """Return all pipelines, ordered by created_at ascending."""
        with self._lock:
            return sorted(self._pipelines.values(), key=lambda p: p.created_at)

    def by_status(self, status: PipelineStatus) -> list[TaskPipeline]:
        """Return pipelines with the given status."""
        with self._lock:
            return [p for p in self._pipelines.values() if p.status == status]

    def active_pipelines(self) -> list[TaskPipeline]:
        """Return pipelines in non-terminal states."""
        active = {
            PipelineStatus.READY,
            PipelineStatus.IN_PROGRESS,
            PipelineStatus.WAITING_ON_OPERATOR,
            PipelineStatus.PAUSED,
        }
        with self._lock:
            return [p for p in self._pipelines.values() if p.status in active]

    def count_by_status(self) -> dict[str, int]:
        """Return {status_value: count} summary."""
        with self._lock:
            counts: dict[str, int] = {}
            for p in self._pipelines.values():
                counts[p.status.value] = counts.get(p.status.value, 0) + 1
            return counts

    # — singleton ────────────────────────────────────────────────────────────

    _default: Optional["PipelineStore"] = None
    _default_lock = threading.Lock()

    @classmethod
    def default(cls) -> "PipelineStore":
        """Return the process-level singleton."""
        if cls._default is None:
            with cls._default_lock:
                if cls._default is None:
                    cls._default = cls()
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        """Tear down singleton for test isolation."""
        with cls._default_lock:
            cls._default = None


# ─── Exports ──────────────────────────────────────────────────────────────────

__all__ = [
    "PipelineStatus",
    "StepStatus",
    "PipelineAgentRole",
    "PipelineStep",
    "TaskPipeline",
    "PipelineStore",
    "_MAX_STEP_RETRIES",
]
