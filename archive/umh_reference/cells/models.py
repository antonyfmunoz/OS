"""Cell models — identity, context, lifecycle, and execution request types.

A Cell is a specialized runtime/cognitive unit that expresses substrate
context and may request work, but NEVER directly executes tools, adapters,
subprocesses, shells, containers, or external systems.

Cells propose/request. Control plane governs. Execution spine acts.
Adapters touch the world.

No imports from execution, adapters, tools, or shell.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any

from umh.brains.profile import AuthorityLevel
from umh.core.clock import iso_now as _iso_now


# ─── Enums ──────────────────────────────────────────────────────────


@unique
class CellType(str, Enum):
    INTERPRETATION = "interpretation"
    DECOMPOSITION = "decomposition"
    PLANNING = "planning"
    REVIEW = "review"
    DEBUG = "debug"
    EXECUTION_REQUESTER = "execution_requester"
    LEARNING = "learning"
    MONITOR = "monitor"
    WORKSTATION = "workstation"
    CUSTOM = "custom"


@unique
class CellStatus(str, Enum):
    CREATED = "created"
    HYDRATED = "hydrated"
    ACTIVE = "active"
    WAITING = "waiting"
    CHECKPOINTED = "checkpointed"
    TERMINATED = "terminated"
    FAILED = "failed"


_VALID_TRANSITIONS: dict[CellStatus, frozenset[CellStatus]] = {
    CellStatus.CREATED: frozenset({CellStatus.HYDRATED, CellStatus.TERMINATED, CellStatus.FAILED}),
    CellStatus.HYDRATED: frozenset({CellStatus.ACTIVE, CellStatus.TERMINATED, CellStatus.FAILED}),
    CellStatus.ACTIVE: frozenset(
        {CellStatus.WAITING, CellStatus.CHECKPOINTED, CellStatus.TERMINATED, CellStatus.FAILED}
    ),
    CellStatus.WAITING: frozenset({CellStatus.ACTIVE, CellStatus.TERMINATED, CellStatus.FAILED}),
    CellStatus.CHECKPOINTED: frozenset(
        {CellStatus.HYDRATED, CellStatus.TERMINATED, CellStatus.FAILED}
    ),
    CellStatus.TERMINATED: frozenset(),
    CellStatus.FAILED: frozenset(),
}


class InvalidTransitionError(Exception):
    """Raised when a cell status transition is not allowed."""

    def __init__(self, cell_id: str, current: CellStatus, target: CellStatus):
        self.cell_id = cell_id
        self.current = current
        self.target = target
        super().__init__(f"Cell '{cell_id}': cannot transition {current.value} → {target.value}")


def validate_transition(cell_id: str, current: CellStatus, target: CellStatus) -> None:
    allowed = _VALID_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise InvalidTransitionError(cell_id, current, target)


# ─── CellIdentity ──────────────────────────────────────────────────


@dataclass(frozen=True)
class CellIdentity:
    """Immutable identity of a cell instance."""

    cell_id: str
    cell_type: CellType
    parent_cell_id: str | None = None
    profile_id: str | None = None
    created_at: str = ""
    lineage: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.cell_id:
            raise ValueError("cell_id must not be empty")
        if not self.created_at:
            object.__setattr__(self, "created_at", _iso_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "cell_type": self.cell_type.value,
            "parent_cell_id": self.parent_cell_id,
            "profile_id": self.profile_id,
            "created_at": self.created_at,
            "lineage": list(self.lineage),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CellIdentity:
        return cls(
            cell_id=data["cell_id"],
            cell_type=CellType(data["cell_type"]),
            parent_cell_id=data.get("parent_cell_id"),
            profile_id=data.get("profile_id"),
            created_at=data.get("created_at", ""),
            lineage=tuple(data.get("lineage", ())),
            metadata=data.get("metadata", {}),
        )


# ─── CellContext ────────────────────────────────────────────────────


@dataclass
class CellContext:
    """Mutable context that shapes a cell's cognitive scope."""

    cell_id: str
    objective: str = ""
    expression_ref: str | None = None
    visible_domains: tuple[str, ...] = ()
    active_primitives: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    authority_level: AuthorityLevel = AuthorityLevel.PROPOSE
    environment_requirements: dict[str, Any] = field(default_factory=dict)
    memory_scope: str = "local"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "objective": self.objective,
            "expression_ref": self.expression_ref,
            "visible_domains": list(self.visible_domains),
            "active_primitives": list(self.active_primitives),
            "constraints": list(self.constraints),
            "authority_level": self.authority_level.value,
            "environment_requirements": self.environment_requirements,
            "memory_scope": self.memory_scope,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CellContext:
        authority = data.get("authority_level", "propose")
        if isinstance(authority, str):
            authority = AuthorityLevel(authority)
        return cls(
            cell_id=data["cell_id"],
            objective=data.get("objective", ""),
            expression_ref=data.get("expression_ref"),
            visible_domains=tuple(data.get("visible_domains", ())),
            active_primitives=tuple(data.get("active_primitives", ())),
            constraints=tuple(data.get("constraints", ())),
            authority_level=authority,
            environment_requirements=data.get("environment_requirements", {}),
            memory_scope=data.get("memory_scope", "local"),
            metadata=data.get("metadata", {}),
        )


# ─── CellCheckpoint ────────────────────────────────────────────────


@dataclass(frozen=True)
class CellCheckpoint:
    """Immutable snapshot of cell state at a point in time."""

    checkpoint_id: str
    cell_id: str
    status: CellStatus
    context: dict[str, Any]
    version: int
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            object.__setattr__(self, "created_at", _iso_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "cell_id": self.cell_id,
            "status": self.status.value,
            "context": self.context,
            "version": self.version,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


# ─── CellExecutionRequest ──────────────────────────────────────────


@dataclass(frozen=True)
class CellExecutionRequest:
    """A request from a cell to the control plane for execution.

    This is the ONLY way a cell can request work. It does NOT execute
    anything — it produces a structured request that the control plane
    bridge routes to the existing planning/execution spine.
    """

    request_id: str
    cell_id: str
    objective: str
    operation: str
    inputs: dict[str, Any] = field(default_factory=dict)
    constraints: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    environment: str = "default"
    authority_level: AuthorityLevel = AuthorityLevel.PROPOSE
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.request_id:
            raise ValueError("request_id must not be empty")
        if not self.cell_id:
            raise ValueError("cell_id must not be empty")
        if not self.objective:
            raise ValueError("objective must not be empty")
        if not self.created_at:
            object.__setattr__(self, "created_at", _iso_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "cell_id": self.cell_id,
            "objective": self.objective,
            "operation": self.operation,
            "inputs": self.inputs,
            "constraints": list(self.constraints),
            "required_capabilities": list(self.required_capabilities),
            "environment": self.environment,
            "authority_level": self.authority_level.value,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CellExecutionRequest:
        authority = data.get("authority_level", "propose")
        if isinstance(authority, str):
            authority = AuthorityLevel(authority)
        return cls(
            request_id=data["request_id"],
            cell_id=data["cell_id"],
            objective=data["objective"],
            operation=data.get("operation", ""),
            inputs=data.get("inputs", {}),
            constraints=tuple(data.get("constraints", ())),
            required_capabilities=tuple(data.get("required_capabilities", ())),
            environment=data.get("environment", "default"),
            authority_level=authority,
            created_at=data.get("created_at", ""),
            metadata=data.get("metadata", {}),
        )


# ─── CellResult ─────────────────────────────────────────────────────


@unique
class RequestStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    DELEGATED = "delegated"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass(frozen=True)
class CellResult:
    """Result of a cell execution request — status and outcome."""

    request_id: str
    cell_id: str
    status: RequestStatus
    plan_id: str = ""
    outputs: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            object.__setattr__(self, "created_at", _iso_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "cell_id": self.cell_id,
            "status": self.status.value,
            "plan_id": self.plan_id,
            "outputs": self.outputs,
            "error": self.error,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


def _gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"
