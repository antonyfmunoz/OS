"""Infrastructure Runtime — register and track system & institutional infrastructure.

Answers operator question #12: "What infrastructure exists because of our learning?"

Splits infrastructure into two layers:
  - System: runtimes, adapters, execution spine, template libraries
  - Institutional: companies, media engines, schools, capital structures

Links back through the full chain:
  Intent → Capability → Operationalization → Infrastructure

Gate 7 comes AFTER Gate 8 because infrastructure should not be registered
without evidence-grade lineage (which Gate 8 validates).

Gate 7 — Infrastructure Runtime. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_INFRA_DIR = os.path.join(_REPO_ROOT, "data", "umh", "infrastructure")
_INFRA_PATH = os.path.join(_INFRA_DIR, "infrastructure.jsonl")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class InfrastructureType(str, Enum):
    RUNTIME = "runtime"
    WORKFLOW_ENGINE = "workflow_engine"
    ADAPTER = "adapter"
    TEMPLATE_LIBRARY = "template_library"
    CAPABILITY_REGISTRY = "capability_registry"
    EXECUTION_SPINE = "execution_spine"
    GOVERNANCE_SYSTEM = "governance_system"
    COMPANY = "company"
    MEDIA_ENGINE = "media_engine"
    SCHOOL = "school"
    FOUNDATION = "foundation"
    CAPITAL_STRUCTURE = "capital_structure"


class InfrastructureHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    UNKNOWN = "unknown"


_SYSTEM_TYPES = {
    InfrastructureType.RUNTIME,
    InfrastructureType.WORKFLOW_ENGINE,
    InfrastructureType.ADAPTER,
    InfrastructureType.TEMPLATE_LIBRARY,
    InfrastructureType.CAPABILITY_REGISTRY,
    InfrastructureType.EXECUTION_SPINE,
    InfrastructureType.GOVERNANCE_SYSTEM,
}

_INSTITUTIONAL_TYPES = {
    InfrastructureType.COMPANY,
    InfrastructureType.MEDIA_ENGINE,
    InfrastructureType.SCHOOL,
    InfrastructureType.FOUNDATION,
    InfrastructureType.CAPITAL_STRUCTURE,
}


@dataclass
class InfrastructureEntity:
    infrastructure_id: str = field(default_factory=lambda: f"infra-{uuid4().hex[:8]}")
    name: str = ""
    infra_type: InfrastructureType = InfrastructureType.RUNTIME
    description: str = ""
    origin_capability_ids: list[str] = field(default_factory=list)
    operationalization_ids: list[str] = field(default_factory=list)
    health: InfrastructureHealth = InfrastructureHealth.UNKNOWN
    dependents: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def is_system(self) -> bool:
        return self.infra_type in _SYSTEM_TYPES

    @property
    def is_institutional(self) -> bool:
        return self.infra_type in _INSTITUTIONAL_TYPES

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["infra_type"] = self.infra_type.value
        d["health"] = self.health.value
        d["is_system"] = self.is_system
        d["is_institutional"] = self.is_institutional
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> InfrastructureEntity:
        d = dict(d)
        d.pop("is_system", None)
        d.pop("is_institutional", None)
        try:
            d["infra_type"] = InfrastructureType(d.get("infra_type", "runtime"))
        except ValueError:
            d["infra_type"] = InfrastructureType.RUNTIME
        try:
            d["health"] = InfrastructureHealth(d.get("health", "unknown"))
        except ValueError:
            d["health"] = InfrastructureHealth.UNKNOWN
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class InfrastructureRuntime:
    """Registry and lifecycle for system + institutional infrastructure."""

    def __init__(self, store_path: str = _INFRA_PATH) -> None:
        self._path = store_path
        self._lock = threading.Lock()
        self._entities: dict[str, InfrastructureEntity] = {}
        self._load()

    # ── Persistence ────────────────────────────────────────────────

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        ent = InfrastructureEntity.from_dict(d)
                        self._entities[ent.infrastructure_id] = ent
                    except (json.JSONDecodeError, TypeError, KeyError) as e:
                        logger.debug("Skip malformed JSONL line: %s", e)
        except OSError as e:
            logger.debug("Cannot read %s: %s", self._path, e)

    def _append(self, ent: InfrastructureEntity) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "a") as f:
            f.write(json.dumps(ent.to_dict(), default=str) + "\n")

    def _rewrite(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            for ent in self._entities.values():
                f.write(json.dumps(ent.to_dict(), default=str) + "\n")

    # ── Registry ───────────────────────────────────────────────────

    def register(
        self,
        name: str,
        infra_type: InfrastructureType,
        description: str = "",
        origin_capability_ids: list[str] | None = None,
        operationalization_ids: list[str] | None = None,
        health: InfrastructureHealth = InfrastructureHealth.UNKNOWN,
        dependencies: list[str] | None = None,
        evidence: list[str] | None = None,
    ) -> InfrastructureEntity:
        ent = InfrastructureEntity(
            name=name,
            infra_type=infra_type,
            description=description,
            origin_capability_ids=origin_capability_ids or [],
            operationalization_ids=operationalization_ids or [],
            health=health,
            dependencies=dependencies or [],
            evidence=evidence or [],
        )
        with self._lock:
            self._entities[ent.infrastructure_id] = ent
            self._append(ent)

        if dependencies:
            for dep_id in dependencies:
                dep = self._entities.get(dep_id)
                if dep and ent.infrastructure_id not in dep.dependents:
                    dep.dependents.append(ent.infrastructure_id)
            self._rewrite()

        logger.info("Registered infrastructure: %s (%s)", ent.name, ent.infrastructure_id)
        return ent

    def get(self, infrastructure_id: str) -> InfrastructureEntity | None:
        return self._entities.get(infrastructure_id)

    def list_entities(
        self,
        infra_type: InfrastructureType | None = None,
        health: InfrastructureHealth | None = None,
        system_only: bool = False,
        institutional_only: bool = False,
    ) -> list[InfrastructureEntity]:
        result = list(self._entities.values())
        if infra_type is not None:
            result = [e for e in result if e.infra_type == infra_type]
        if health is not None:
            result = [e for e in result if e.health == health]
        if system_only:
            result = [e for e in result if e.is_system]
        if institutional_only:
            result = [e for e in result if e.is_institutional]
        result.sort(key=lambda e: e.created_at, reverse=True)
        return result

    # ── Full lineage ───────────────────────────────────────────────

    def full_lineage(self, infrastructure_id: str) -> dict[str, Any]:
        """4-hop lineage: intent→capability→operationalization→infrastructure."""
        ent = self._entities.get(infrastructure_id)
        if ent is None:
            return {"error": f"infrastructure {infrastructure_id} not found"}

        lineage: dict[str, Any] = {
            "infrastructure_id": ent.infrastructure_id,
            "name": ent.name,
            "infra_type": ent.infra_type.value,
            "origin_capability_ids": ent.origin_capability_ids,
            "operationalization_ids": ent.operationalization_ids,
            "capabilities": [],
        }

        try:
            from substrate.organism.capability_runtime import CapabilityRuntime

            cr = CapabilityRuntime()
            for cap_id in ent.origin_capability_ids:
                cap = cr.get(cap_id)
                if cap:
                    lineage["capabilities"].append(
                        {
                            "capability_id": cap.capability_id,
                            "name": cap.name,
                            "origin_intent_id": cap.origin_intent_id,
                            "maturity": cap.maturity.value,
                        }
                    )
        except ImportError:
            logger.debug("CapabilityRuntime not available for lineage")

        return lineage

    # ── Health ─────────────────────────────────────────────────────

    def update_health(self, infrastructure_id: str, health: InfrastructureHealth) -> bool:
        ent = self._entities.get(infrastructure_id)
        if ent is None:
            return False
        with self._lock:
            ent.health = health
            ent.updated_at = time.time()
            self._rewrite()
        return True

    def health_check(self) -> dict[str, Any]:
        by_health: dict[str, int] = Counter(e.health.value for e in self._entities.values())
        failing = [
            e.to_dict() for e in self._entities.values() if e.health == InfrastructureHealth.FAILING
        ]
        degraded = [
            e.to_dict()
            for e in self._entities.values()
            if e.health == InfrastructureHealth.DEGRADED
        ]
        return {
            "total": len(self._entities),
            "by_health": dict(by_health),
            "failing": failing,
            "degraded": degraded,
            "healthy_rate": round(by_health.get("healthy", 0) / len(self._entities), 3)
            if self._entities
            else 0.0,
        }

    # ── Dependencies ───────────────────────────────────────────────

    def dependents_of(self, infrastructure_id: str) -> list[str]:
        ent = self._entities.get(infrastructure_id)
        return ent.dependents if ent else []

    def dependencies_of(self, infrastructure_id: str) -> list[str]:
        ent = self._entities.get(infrastructure_id)
        return ent.dependencies if ent else []

    def add_dependency(self, infrastructure_id: str, depends_on_id: str) -> bool:
        ent = self._entities.get(infrastructure_id)
        dep = self._entities.get(depends_on_id)
        if ent is None or dep is None:
            return False
        with self._lock:
            if depends_on_id not in ent.dependencies:
                ent.dependencies.append(depends_on_id)
            if infrastructure_id not in dep.dependents:
                dep.dependents.append(infrastructure_id)
            self._rewrite()
        return True

    # ── Sync from existing systems ─────────────────────────────────

    def sync_from_service_graph(self) -> int:
        """Populate from ServiceDependencyGraph — system infrastructure."""
        try:
            from substrate.organism.service_dependency_graph import (
                ServiceDependencyGraph,
            )

            sdg = ServiceDependencyGraph()
            services = sdg.list_services()
            created = 0
            existing_names = {e.name for e in self._entities.values()}
            for svc in services:
                name = svc.service_role if hasattr(svc, "service_role") else str(svc)
                if name not in existing_names:
                    self.register(
                        name=name,
                        infra_type=InfrastructureType.RUNTIME,
                        description=f"Service: {name}",
                        health=InfrastructureHealth.UNKNOWN,
                    )
                    created += 1
            return created
        except (ImportError, Exception) as e:
            logger.debug("sync_from_service_graph: %s", e)
            return 0

    def sync_from_node_registry(self) -> int:
        """Populate from UMHNodeRegistry — node infrastructure."""
        try:
            from substrate.organism.umh_node_registry import UMHNodeRegistry

            registry = UMHNodeRegistry()
            nodes = registry.list_nodes()
            created = 0
            existing_names = {e.name for e in self._entities.values()}
            for node in nodes:
                name = node.node_id if hasattr(node, "node_id") else str(node)
                if name not in existing_names:
                    self.register(
                        name=name,
                        infra_type=InfrastructureType.RUNTIME,
                        description=f"Node: {name}",
                        health=InfrastructureHealth.UNKNOWN,
                    )
                    created += 1
            return created
        except (ImportError, Exception) as e:
            logger.debug("sync_from_node_registry: %s", e)
            return 0

    # ── Summary ────────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        by_type: dict[str, int] = Counter(e.infra_type.value for e in self._entities.values())
        by_health: dict[str, int] = Counter(e.health.value for e in self._entities.values())
        system_count = sum(1 for e in self._entities.values() if e.is_system)
        institutional_count = sum(1 for e in self._entities.values() if e.is_institutional)
        return {
            "total_infrastructure": len(self._entities),
            "system_count": system_count,
            "institutional_count": institutional_count,
            "by_type": dict(by_type),
            "by_health": dict(by_health),
        }
