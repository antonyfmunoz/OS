"""Environment models — nodes, tasks, contexts, and results.

Typed contracts for the environment runtime layer.
Cells decide WHAT. Control plane approves. This layer decides WHERE + HOW.

No imports from umh/cells, umh/adapters, or umh/execution.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any

from umh.core.clock import iso_now as _iso_now


@unique
class NodeType(str, Enum):
    LOCAL = "local"
    VPS = "vps"
    CLOUD = "cloud"
    MOBILE = "mobile"


@unique
class NodeStatus(str, Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"


@unique
class ExecutionIsolation(str, Enum):
    PROCESS = "process"
    CONTAINER = "container"
    SANDBOX = "sandbox"


@unique
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"


@unique
class ExecutionMode(str, Enum):
    DOCKER = "docker"
    SUBPROCESS = "subprocess"


@unique
class ContainerStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    TERMINATED = "terminated"


@unique
class SandboxVerdict(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


# ─── Resource spec ────────────────────────────────────────────────────


@dataclass(frozen=True)
class ResourceRequirements:
    cpu_cores: float = 1.0
    memory_mb: int = 512
    gpu: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


# ─── Permission spec ──────────────────────────────────────────────────


@dataclass(frozen=True)
class EnvironmentPermissions:
    read: bool = True
    write: bool = False
    network: bool = False
    filesystem: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


# ─── Node ─────────────────────────────────────────────────────────────


@dataclass
class Node:
    node_id: str
    node_type: NodeType
    cpu_cores: float = 4.0
    memory_mb: int = 8192
    gpu: bool = False
    current_load: float = 0.0
    status: NodeStatus = NodeStatus.AVAILABLE
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def can_satisfy(self, requirements: ResourceRequirements) -> bool:
        if requirements.gpu and not self.gpu:
            return False
        if requirements.cpu_cores > self.cpu_cores:
            return False
        if requirements.memory_mb > self.memory_mb:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "cpu_cores": self.cpu_cores,
            "memory_mb": self.memory_mb,
            "gpu": self.gpu,
            "current_load": self.current_load,
            "status": self.status.value,
            "priority": self.priority,
            "metadata": self.metadata,
        }


# ─── ExecutionContext ─────────────────────────────────────────────────


@dataclass(frozen=True)
class ExecutionContext:
    context_id: str
    node_id: str
    isolation: ExecutionIsolation
    permissions: EnvironmentPermissions = field(default_factory=EnvironmentPermissions)
    timeout_s: int = 30
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            object.__setattr__(self, "created_at", _iso_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "node_id": self.node_id,
            "isolation": self.isolation.value,
            "timeout_s": self.timeout_s,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


# ─── ExecutionTask ────────────────────────────────────────────────────


@dataclass(frozen=True)
class ExecutionTask:
    task_id: str
    plan_objective_id: str
    operation: str
    resources: ResourceRequirements = field(default_factory=ResourceRequirements)
    priority: int = 0
    latency_sensitive: bool = False
    environment_preference: NodeType | None = None
    inputs: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.task_id:
            raise ValueError("task_id must not be empty")
        if not self.plan_objective_id:
            raise ValueError("plan_objective_id must not be empty")
        if not self.created_at:
            object.__setattr__(self, "created_at", _iso_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "plan_objective_id": self.plan_objective_id,
            "operation": self.operation,
            "priority": self.priority,
            "latency_sensitive": self.latency_sensitive,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


# ─── ExecutionResult ──────────────────────────────────────────────────


@dataclass(frozen=True)
class ExecutionResult:
    task_id: str
    status: TaskStatus
    output: dict[str, Any] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)
    node_id: str = ""
    container_id: str | None = None
    started_at: str = ""
    finished_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.started_at:
            object.__setattr__(self, "started_at", _iso_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "output": self.output,
            "logs": self.logs,
            "node_id": self.node_id,
            "container_id": self.container_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "metadata": self.metadata,
        }


# ─── Container ────────────────────────────────────────────────────────


@dataclass
class ExecutionContainer:
    container_id: str
    node_id: str
    status: ContainerStatus = ContainerStatus.CREATED
    context: ExecutionContext | None = None
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = _iso_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "container_id": self.container_id,
            "node_id": self.node_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


def _gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"
