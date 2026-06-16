"""Service Dependency Graph — canonical service dependency models.

Models service-to-service dependencies within the UMH organism.
Dependencies are architectural (Service→Service), not implementation
(file→file). Services reference UMHServiceRole from Phase 28.

No execution, no orchestration, no failover, no restart authority.
Observation and topology only.

Phase 30. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class DependencyStrength(str, Enum):
    REQUIRED = "required"
    DEGRADED = "degraded"
    OPTIONAL = "optional"


class ServiceCriticality(str, Enum):
    CRITICAL = "critical"
    CORE = "core"
    SUPPORTING = "supporting"
    OPTIONAL = "optional"


class ServiceHealthImpact(str, Enum):
    BLOCKED = "blocked"
    DEGRADED = "degraded"
    UNAFFECTED = "unaffected"
    UNKNOWN = "unknown"


@dataclass
class ServiceDependency:
    """A single directed edge: source depends on target."""

    source_service: str
    target_service: str = ""
    strength: str = "degraded"
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_service": self.source_service,
            "target_service": self.target_service,
            "strength": self.strength,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServiceDependency:
        return cls(
            source_service=data.get("source_service", ""),
            target_service=data.get("target_service", ""),
            strength=data.get("strength", "degraded"),
            description=data.get("description", ""),
        )


@dataclass
class ServiceNode:
    """Architectural identity of a service in the dependency graph."""

    service_role: str
    description: str = ""
    criticality: str = "supporting"
    owner_node: str = ""
    state_domains: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_role": self.service_role,
            "description": self.description,
            "criticality": self.criticality,
            "owner_node": self.owner_node,
            "state_domains": self.state_domains,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServiceNode:
        return cls(
            service_role=data.get("service_role", ""),
            description=data.get("description", ""),
            criticality=data.get("criticality", "supporting"),
            owner_node=data.get("owner_node", ""),
            state_domains=data.get("state_domains", []),
        )


@dataclass
class FailureImpact:
    """What breaks if a service goes down."""

    failed_service: str
    directly_affected: list[str] = field(default_factory=list)
    transitively_affected: list[str] = field(default_factory=list)
    affected_state_domains: list[str] = field(default_factory=list)
    blast_radius: int = 0
    severity: str = "low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "failed_service": self.failed_service,
            "directly_affected": self.directly_affected,
            "transitively_affected": self.transitively_affected,
            "affected_state_domains": self.affected_state_domains,
            "blast_radius": self.blast_radius,
            "severity": self.severity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FailureImpact:
        return cls(
            failed_service=data.get("failed_service", ""),
            directly_affected=data.get("directly_affected", []),
            transitively_affected=data.get("transitively_affected", []),
            affected_state_domains=data.get("affected_state_domains", []),
            blast_radius=data.get("blast_radius", 0),
            severity=data.get("severity", "low"),
        )


@dataclass
class ServiceDependencyTopology:
    """Full service dependency graph snapshot."""

    topology_id: str = field(default_factory=lambda: f"sdt-{uuid4().hex[:12]}")
    organism_id: str = "umh"
    services: list[ServiceNode] = field(default_factory=list)
    dependencies: list[ServiceDependency] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_id": self.topology_id,
            "organism_id": self.organism_id,
            "services": [s.to_dict() for s in self.services],
            "dependencies": [d.to_dict() for d in self.dependencies],
            "service_count": len(self.services),
            "dependency_count": len(self.dependencies),
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServiceDependencyTopology:
        return cls(
            topology_id=data.get("topology_id", ""),
            organism_id=data.get("organism_id", "umh"),
            services=[
                ServiceNode.from_dict(s) for s in data.get("services", [])
            ],
            dependencies=[
                ServiceDependency.from_dict(d)
                for d in data.get("dependencies", [])
            ],
            generated_at=data.get("generated_at", 0.0),
        )
