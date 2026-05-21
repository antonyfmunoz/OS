"""Phase 80 registry contracts — universal typed envelopes for all UMH resources.

Every discoverable thing (capability, adapter, backend, environment, policy,
model, tool, template, mode, etc.) becomes a RegistryItem with a stable shape.

No execution. No mutation. No adapter calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RegistryType(str, Enum):
    CAPABILITY = "capability"
    ADAPTER = "adapter"
    BACKEND = "backend"
    ENVIRONMENT = "environment"
    POLICY = "policy"
    MODEL = "model"
    TOOL = "tool"
    TEMPLATE = "template"
    LIBRARY = "library"
    WORKSTATION_MODE = "workstation_mode"
    RESOURCE = "resource"
    LEVERAGE = "leverage"
    METRIC = "metric"
    SCHEMA = "schema"
    WORKFLOW = "workflow"
    PRIMITIVE = "primitive"
    LAW = "law"
    DOMAIN_PROJECTION = "domain_projection"
    CORRESPONDENCE_MAP = "correspondence_map"
    ONTOLOGY = "ontology"
    LEGACY_MODULE = "legacy_module"
    MIGRATION_MAPPING = "migration_mapping"
    DEPRECATION_POLICY = "deprecation_policy"
    IMPORT_BOUNDARY_RULE = "import_boundary_rule"
    INTERFACE_SURFACE = "interface_surface"
    INTERFACE_COMMAND = "interface_command"
    INTERFACE_EVENT = "interface_event"
    COMMAND_CENTER_SECTION = "command_center_section"
    VOICE_WAVE_STATE = "voice_wave_state"
    NOTIFICATION_CHANNEL = "notification_channel"
    APPROVAL_SURFACE = "approval_surface"
    COUNCIL_ROLE = "council_role"
    COUNCIL_ADVISORY = "council_advisory"
    UNKNOWN = "unknown"


def normalize_registry_type(value: str) -> RegistryType:
    value = value.strip().lower()
    for member in RegistryType:
        if member.value == value:
            return member
    return RegistryType.UNKNOWN


class RegistryItemStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    REGISTERED = "registered"
    UNAVAILABLE = "unavailable"
    PENDING = "pending"
    UNKNOWN = "unknown"


def normalize_registry_item_status(value: str) -> RegistryItemStatus:
    value = value.strip().lower()
    for member in RegistryItemStatus:
        if member.value == value:
            return member
    return RegistryItemStatus.UNKNOWN


class RegistryAuthorityRequirement(str, Enum):
    NONE = "none"
    OBSERVE = "observe"
    ANALYZE = "analyze"
    ACT = "act"
    EXECUTE = "execute"
    UNKNOWN = "unknown"


def normalize_authority_requirement(value: str) -> RegistryAuthorityRequirement:
    value = value.strip().lower()
    for member in RegistryAuthorityRequirement:
        if member.value == value:
            return member
    return RegistryAuthorityRequirement.UNKNOWN


_MAX_QUERY_LIMIT = 100


def _registry_id() -> str:
    return f"reg_{uuid.uuid4().hex[:12]}"


@dataclass
class RegistryItem:
    item_id: str
    registry_type: RegistryType = RegistryType.UNKNOWN
    name: str = ""
    description: str = ""
    status: RegistryItemStatus = RegistryItemStatus.UNKNOWN
    authority_required: RegistryAuthorityRequirement = RegistryAuthorityRequirement.UNKNOWN
    capabilities: list[str] = field(default_factory=list)
    environments: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    version: str = ""
    source_module: str = ""
    risk_level: str = ""
    requires_approval: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "registry_type": self.registry_type.value,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "authority_required": self.authority_required.value,
            "capabilities": self.capabilities,
            "environments": self.environments,
            "tags": self.tags,
            "version": self.version,
            "source_module": self.source_module,
            "risk_level": self.risk_level,
            "requires_approval": self.requires_approval,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegistryItem:
        return cls(
            item_id=data.get("item_id", _registry_id()),
            registry_type=normalize_registry_type(data.get("registry_type", "unknown")),
            name=data.get("name", ""),
            description=data.get("description", ""),
            status=normalize_registry_item_status(data.get("status", "unknown")),
            authority_required=normalize_authority_requirement(
                data.get("authority_required", "unknown")
            ),
            capabilities=data.get("capabilities", []),
            environments=data.get("environments", []),
            tags=data.get("tags", []),
            version=data.get("version", ""),
            source_module=data.get("source_module", ""),
            risk_level=data.get("risk_level", ""),
            requires_approval=data.get("requires_approval", False),
            metadata=data.get("metadata", {}),
        )


@dataclass
class RegistryQuery:
    registry_type: str = ""
    name: str = ""
    capability: str = ""
    environment: str = ""
    tag: str = ""
    status: str = ""
    authority_required: str = ""
    risk_level: str = ""
    source_module: str = ""
    limit: int = 50

    def effective_limit(self) -> int:
        return max(1, min(self.limit, _MAX_QUERY_LIMIT))


@dataclass
class RegistryQueryResult:
    query: dict[str, Any] = field(default_factory=dict)
    items: list[RegistryItem] = field(default_factory=list)
    total_returned: int = 0
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "items": [i.to_dict() for i in self.items],
            "total_returned": self.total_returned,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }
