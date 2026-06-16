"""Service Dependency Registry — canonical registry of service dependencies.

Single source of truth for service-to-service architectural dependencies.
Loads seed data from infra/service_dependency_registry.json. Composes
with UMHNodeRegistry and StateRegistry for cross-layer queries.

Phase 30. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from substrate.organism.service_dependency_graph import (
    ServiceDependency,
    ServiceDependencyTopology,
    ServiceNode,
)

logger = logging.getLogger(__name__)


def _find_registry_path() -> str:
    """Locate service_dependency_registry.json, checking UMH_ROOT and file-relative."""
    root = os.environ.get("UMH_ROOT", "/opt/OS")
    candidate = os.path.join(root, "infra", "service_dependency_registry.json")
    if os.path.exists(candidate):
        return candidate
    here = os.path.dirname(os.path.abspath(__file__))
    fallback = os.path.normpath(
        os.path.join(here, "..", "..", "infra", "service_dependency_registry.json")
    )
    return fallback


def _load_seed_data() -> tuple[list[ServiceNode], list[ServiceDependency]]:
    """Load service and dependency definitions from seed JSON."""
    registry_path = _find_registry_path()
    try:
        with open(registry_path) as f:
            data = json.load(f)
    except Exception:
        logger.debug("Could not load service dependency registry from %s", registry_path)
        return [], []

    services: list[ServiceNode] = []
    for entry in data.get("services", []):
        role = entry.get("service_role", "")
        if not role:
            continue
        services.append(ServiceNode.from_dict(entry))

    dependencies: list[ServiceDependency] = []
    for entry in data.get("dependencies", []):
        src = entry.get("source_service", "")
        tgt = entry.get("target_service", "")
        if not src or not tgt:
            continue
        dependencies.append(ServiceDependency.from_dict(entry))

    return services, dependencies


class ServiceDependencyRegistry:
    """Single source of truth for service dependency topology."""

    def __init__(self, seed: bool = True) -> None:
        self._services: dict[str, ServiceNode] = {}
        self._dependencies: list[ServiceDependency] = []
        if seed:
            services, deps = _load_seed_data()
            for svc in services:
                self._services[svc.service_role] = svc
            self._dependencies = deps

    def get_service(self, service_role: str) -> ServiceNode | None:
        return self._services.get(service_role)

    def list_services(self) -> list[ServiceNode]:
        return list(self._services.values())

    def dependencies_of(self, service_role: str) -> list[ServiceDependency]:
        """What does this service depend ON?"""
        return [d for d in self._dependencies if d.source_service == service_role]

    def dependents_of(self, service_role: str) -> list[ServiceDependency]:
        """What depends ON this service?"""
        return [d for d in self._dependencies if d.target_service == service_role]

    def services_for_node(self, node_id: str) -> list[ServiceNode]:
        return [s for s in self._services.values() if s.owner_node == node_id]

    def services_for_domain(self, domain: str) -> list[ServiceNode]:
        """All services that own a state domain."""
        return [
            s for s in self._services.values() if domain in s.state_domains
        ]

    def critical_services(self) -> list[ServiceNode]:
        return [s for s in self._services.values() if s.criticality == "critical"]

    def leaf_services(self) -> list[ServiceNode]:
        """Services with no downstream dependents."""
        has_dependents = {d.target_service for d in self._dependencies}
        return [
            s for s in self._services.values()
            if s.service_role not in has_dependents
        ]

    def register_service(self, service: ServiceNode) -> None:
        self._services[service.service_role] = service
        logger.info("Service registered: %s", service.service_role)

    def register_dependency(self, dep: ServiceDependency) -> None:
        self._dependencies.append(dep)
        logger.info(
            "Dependency registered: %s → %s",
            dep.source_service,
            dep.target_service,
        )

    def topology(self) -> ServiceDependencyTopology:
        return ServiceDependencyTopology(
            services=list(self._services.values()),
            dependencies=list(self._dependencies),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_count": len(self._services),
            "dependency_count": len(self._dependencies),
            "services": {
                r: s.to_dict() for r, s in self._services.items()
            },
            "dependencies": [d.to_dict() for d in self._dependencies],
        }
