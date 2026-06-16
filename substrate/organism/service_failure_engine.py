"""Service Failure Engine — computes failure impact across service graph.

Given a service failure, computes direct and transitive impact.
Identifies critical path services whose failure would cascade widest.

No repair, no failover, no restart authority. Analysis only.

Phase 30. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Any

from substrate.organism.service_dependency_graph import (
    FailureImpact,
    ServiceHealthImpact,
)

logger = logging.getLogger(__name__)


class ServiceFailureEngine:
    """Computes failure impact and critical path across the service graph."""

    def __init__(
        self,
        registry: Any | None = None,
        state_registry: Any | None = None,
    ) -> None:
        self._registry = registry
        self._state_registry = state_registry

    @property
    def registry(self) -> Any:
        if self._registry is None:
            from substrate.organism.service_dependency_registry import (
                ServiceDependencyRegistry,
            )

            self._registry = ServiceDependencyRegistry()
        return self._registry

    @property
    def state_registry(self) -> Any:
        if self._state_registry is None:
            from substrate.organism.state_registry import StateRegistry

            self._state_registry = StateRegistry()
        return self._state_registry

    def failure_impact(self, service_role: str) -> FailureImpact:
        """Compute what breaks if service_role goes down."""
        direct_deps = self.registry.dependents_of(service_role)
        direct = [d.source_service for d in direct_deps]

        visited: set[str] = set(direct)
        transitive: list[str] = []
        queue: deque[str] = deque(direct)

        while queue:
            svc = queue.popleft()
            for dep in self.registry.dependents_of(svc):
                if dep.source_service not in visited:
                    visited.add(dep.source_service)
                    transitive.append(dep.source_service)
                    queue.append(dep.source_service)

        affected_domains: set[str] = set()
        for svc_role in visited:
            svc_node = self.registry.get_service(svc_role)
            if svc_node and svc_node.state_domains:
                affected_domains.update(svc_node.state_domains)

        failed_node = self.registry.get_service(service_role)
        if failed_node and failed_node.state_domains:
            affected_domains.update(failed_node.state_domains)

        blast_radius = len(visited)
        total = len(self.registry.list_services())
        severity = self._classify_severity(blast_radius, total)

        return FailureImpact(
            failed_service=service_role,
            directly_affected=direct,
            transitively_affected=transitive,
            affected_state_domains=sorted(affected_domains),
            blast_radius=blast_radius,
            severity=severity,
        )

    def critical_path(self) -> list[dict[str, Any]]:
        """Services ranked by blast radius, highest first."""
        results: list[dict[str, Any]] = []
        for svc in self.registry.list_services():
            impact = self.failure_impact(svc.service_role)
            results.append({
                "service_role": svc.service_role,
                "criticality": svc.criticality,
                "blast_radius": impact.blast_radius,
                "direct_dependents": len(impact.directly_affected),
                "transitive_dependents": len(impact.transitively_affected),
            })
        results.sort(key=lambda x: x["blast_radius"], reverse=True)
        return results

    def leaf_services(self) -> list[str]:
        """Services with no downstream dependents."""
        return [s.service_role for s in self.registry.leaf_services()]

    def service_health_map(self) -> dict[str, str]:
        """Map each service to its health impact status."""
        health: dict[str, str] = {}
        for svc in self.registry.list_services():
            deps = self.registry.dependencies_of(svc.service_role)
            if not deps:
                health[svc.service_role] = ServiceHealthImpact.UNAFFECTED.value
                continue

            has_required = any(d.strength == "required" for d in deps)
            has_degraded = any(d.strength == "degraded" for d in deps)

            if has_required:
                health[svc.service_role] = ServiceHealthImpact.BLOCKED.value
            elif has_degraded:
                health[svc.service_role] = ServiceHealthImpact.DEGRADED.value
            else:
                health[svc.service_role] = ServiceHealthImpact.UNAFFECTED.value

        return health

    def organism_health(self) -> dict[str, Any]:
        """Summary health of the service dependency graph."""
        services = self.registry.list_services()
        deps = self.registry.topology().dependencies
        critical = self.registry.critical_services()
        leaves = self.registry.leaf_services()

        max_blast = 0
        highest_risk = ""
        for svc in services:
            impact = self.failure_impact(svc.service_role)
            if impact.blast_radius > max_blast:
                max_blast = impact.blast_radius
                highest_risk = svc.service_role

        return {
            "total_services": len(services),
            "total_dependencies": len(deps),
            "critical_count": len(critical),
            "leaf_count": len(leaves),
            "max_blast_radius": max_blast,
            "highest_risk_service": highest_risk,
        }

    def _classify_severity(self, blast_radius: int, total: int) -> str:
        if total == 0:
            return "low"
        ratio = blast_radius / total
        if ratio > 0.5:
            return "critical"
        if ratio > 0.3:
            return "high"
        if blast_radius > 0:
            return "medium"
        return "low"
