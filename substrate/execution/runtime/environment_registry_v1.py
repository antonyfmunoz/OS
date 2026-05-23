"""Environment Registry v1 for the canonical runtime spine.

Registry of execution environments with capability maps, authority
domains, and health tracking. Each environment declares what it can
do and what authority it holds.

Three environments at launch:
  vps_tmux       — remote orchestration, shell, filesystem, git
  local_workstation — GUI actuation, local shell, filesystem
  sandbox        — read-only analysis, report generation

Deterministic. No ML. No autonomy.

UMH substrate subsystem.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .execution_contracts_v1 import CapabilityDomain, _now_iso


class EnvironmentStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass
class EnvironmentDescriptor:
    """Describes a single execution environment."""

    environment_id: str
    environment_type: str
    display_name: str
    capabilities: list[CapabilityDomain] = field(default_factory=list)
    authority_domains: list[str] = field(default_factory=list)
    can_gui: bool = False
    can_shell: bool = False
    can_write_filesystem: bool = False
    is_remote: bool = False
    status: EnvironmentStatus = EnvironmentStatus.HEALTHY
    last_heartbeat: str = ""
    notes: list[str] = field(default_factory=list)

    def has_capability(self, cap: CapabilityDomain) -> bool:
        return cap in self.capabilities

    def is_available(self) -> bool:
        return self.status in (EnvironmentStatus.HEALTHY, EnvironmentStatus.DEGRADED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment_id": self.environment_id,
            "environment_type": self.environment_type,
            "display_name": self.display_name,
            "capabilities": [c.value for c in self.capabilities],
            "authority_domains": self.authority_domains,
            "can_gui": self.can_gui,
            "can_shell": self.can_shell,
            "can_write_filesystem": self.can_write_filesystem,
            "is_remote": self.is_remote,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Pre-built environment descriptors
# ---------------------------------------------------------------------------

VPS_TMUX = EnvironmentDescriptor(
    environment_id="vps-tmux-01",
    environment_type="vps_tmux",
    display_name="VPS (tmux)",
    capabilities=[
        CapabilityDomain.SHELL_EXECUTION,
        CapabilityDomain.FILESYSTEM_READ,
        CapabilityDomain.FILESYSTEM_WRITE,
        CapabilityDomain.GIT_INSPECTION,
        CapabilityDomain.MEMORY_QUERY,
        CapabilityDomain.MEMORY_WRITE,
        CapabilityDomain.REPORT_GENERATION,
        CapabilityDomain.DOCUMENT_INGESTION,
    ],
    authority_domains=["remote_orchestration"],
    can_gui=False,
    can_shell=True,
    can_write_filesystem=True,
    is_remote=True,
)

LOCAL_WORKSTATION = EnvironmentDescriptor(
    environment_id="local-workstation-01",
    environment_type="local_windows_desktop",
    display_name="Local Workstation (Windows)",
    capabilities=[
        CapabilityDomain.SHELL_EXECUTION,
        CapabilityDomain.FILESYSTEM_READ,
        CapabilityDomain.FILESYSTEM_WRITE,
        CapabilityDomain.GIT_INSPECTION,
        CapabilityDomain.GUI_ACTUATION,
    ],
    authority_domains=["local_gui", "local_shell"],
    can_gui=True,
    can_shell=True,
    can_write_filesystem=True,
    is_remote=False,
)

SANDBOX = EnvironmentDescriptor(
    environment_id="sandbox-01",
    environment_type="sandbox",
    display_name="Sandbox (read-only)",
    capabilities=[
        CapabilityDomain.FILESYSTEM_READ,
        CapabilityDomain.GIT_INSPECTION,
        CapabilityDomain.MEMORY_QUERY,
        CapabilityDomain.REPORT_GENERATION,
    ],
    authority_domains=[],
    can_gui=False,
    can_shell=False,
    can_write_filesystem=False,
    is_remote=False,
    notes=["Read-only analysis environment, no side effects"],
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class EnvironmentRegistry:
    """Registry of available execution environments."""

    def __init__(self) -> None:
        self._environments: dict[str, EnvironmentDescriptor] = {}

    def register(self, env: EnvironmentDescriptor) -> None:
        self._environments[env.environment_id] = env

    def get(self, environment_id: str) -> EnvironmentDescriptor | None:
        return self._environments.get(environment_id)

    def get_by_type(self, environment_type: str) -> list[EnvironmentDescriptor]:
        return [e for e in self._environments.values() if e.environment_type == environment_type]

    def find_for_capability(self, capability: CapabilityDomain) -> list[EnvironmentDescriptor]:
        return [
            e
            for e in self._environments.values()
            if e.has_capability(capability) and e.is_available()
        ]

    def find_for_gui(self) -> list[EnvironmentDescriptor]:
        return [e for e in self._environments.values() if e.can_gui and e.is_available()]

    def get_available(self) -> list[EnvironmentDescriptor]:
        return [e for e in self._environments.values() if e.is_available()]

    def update_status(self, environment_id: str, status: EnvironmentStatus) -> bool:
        env = self._environments.get(environment_id)
        if not env:
            return False
        env.status = status
        env.last_heartbeat = _now_iso()
        return True

    def get_stats(self) -> dict[str, Any]:
        statuses = {}
        for env in self._environments.values():
            statuses[env.status.value] = statuses.get(env.status.value, 0) + 1
        return {
            "total": len(self._environments),
            "available": len(self.get_available()),
            "by_status": statuses,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "environments": {eid: e.to_dict() for eid, e in self._environments.items()},
            "stats": self.get_stats(),
        }

    @classmethod
    def create_default(cls) -> EnvironmentRegistry:
        """Create registry with the three default environments."""
        registry = cls()
        registry.register(VPS_TMUX)
        registry.register(LOCAL_WORKSTATION)
        registry.register(SANDBOX)
        return registry

    @classmethod
    def from_json_file(cls, path: Path | str) -> EnvironmentRegistry:
        """Load environments from a JSON file."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        registry = cls()
        for env_data in data.get("environments", []):
            caps = [CapabilityDomain(c) for c in env_data.get("capabilities", [])]
            env = EnvironmentDescriptor(
                environment_id=env_data["environment_id"],
                environment_type=env_data["environment_type"],
                display_name=env_data.get("display_name", env_data["environment_id"]),
                capabilities=caps,
                authority_domains=env_data.get("authority_domains", []),
                can_gui=env_data.get("can_gui", False),
                can_shell=env_data.get("can_shell", False),
                can_write_filesystem=env_data.get("can_write_filesystem", False),
                is_remote=env_data.get("is_remote", False),
                status=EnvironmentStatus(env_data.get("status", "healthy")),
                notes=env_data.get("notes", []),
            )
            registry.register(env)
        return registry
