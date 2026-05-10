"""Phase 80 registry views — UI-facing read models for registry data.

Stable, typed, safe for display. No sensitive data exposed. No execution.
No adapter calls. No mutation. Sparse-safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.registry.catalog import RegistryCatalog, build_default_registry_catalog
from umh.registry.contracts import RegistryItem


@dataclass
class RegistryItemView:
    item_id: str
    registry_type: str = ""
    name: str = ""
    description: str = ""
    status: str = ""
    authority_required: str = ""
    capability_count: int = 0
    environment_count: int = 0
    tags: list[str] = field(default_factory=list)
    risk_level: str = ""
    requires_approval: bool = False
    source_module: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "registry_type": self.registry_type,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "authority_required": self.authority_required,
            "capability_count": self.capability_count,
            "environment_count": self.environment_count,
            "tags": self.tags,
            "risk_level": self.risk_level,
            "requires_approval": self.requires_approval,
            "source_module": self.source_module,
            "metadata": self.metadata,
        }


@dataclass
class RegistryCatalogView:
    total_items: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    by_status: dict[str, int] = field(default_factory=dict)
    capabilities_count: int = 0
    adapters_count: int = 0
    backends_count: int = 0
    environments_count: int = 0
    modes_count: int = 0
    policies_count: int = 0
    warnings: list[str] = field(default_factory=list)
    generated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_items": self.total_items,
            "by_type": self.by_type,
            "by_status": self.by_status,
            "capabilities_count": self.capabilities_count,
            "adapters_count": self.adapters_count,
            "backends_count": self.backends_count,
            "environments_count": self.environments_count,
            "modes_count": self.modes_count,
            "policies_count": self.policies_count,
            "warnings": self.warnings,
            "generated_at": self.generated_at,
            "metadata": self.metadata,
        }


@dataclass
class RegistryHealthView:
    total_items: int = 0
    active_count: int = 0
    inactive_count: int = 0
    deprecated_count: int = 0
    unavailable_count: int = 0
    unknown_count: int = 0
    source_modules: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_items": self.total_items,
            "active_count": self.active_count,
            "inactive_count": self.inactive_count,
            "deprecated_count": self.deprecated_count,
            "unavailable_count": self.unavailable_count,
            "unknown_count": self.unknown_count,
            "source_modules": self.source_modules,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def registry_item_to_view(item: RegistryItem) -> RegistryItemView:
    return RegistryItemView(
        item_id=item.item_id,
        registry_type=item.registry_type.value,
        name=item.name,
        description=item.description[:200] if item.description else "",
        status=item.status.value,
        authority_required=item.authority_required.value,
        capability_count=len(item.capabilities),
        environment_count=len(item.environments),
        tags=list(item.tags),
        risk_level=item.risk_level,
        requires_approval=item.requires_approval,
        source_module=item.source_module,
    )


def build_catalog_view(catalog: RegistryCatalog | None = None) -> RegistryCatalogView:
    if catalog is None:
        catalog = build_default_registry_catalog()

    by_type = catalog.count_by_type()
    by_status: dict[str, int] = {}
    for item in catalog.items:
        s = item.status.value
        by_status[s] = by_status.get(s, 0) + 1

    return RegistryCatalogView(
        total_items=len(catalog.items),
        by_type=by_type,
        by_status=by_status,
        capabilities_count=by_type.get("capability", 0),
        adapters_count=by_type.get("adapter", 0),
        backends_count=by_type.get("backend", 0),
        environments_count=by_type.get("environment", 0),
        modes_count=by_type.get("workstation_mode", 0),
        policies_count=by_type.get("policy", 0),
        warnings=catalog.warnings,
        generated_at=catalog.generated_at,
    )


def build_registry_health_view(
    catalog: RegistryCatalog | None = None,
) -> RegistryHealthView:
    if catalog is None:
        catalog = build_default_registry_catalog()

    active = sum(1 for i in catalog.items if i.status.value == "active")
    inactive = sum(1 for i in catalog.items if i.status.value == "inactive")
    deprecated = sum(1 for i in catalog.items if i.status.value == "deprecated")
    unavailable = sum(1 for i in catalog.items if i.status.value == "unavailable")
    unknown = sum(1 for i in catalog.items if i.status.value == "unknown")

    sources = sorted({i.source_module for i in catalog.items if i.source_module})

    return RegistryHealthView(
        total_items=len(catalog.items),
        active_count=active,
        inactive_count=inactive,
        deprecated_count=deprecated,
        unavailable_count=unavailable,
        unknown_count=unknown,
        source_modules=sources,
        warnings=catalog.warnings,
    )
