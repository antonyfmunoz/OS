"""Phase 77 workstation modes — operational context presets.

Modes affect context and preferences, NOT authority.
A mode cannot downgrade governance below policy.
A mode cannot execute directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WorkstationMode(str, Enum):
    COMMAND_CENTER = "command_center"
    DEVELOPER = "developer"
    RESEARCH = "research"
    MAINTENANCE = "maintenance"
    OUTREACH = "outreach"
    CONTENT = "content"
    OVERNIGHT = "overnight"
    SIMULATION = "simulation"
    EMERGENCY = "emergency"


@dataclass(frozen=True)
class ModeProfile:
    mode: WorkstationMode
    description: str
    default_environment_preference: str = "local"
    allowed_capabilities: frozenset[str] = field(default_factory=frozenset)
    restricted_capabilities: frozenset[str] = field(default_factory=frozenset)
    default_governance_level: str = "analyze"
    memory_context_tags: tuple[str, ...] = ()
    trace_query_defaults: dict[str, Any] = field(default_factory=dict)
    boot_sequence_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "description": self.description,
            "default_environment_preference": self.default_environment_preference,
            "allowed_capabilities": sorted(self.allowed_capabilities),
            "restricted_capabilities": sorted(self.restricted_capabilities),
            "default_governance_level": self.default_governance_level,
            "memory_context_tags": list(self.memory_context_tags),
            "boot_sequence_id": self.boot_sequence_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModeProfile:
        return cls(
            mode=WorkstationMode(data["mode"]),
            description=data.get("description", ""),
            default_environment_preference=data.get("default_environment_preference", "local"),
            allowed_capabilities=frozenset(data.get("allowed_capabilities", [])),
            restricted_capabilities=frozenset(data.get("restricted_capabilities", [])),
            default_governance_level=data.get("default_governance_level", "analyze"),
            memory_context_tags=tuple(data.get("memory_context_tags", [])),
            boot_sequence_id=data.get("boot_sequence_id", ""),
        )


_MVP_MODES: dict[WorkstationMode, ModeProfile] = {
    WorkstationMode.COMMAND_CENTER: ModeProfile(
        mode=WorkstationMode.COMMAND_CENTER,
        description="Full operational mode — all capabilities, governed execution",
        default_environment_preference="local",
        default_governance_level="analyze",
        memory_context_tags=("operations", "tasks", "goals"),
    ),
    WorkstationMode.DEVELOPER: ModeProfile(
        mode=WorkstationMode.DEVELOPER,
        description="Development focus — CLI and filesystem primary",
        default_environment_preference="local",
        default_governance_level="act",
        memory_context_tags=("development", "code", "architecture"),
    ),
    WorkstationMode.RESEARCH: ModeProfile(
        mode=WorkstationMode.RESEARCH,
        description="Research mode — read-heavy, simulation preferred",
        default_environment_preference="simulation",
        default_governance_level="analyze",
        memory_context_tags=("research", "analysis", "data"),
    ),
    WorkstationMode.MAINTENANCE: ModeProfile(
        mode=WorkstationMode.MAINTENANCE,
        description="System maintenance — diagnostics, health checks",
        default_environment_preference="local",
        default_governance_level="act",
        memory_context_tags=("maintenance", "diagnostics", "health"),
    ),
    WorkstationMode.OUTREACH: ModeProfile(
        mode=WorkstationMode.OUTREACH,
        description="Outreach and communication focus",
        default_environment_preference="local",
        default_governance_level="analyze",
        memory_context_tags=("outreach", "crm", "leads"),
    ),
    WorkstationMode.CONTENT: ModeProfile(
        mode=WorkstationMode.CONTENT,
        description="Content creation and publishing",
        default_environment_preference="local",
        default_governance_level="analyze",
        memory_context_tags=("content", "brand", "media"),
    ),
    WorkstationMode.OVERNIGHT: ModeProfile(
        mode=WorkstationMode.OVERNIGHT,
        description="Unattended overnight execution — conservative governance",
        default_environment_preference="simulation",
        default_governance_level="observe",
        memory_context_tags=("overnight", "scheduled"),
    ),
    WorkstationMode.SIMULATION: ModeProfile(
        mode=WorkstationMode.SIMULATION,
        description="Simulation-only — no real execution",
        default_environment_preference="simulation",
        default_governance_level="observe",
        memory_context_tags=("simulation", "testing"),
    ),
    WorkstationMode.EMERGENCY: ModeProfile(
        mode=WorkstationMode.EMERGENCY,
        description="Emergency response — elevated authority, all capabilities",
        default_environment_preference="local",
        default_governance_level="execute",
        memory_context_tags=("emergency", "incident"),
    ),
}


class ModeRegistry:
    """Registry of available workstation modes."""

    def __init__(self) -> None:
        self._modes: dict[WorkstationMode, ModeProfile] = dict(_MVP_MODES)

    def register_mode(self, profile: ModeProfile) -> None:
        self._modes[profile.mode] = profile

    def get_mode(self, mode: WorkstationMode | str) -> ModeProfile | None:
        if isinstance(mode, str):
            try:
                mode = WorkstationMode(mode)
            except ValueError:
                return None
        return self._modes.get(mode)

    def list_modes(self) -> list[ModeProfile]:
        return list(self._modes.values())

    def validate_mode(self, mode: str) -> bool:
        try:
            WorkstationMode(mode)
            return True
        except ValueError:
            return False

    @staticmethod
    def default_modes() -> list[ModeProfile]:
        return list(_MVP_MODES.values())
