"""State Authority Graph — canonical state domain authority models.

Declares which node is authoritative for each state domain in the
UMH organism. State is modeled by DOMAIN (memory, governance, runtime),
not by file or service. Domains are reality. Files are implementation.

No replication. No synchronization. No consensus. Observation only.

Phase 29. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class StateDomain(str, Enum):
    MEMORY = "memory"
    GOVERNANCE = "governance"
    RUNTIME = "runtime"
    WORKSPACE = "workspace"
    SESSION = "session"
    OBSERVATION = "observation"
    EXECUTION = "execution"
    PROOF = "proof"
    REALITY = "reality"
    CONFIGURATION = "configuration"


class StateAuthorityLevel(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    CACHE = "cache"
    MIRROR = "mirror"
    DERIVED = "derived"


class StateCoherenceStatus(str, Enum):
    COHERENT = "coherent"
    STALE = "stale"
    DRIFTED = "drifted"
    UNKNOWN = "unknown"


@dataclass
class StateAuthority:
    domain: str
    node_id: str = ""
    authority_level: str = "primary"
    storage_location: str = ""
    service_owner: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "node_id": self.node_id,
            "authority_level": self.authority_level,
            "storage_location": self.storage_location,
            "service_owner": self.service_owner,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StateAuthority:
        return cls(
            domain=data.get("domain", ""),
            node_id=data.get("node_id", ""),
            authority_level=data.get("authority_level", "primary"),
            storage_location=data.get("storage_location", ""),
            service_owner=data.get("service_owner", ""),
        )


@dataclass
class StateDomainStatus:
    domain: str
    authority_node: str = ""
    secondary_nodes: list[str] = field(default_factory=list)
    status: str = "unknown"
    last_updated: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "authority_node": self.authority_node,
            "secondary_nodes": self.secondary_nodes,
            "status": self.status,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StateDomainStatus:
        return cls(
            domain=data.get("domain", ""),
            authority_node=data.get("authority_node", ""),
            secondary_nodes=data.get("secondary_nodes", []),
            status=data.get("status", "unknown"),
            last_updated=data.get("last_updated", 0.0),
        )


@dataclass
class OrganismStateGraph:
    topology_id: str = field(default_factory=lambda: f"osg-{uuid4().hex[:12]}")
    organism_id: str = "umh"
    domains: list[StateDomainStatus] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_id": self.topology_id,
            "organism_id": self.organism_id,
            "domains": [d.to_dict() for d in self.domains],
            "domain_count": len(self.domains),
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OrganismStateGraph:
        return cls(
            topology_id=data.get("topology_id", ""),
            organism_id=data.get("organism_id", "umh"),
            domains=[
                StateDomainStatus.from_dict(d)
                for d in data.get("domains", [])
            ],
            generated_at=data.get("generated_at", 0.0),
        )
