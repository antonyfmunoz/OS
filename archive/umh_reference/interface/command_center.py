"""Phase 84 Command Center read models — UI-safe snapshot assembly.

Read model only. No execution. Accepts optional inputs and degrades
gracefully. Missing components produce warnings, not crashes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


class CommandCenterSection(str, Enum):
    DASHBOARD = "dashboard"
    ACTIVITY = "activity"
    APPROVALS = "approvals"
    TRACES = "traces"
    MEMORY = "memory"
    REGISTRY = "registry"
    ONTOLOGY = "ontology"
    STORAGE = "storage"
    MIGRATION = "migration"
    WORKSTATION = "workstation"
    SETTINGS = "settings"
    UNKNOWN = "unknown"


def normalize_command_center_section(value: str) -> CommandCenterSection:
    try:
        return CommandCenterSection(value.lower().strip())
    except (ValueError, AttributeError):
        return CommandCenterSection.UNKNOWN


@dataclass
class CommandCenterSnapshot:
    generated_at: str = ""
    active_section: CommandCenterSection = CommandCenterSection.DASHBOARD
    surface_id: str | None = None
    system_status: dict[str, Any] | None = None
    operator_dashboard: dict[str, Any] | None = None
    workstation_summary: dict[str, Any] | None = None
    pending_approvals: list[dict[str, Any]] = field(default_factory=list)
    notifications: list[dict[str, Any]] = field(default_factory=list)
    registry_summary: dict[str, Any] | None = None
    ontology_summary: dict[str, Any] | None = None
    storage_summary: dict[str, Any] | None = None
    migration_summary: dict[str, Any] | None = None
    voice_wave: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "active_section": self.active_section.value
            if isinstance(self.active_section, Enum)
            else self.active_section,
            "surface_id": self.surface_id,
            "system_status": self.system_status,
            "operator_dashboard": self.operator_dashboard,
            "workstation_summary": self.workstation_summary,
            "pending_approvals": self.pending_approvals,
            "notifications": self.notifications,
            "registry_summary": self.registry_summary,
            "ontology_summary": self.ontology_summary,
            "storage_summary": self.storage_summary,
            "migration_summary": self.migration_summary,
            "voice_wave": self.voice_wave,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def build_command_center_snapshot(
    *,
    system_status: dict[str, Any] | None = None,
    operator_dashboard: dict[str, Any] | None = None,
    workstation_summary: dict[str, Any] | None = None,
    pending_approvals: list[dict[str, Any]] | None = None,
    notifications: list[dict[str, Any]] | None = None,
    registry_summary: dict[str, Any] | None = None,
    ontology_summary: dict[str, Any] | None = None,
    storage_summary: dict[str, Any] | None = None,
    migration_summary: dict[str, Any] | None = None,
    voice_wave: dict[str, Any] | None = None,
    active_section: CommandCenterSection | None = None,
    surface_id: str | None = None,
) -> CommandCenterSnapshot:
    warnings: list[str] = []

    if system_status is None:
        warnings.append("System status unavailable")
    if operator_dashboard is None:
        warnings.append("Operator dashboard unavailable")
    if workstation_summary is None:
        warnings.append("Workstation summary unavailable")
    if registry_summary is None:
        warnings.append("Registry summary unavailable")
    if ontology_summary is None:
        warnings.append("Ontology summary unavailable")
    if storage_summary is None:
        warnings.append("Storage summary unavailable")
    if migration_summary is None:
        warnings.append("Migration summary unavailable")

    return CommandCenterSnapshot(
        generated_at=_iso_now(),
        active_section=active_section or CommandCenterSection.DASHBOARD,
        surface_id=surface_id,
        system_status=system_status,
        operator_dashboard=operator_dashboard,
        workstation_summary=workstation_summary,
        pending_approvals=pending_approvals or [],
        notifications=notifications or [],
        registry_summary=registry_summary,
        ontology_summary=ontology_summary,
        storage_summary=storage_summary,
        migration_summary=migration_summary,
        voice_wave=voice_wave,
        warnings=warnings,
    )
