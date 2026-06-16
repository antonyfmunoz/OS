"""Workspace Runtime Graph — canonical workspace topology models.

Maps engineering workspaces to their repositories, runtimes, build targets,
and devices. Read-only topology — no execution, no deployment, no build authority.

Phase 27. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class WorkspaceType(str, Enum):
    CORE = "core"
    PRODUCT = "product"
    SERVICE = "service"
    INFRASTRUCTURE = "infrastructure"


class RuntimeTargetType(str, Enum):
    ELECTRON = "electron"
    REACT = "react"
    DOCKER = "docker"
    PYTHON = "python"
    PREVIEW = "preview"
    API = "api"


class BuildTargetType(str, Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    CONTAINER = "container"


class WorkspaceHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass
class WorkspaceRepository:
    repository_id: str
    name: str = ""
    path: str = ""
    branch: str = "main"
    workspace_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "name": self.name,
            "path": self.path,
            "branch": self.branch,
            "workspace_id": self.workspace_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkspaceRepository:
        return cls(
            repository_id=data.get("repository_id", ""),
            name=data.get("name", ""),
            path=data.get("path", ""),
            branch=data.get("branch", "main"),
            workspace_id=data.get("workspace_id", ""),
        )


@dataclass
class WorkspaceRuntime:
    runtime_id: str
    workspace_id: str = ""
    runtime_type: str = ""
    host_device_id: str = ""
    ports: list[int] = field(default_factory=list)
    status: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "workspace_id": self.workspace_id,
            "runtime_type": self.runtime_type,
            "host_device_id": self.host_device_id,
            "ports": self.ports,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkspaceRuntime:
        return cls(
            runtime_id=data.get("runtime_id", ""),
            workspace_id=data.get("workspace_id", ""),
            runtime_type=data.get("runtime_type", ""),
            host_device_id=data.get("host_device_id", ""),
            ports=data.get("ports", []),
            status=data.get("status", "unknown"),
        )


@dataclass
class WorkspaceBuildTarget:
    target_id: str
    workspace_id: str = ""
    build_type: str = ""
    device_id: str = ""
    preferred: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "workspace_id": self.workspace_id,
            "build_type": self.build_type,
            "device_id": self.device_id,
            "preferred": self.preferred,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkspaceBuildTarget:
        return cls(
            target_id=data.get("target_id", ""),
            workspace_id=data.get("workspace_id", ""),
            build_type=data.get("build_type", ""),
            device_id=data.get("device_id", ""),
            preferred=data.get("preferred", False),
        )


@dataclass
class WorkspaceDefinition:
    workspace_id: str
    name: str = ""
    workspace_type: WorkspaceType = WorkspaceType.CORE
    repositories: list[WorkspaceRepository] = field(default_factory=list)
    runtimes: list[WorkspaceRuntime] = field(default_factory=list)
    build_targets: list[WorkspaceBuildTarget] = field(default_factory=list)
    device_ids: list[str] = field(default_factory=list)
    health: WorkspaceHealth = WorkspaceHealth.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "workspace_type": self.workspace_type.value,
            "repositories": [r.to_dict() for r in self.repositories],
            "runtimes": [r.to_dict() for r in self.runtimes],
            "build_targets": [b.to_dict() for b in self.build_targets],
            "device_ids": self.device_ids,
            "health": self.health.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkspaceDefinition:
        wtype = data.get("workspace_type", "core")
        health = data.get("health", "unknown")
        return cls(
            workspace_id=data.get("workspace_id", ""),
            name=data.get("name", ""),
            workspace_type=WorkspaceType(wtype) if isinstance(wtype, str) else wtype,
            repositories=[WorkspaceRepository.from_dict(r) for r in data.get("repositories", [])],
            runtimes=[WorkspaceRuntime.from_dict(r) for r in data.get("runtimes", [])],
            build_targets=[
                WorkspaceBuildTarget.from_dict(b) for b in data.get("build_targets", [])
            ],
            device_ids=data.get("device_ids", []),
            health=WorkspaceHealth(health) if isinstance(health, str) else health,
        )


@dataclass
class WorkspaceRuntimeGraph:
    graph_id: str = field(default_factory=lambda: f"wrg-{uuid4().hex[:12]}")
    workspaces: list[WorkspaceDefinition] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "workspaces": [w.to_dict() for w in self.workspaces],
            "workspace_count": len(self.workspaces),
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkspaceRuntimeGraph:
        return cls(
            graph_id=data.get("graph_id", ""),
            workspaces=[WorkspaceDefinition.from_dict(w) for w in data.get("workspaces", [])],
            generated_at=data.get("generated_at", 0.0),
        )
