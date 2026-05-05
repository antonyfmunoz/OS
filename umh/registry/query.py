"""Phase 80 registry query — typed discovery across the unified catalog.

All queries are read-only. No execution. No mutation. No adapter calls.
Graceful when catalog is empty or sources unavailable.
"""

from __future__ import annotations

from typing import Any

from umh.registry.catalog import RegistryCatalog, build_default_registry_catalog
from umh.registry.contracts import (
    RegistryItem,
    RegistryQuery,
    RegistryQueryResult,
    RegistryType,
    normalize_registry_type,
)


def query_registry(
    catalog: RegistryCatalog | None = None,
    query: RegistryQuery | None = None,
) -> RegistryQueryResult:
    """Run a filtered query against the registry catalog."""
    if catalog is None:
        catalog = build_default_registry_catalog()

    q = query or RegistryQuery()
    warnings: list[str] = list(catalog.warnings)
    items = list(catalog.items)

    if q.registry_type:
        rt = normalize_registry_type(q.registry_type)
        items = [i for i in items if i.registry_type == rt]

    if q.name:
        name_lower = q.name.lower()
        items = [i for i in items if name_lower in i.name.lower()]

    if q.capability:
        items = [i for i in items if q.capability in i.capabilities]

    if q.environment:
        items = [i for i in items if q.environment in i.environments]

    if q.tag:
        items = [i for i in items if q.tag in i.tags]

    if q.status:
        items = [i for i in items if i.status.value == q.status]

    if q.authority_required:
        items = [i for i in items if i.authority_required.value == q.authority_required]

    if q.risk_level:
        items = [i for i in items if i.risk_level == q.risk_level]

    if q.source_module:
        items = [i for i in items if q.source_module in i.source_module]

    items = items[: q.effective_limit()]

    return RegistryQueryResult(
        query={
            "registry_type": q.registry_type,
            "name": q.name,
            "capability": q.capability,
            "environment": q.environment,
            "tag": q.tag,
            "status": q.status,
            "limit": q.effective_limit(),
        },
        items=items,
        total_returned=len(items),
        warnings=warnings,
    )


def find_capabilities(
    catalog: RegistryCatalog | None = None,
    environment: str = "",
    risk_level: str = "",
    limit: int = 50,
) -> list[RegistryItem]:
    result = query_registry(
        catalog,
        RegistryQuery(
            registry_type="capability",
            environment=environment,
            risk_level=risk_level,
            limit=limit,
        ),
    )
    return result.items


def find_adapters(
    catalog: RegistryCatalog | None = None,
    capability: str = "",
    environment: str = "",
    limit: int = 50,
) -> list[RegistryItem]:
    result = query_registry(
        catalog,
        RegistryQuery(
            registry_type="adapter",
            capability=capability,
            environment=environment,
            limit=limit,
        ),
    )
    return result.items


def find_backends(
    catalog: RegistryCatalog | None = None,
    environment: str = "",
    limit: int = 50,
) -> list[RegistryItem]:
    result = query_registry(
        catalog,
        RegistryQuery(
            registry_type="backend",
            environment=environment,
            limit=limit,
        ),
    )
    return result.items


def find_environments(
    catalog: RegistryCatalog | None = None,
    capability: str = "",
    limit: int = 50,
) -> list[RegistryItem]:
    result = query_registry(
        catalog,
        RegistryQuery(
            registry_type="environment",
            capability=capability,
            limit=limit,
        ),
    )
    return result.items


def find_policies(
    catalog: RegistryCatalog | None = None,
    limit: int = 50,
) -> list[RegistryItem]:
    result = query_registry(
        catalog,
        RegistryQuery(registry_type="policy", limit=limit),
    )
    return result.items


def find_workstation_modes(
    catalog: RegistryCatalog | None = None,
    limit: int = 50,
) -> list[RegistryItem]:
    result = query_registry(
        catalog,
        RegistryQuery(registry_type="workstation_mode", limit=limit),
    )
    return result.items


def get_registry_item(
    catalog: RegistryCatalog | None = None,
    item_id: str = "",
    name: str = "",
) -> RegistryItem | None:
    if catalog is None:
        catalog = build_default_registry_catalog()

    if item_id:
        return catalog.by_id(item_id)
    if name:
        return catalog.by_name(name)
    return None


def explain_registry_match(
    item: RegistryItem,
    query: RegistryQuery,
) -> dict[str, Any]:
    """Explain why a registry item matched a query. Evidence-derived, no causal claims."""
    reasons: list[str] = []

    if query.registry_type and item.registry_type.value == query.registry_type:
        reasons.append(f"type matches: {item.registry_type.value}")
    if query.name and query.name.lower() in item.name.lower():
        reasons.append(f"name contains: {query.name}")
    if query.capability and query.capability in item.capabilities:
        reasons.append(f"supports capability: {query.capability}")
    if query.environment and query.environment in item.environments:
        reasons.append(f"available in environment: {query.environment}")
    if query.tag and query.tag in item.tags:
        reasons.append(f"tagged: {query.tag}")
    if query.status and item.status.value == query.status:
        reasons.append(f"status: {query.status}")
    if query.risk_level and item.risk_level == query.risk_level:
        reasons.append(f"risk level: {query.risk_level}")

    return {
        "item_id": item.item_id,
        "name": item.name,
        "match_reasons": reasons,
        "match_count": len(reasons),
    }
