"""Phase 80 registry catalog — unified collection of all discoverable items.

Assembles RegistryItems from all compatibility bridges. Read-only.
Safe if any bridge source is unavailable — returns empty for that type.
No execution. No mutation. No adapter calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.registry.contracts import (
    RegistryItem,
    RegistryType,
)


@dataclass
class RegistryCatalog:
    items: list[RegistryItem] = field(default_factory=list)
    generated_at: str = ""
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add(self, item: RegistryItem) -> None:
        self.items.append(item)

    def add_all(self, items: list[RegistryItem]) -> None:
        self.items.extend(items)

    def by_type(self, registry_type: RegistryType) -> list[RegistryItem]:
        return [i for i in self.items if i.registry_type == registry_type]

    def by_name(self, name: str) -> RegistryItem | None:
        name_lower = name.lower()
        for item in self.items:
            if item.name.lower() == name_lower:
                return item
        return None

    def by_id(self, item_id: str) -> RegistryItem | None:
        for item in self.items:
            if item.item_id == item_id:
                return item
        return None

    def count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.items:
            key = item.registry_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [i.to_dict() for i in self.items],
            "total": len(self.items),
            "by_type": self.count_by_type(),
            "generated_at": self.generated_at,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def build_default_registry_catalog(
    *,
    adapter_backend: Any | None = None,
    backend_registry: Any | None = None,
    mode_registry: Any | None = None,
) -> RegistryCatalog:
    """Build a catalog from all known sources. Safe if any source unavailable."""
    from umh.registry.bridges import (
        adapter_pack_to_registry_items,
        backend_registry_to_registry_items,
        capability_definitions_to_registry_items,
        environment_definitions_to_registry_items,
        governance_policies_to_registry_items,
        workstation_modes_to_registry_items,
    )

    catalog = RegistryCatalog(generated_at=_iso_now())

    try:
        catalog.add_all(capability_definitions_to_registry_items())
    except Exception:
        catalog.warnings.append("failed to load capability definitions")

    try:
        catalog.add_all(environment_definitions_to_registry_items())
    except Exception:
        catalog.warnings.append("failed to load environment definitions")

    try:
        catalog.add_all(adapter_pack_to_registry_items(adapter_backend))
    except Exception:
        catalog.warnings.append("failed to load adapter pack")

    try:
        catalog.add_all(backend_registry_to_registry_items(backend_registry))
    except Exception:
        catalog.warnings.append("failed to load backend registry")

    try:
        catalog.add_all(workstation_modes_to_registry_items(mode_registry))
    except Exception:
        catalog.warnings.append("failed to load workstation modes")

    try:
        catalog.add_all(governance_policies_to_registry_items())
    except Exception:
        catalog.warnings.append("failed to load governance policies")

    try:
        from umh.registry.bridges import ontology_primitives_to_registry_items

        catalog.add_all(ontology_primitives_to_registry_items())
    except Exception:
        catalog.warnings.append("failed to load ontology primitives")

    try:
        from umh.registry.bridges import ontology_laws_to_registry_items

        catalog.add_all(ontology_laws_to_registry_items())
    except Exception:
        catalog.warnings.append("failed to load ontology laws")

    try:
        from umh.registry.bridges import domain_projections_to_registry_items

        catalog.add_all(domain_projections_to_registry_items())
    except Exception:
        catalog.warnings.append("failed to load domain projections")

    try:
        from umh.registry.bridges import correspondence_maps_to_registry_items

        catalog.add_all(correspondence_maps_to_registry_items())
    except Exception:
        catalog.warnings.append("failed to load correspondence maps")

    try:
        from umh.registry.bridges import import_boundary_rules_to_registry_items

        catalog.add_all(import_boundary_rules_to_registry_items())
    except Exception:
        catalog.warnings.append("failed to load import boundary rules")

    try:
        from umh.registry.bridges import interface_surfaces_to_registry_items

        catalog.add_all(interface_surfaces_to_registry_items())
    except Exception:
        catalog.warnings.append("failed to load interface surfaces")

    try:
        from umh.registry.bridges import interface_commands_to_registry_items

        catalog.add_all(interface_commands_to_registry_items())
    except Exception:
        catalog.warnings.append("failed to load interface commands")

    try:
        from umh.registry.bridges import voice_wave_states_to_registry_items

        catalog.add_all(voice_wave_states_to_registry_items())
    except Exception:
        catalog.warnings.append("failed to load voice wave states")

    try:
        from umh.registry.bridges import command_center_sections_to_registry_items

        catalog.add_all(command_center_sections_to_registry_items())
    except Exception:
        catalog.warnings.append("failed to load command center sections")

    try:
        from umh.registry.bridges import council_roles_to_registry_items

        catalog.add_all(council_roles_to_registry_items())
    except Exception:
        catalog.warnings.append("failed to load council roles")

    return catalog


def export_storage_descriptors(
    catalog: RegistryCatalog | None = None,
) -> list[Any]:
    from umh.storage.contracts import (
        StorageBackendType,
        StorageMutability,
        StorageRecordDescriptor,
        StorageRecordType,
        StorageScope,
        StorageSource,
    )

    if catalog is None:
        try:
            catalog = build_default_registry_catalog()
        except Exception:
            return []

    descriptors: list[StorageRecordDescriptor] = []
    for item in catalog.items:
        descriptors.append(
            StorageRecordDescriptor(
                record_id=item.item_id,
                record_type=StorageRecordType.REGISTRY_ITEM,
                scope=StorageScope.SYSTEM,
                mutability=StorageMutability.VERSIONED,
                source=StorageSource.REGISTRY,
                backend_type=StorageBackendType.MEMORY,
                owner_id="",
            )
        )
    return descriptors
