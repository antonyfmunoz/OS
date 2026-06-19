"""Reality Graph — canonical operator-world graph for UMH.

RealityGraph is the operator-world graph, NOT a replacement for existing
topology graphs. Existing graphs (WorkspaceRuntimeGraph, UMHNodeTopology,
StateAuthorityGraph, ServiceDependencyGraph) remain authorities over their
domains. RealityGraph only composes, links, resolves, and exposes
cross-domain relationships.

RealityGraph never mutates canonical reality directly. Any mutation routes
through CanonicalRealityWritePath. RealityGraph reflects mutations after
they happen — it never initiates them.

Campaign 5.0. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT") or "/opt/OS"


# ── Types ─────────────────────────────────────────────────────────────────


class RealityEntityType(str, Enum):
    PROJECT = "project"
    REPOSITORY = "repository"
    WORKSPACE = "workspace"
    DEVICE = "device"
    DOCUMENT = "document"
    SERVICE = "service"
    PROJECTION = "projection"
    BRANCH = "branch"
    WORK_PACKET = "work_packet"
    APPROVAL = "approval"
    DELEGATION_MISSION = "delegation_mission"
    CAPABILITY = "capability"
    INFRASTRUCTURE = "infrastructure"
    FILE = "file"
    ARTIFACT = "artifact"
    DECISION = "decision"


class RealityRelationType(str, Enum):
    CONTAINS = "contains"
    RUNS_ON = "runs_on"
    BUILT_FROM = "built_from"
    OWNED_BY = "owned_by"
    DEPLOYED_TO = "deployed_to"
    DOCUMENTS = "documents"
    DEPENDS_ON = "depends_on"
    ACTIVE_IN = "active_in"
    PRODUCED_BY = "produced_by"
    SUPPORTS = "supports"
    CREATED = "created"
    APPROVED_BY = "approved_by"
    SUPERSEDES = "supersedes"
    IMPLEMENTS = "implements"
    ENABLES = "enables"
    COMPOSES = "composes"
    CONFLICTS_WITH = "conflicts_with"


class RealityEntityStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class RealityEntity:
    entity_id: str
    entity_type: RealityEntityType
    name: str
    status: RealityEntityStatus = RealityEntityStatus.UNKNOWN
    properties: dict[str, Any] = field(default_factory=dict)
    source_system: str = ""
    source_id: str = ""
    last_observed: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "name": self.name,
            "status": self.status.value,
            "properties": self.properties,
            "source_system": self.source_system,
            "source_id": self.source_id,
            "last_observed": self.last_observed,
        }


@dataclass
class RealityRelation:
    source_id: str
    target_id: str
    relation_type: RealityRelationType
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "properties": self.properties,
        }


# ── Reality Graph ─────────────────────────────────────────────────────────


class RealityGraph:
    """Read-only composition layer over existing UMH topology systems."""

    def __init__(self) -> None:
        self._entities: dict[str, RealityEntity] = {}
        self._relations: list[RealityRelation] = []
        self._built_at: float = 0.0

    @property
    def entity_count(self) -> int:
        return len(self._entities)

    @property
    def relation_count(self) -> int:
        return len(self._relations)

    @property
    def built_at(self) -> float:
        return self._built_at

    # ── Entity Access ─────────────────────────────────────────────────

    def get(self, entity_id: str) -> RealityEntity | None:
        return self._entities.get(entity_id)

    def find_by_type(self, entity_type: RealityEntityType) -> list[RealityEntity]:
        return [e for e in self._entities.values() if e.entity_type == entity_type]

    def find_by_name(self, name: str) -> list[RealityEntity]:
        lower = name.lower()
        exact = [e for e in self._entities.values() if e.name.lower() == lower]
        if exact:
            return exact
        return [e for e in self._entities.values() if lower in e.name.lower()]

    def find_by_property(self, key: str, value: Any) -> list[RealityEntity]:
        return [e for e in self._entities.values() if e.properties.get(key) == value]

    def all_entities(self) -> list[RealityEntity]:
        return list(self._entities.values())

    def all_relations(self) -> list[RealityRelation]:
        return list(self._relations)

    # ── Graph Traversal ───────────────────────────────────────────────

    def neighbors(
        self,
        entity_id: str,
        relation_type: RealityRelationType | None = None,
    ) -> list[RealityEntity]:
        result: list[RealityEntity] = []
        seen: set[str] = set()
        for rel in self._relations:
            target_id: str | None = None
            if rel.source_id == entity_id:
                target_id = rel.target_id
            elif rel.target_id == entity_id:
                target_id = rel.source_id
            if target_id is None:
                continue
            if relation_type is not None and rel.relation_type != relation_type:
                continue
            if target_id not in seen:
                entity = self._entities.get(target_id)
                if entity is not None:
                    result.append(entity)
                    seen.add(target_id)
        return result

    def path(self, from_id: str, to_id: str) -> list[RealityRelation]:
        if from_id == to_id:
            return []
        if from_id not in self._entities or to_id not in self._entities:
            return []

        adj: dict[str, list[tuple[str, RealityRelation]]] = {}
        for rel in self._relations:
            adj.setdefault(rel.source_id, []).append((rel.target_id, rel))
            adj.setdefault(rel.target_id, []).append((rel.source_id, rel))

        visited: set[str] = {from_id}
        queue: deque[tuple[str, list[RealityRelation]]] = deque([(from_id, [])])
        while queue:
            current, trail = queue.popleft()
            for neighbor_id, rel in adj.get(current, []):
                if neighbor_id in visited:
                    continue
                new_trail = trail + [rel]
                if neighbor_id == to_id:
                    return new_trail
                visited.add(neighbor_id)
                queue.append((neighbor_id, new_trail))
        return []

    def subgraph(self, entity_id: str, depth: int = 2) -> "RealityGraph":
        if entity_id not in self._entities:
            return RealityGraph()

        collected: set[str] = {entity_id}
        frontier: set[str] = {entity_id}
        for _ in range(depth):
            next_frontier: set[str] = set()
            for eid in frontier:
                for neighbor in self.neighbors(eid):
                    if neighbor.entity_id not in collected:
                        collected.add(neighbor.entity_id)
                        next_frontier.add(neighbor.entity_id)
            frontier = next_frontier
            if not frontier:
                break

        sub = RealityGraph()
        for eid in collected:
            entity = self._entities.get(eid)
            if entity is not None:
                sub._entities[eid] = entity
        for rel in self._relations:
            if rel.source_id in collected and rel.target_id in collected:
                sub._relations.append(rel)
        sub._built_at = self._built_at
        return sub

    # ── Mutation (internal only — never exposed) ──────────────────────

    def _add_entity(self, entity: RealityEntity) -> bool:
        if entity.entity_id in self._entities:
            existing = self._entities[entity.entity_id]
            if entity.last_observed > existing.last_observed:
                self._entities[entity.entity_id] = entity
                return True
            return False
        self._entities[entity.entity_id] = entity
        return True

    def _add_relation(self, relation: RealityRelation) -> bool:
        for existing in self._relations:
            if (
                existing.source_id == relation.source_id
                and existing.target_id == relation.target_id
                and existing.relation_type == relation.relation_type
            ):
                return False
        self._relations.append(relation)
        return True

    # ── Seeding from JSON Registries ──────────────────────────────────

    @classmethod
    def seed_from_registries(
        cls,
        device_registry_path: str | None = None,
        workspace_registry_path: str | None = None,
        project_registry_path: str | None = None,
    ) -> "RealityGraph":
        graph = cls()
        now = time.time()

        device_path = device_registry_path or os.path.join(_ROOT, "infra", "device_registry.json")
        workspace_path = workspace_registry_path or os.path.join(_ROOT, "infra", "workspace_registry.json")
        project_path = project_registry_path or os.path.join(_ROOT, "infra", "project_registry.json")

        graph._seed_devices(device_path, now)
        graph._seed_workspaces(workspace_path, now)
        graph._seed_projects(project_path, now)

        graph._built_at = now
        return graph

    def _seed_devices(self, path: str, now: float) -> int:
        count = 0
        try:
            with open(path, "r") as f:
                devices = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.debug("Could not load device registry %s: %s", path, exc)
            return 0

        for dev in devices:
            entity = RealityEntity(
                entity_id=f"dev-{dev['id']}",
                entity_type=RealityEntityType.DEVICE,
                name=dev.get("display_name", dev["id"]),
                status=RealityEntityStatus.ACTIVE,
                properties={
                    k: v for k, v in dev.items()
                    if k not in ("id", "display_name")
                },
                source_system="device_registry",
                source_id=dev["id"],
                last_observed=now,
            )
            if self._add_entity(entity):
                count += 1
        logger.debug("Seeded %d device entities", count)
        return count

    def _seed_workspaces(self, path: str, now: float) -> int:
        count = 0
        try:
            with open(path, "r") as f:
                workspaces = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.debug("Could not load workspace registry %s: %s", path, exc)
            return 0

        for ws in workspaces:
            ws_id = f"ws-{ws['workspace_id']}"
            entity = RealityEntity(
                entity_id=ws_id,
                entity_type=RealityEntityType.WORKSPACE,
                name=ws.get("name", ws["workspace_id"]),
                status=RealityEntityStatus.ACTIVE,
                properties={
                    "workspace_type": ws.get("workspace_type", ""),
                    "primary_umh_node_id": ws.get("primary_umh_node_id", ""),
                },
                source_system="workspace_registry",
                source_id=ws["workspace_id"],
                last_observed=now,
            )
            if self._add_entity(entity):
                count += 1

            for repo in ws.get("repositories", []):
                repo_id = f"repo-{repo['repository_id']}"
                repo_entity = RealityEntity(
                    entity_id=repo_id,
                    entity_type=RealityEntityType.REPOSITORY,
                    name=repo.get("name", repo["repository_id"]),
                    status=RealityEntityStatus.ACTIVE,
                    properties={
                        "path": repo.get("path", ""),
                        "branch": repo.get("branch", "main"),
                    },
                    source_system="workspace_registry",
                    source_id=repo["repository_id"],
                    last_observed=now,
                )
                if self._add_entity(repo_entity):
                    count += 1
                self._add_relation(RealityRelation(
                    source_id=ws_id,
                    target_id=repo_id,
                    relation_type=RealityRelationType.CONTAINS,
                ))

            for device_id in ws.get("device_ids", []):
                self._add_relation(RealityRelation(
                    source_id=ws_id,
                    target_id=f"dev-{device_id}",
                    relation_type=RealityRelationType.DEPLOYED_TO,
                ))

        logger.debug("Seeded %d workspace/repo entities", count)
        return count

    def _seed_projects(self, path: str, now: float) -> int:
        count = 0
        try:
            with open(path, "r") as f:
                projects = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.debug("Could not load project registry %s: %s", path, exc)
            return 0

        for proj in projects:
            proj_id = f"proj-{proj['project_id']}"
            entity = RealityEntity(
                entity_id=proj_id,
                entity_type=RealityEntityType.PROJECT,
                name=proj.get("name", proj["project_id"]),
                status=RealityEntityStatus.ACTIVE if proj.get("status") == "active" else RealityEntityStatus.INACTIVE,
                properties={
                    k: v for k, v in proj.items()
                    if k not in ("project_id", "name", "status", "repositories", "infrastructure", "owner_device_ids")
                },
                source_system="project_registry",
                source_id=proj["project_id"],
                last_observed=now,
            )
            if self._add_entity(entity):
                count += 1

            for repo_ref in proj.get("repositories", []):
                self._add_relation(RealityRelation(
                    source_id=proj_id,
                    target_id=f"repo-{repo_ref}",
                    relation_type=RealityRelationType.CONTAINS,
                ))

            for infra_ref in proj.get("infrastructure", []):
                self._add_relation(RealityRelation(
                    source_id=proj_id,
                    target_id=f"infra-{infra_ref}",
                    relation_type=RealityRelationType.DEPENDS_ON,
                ))

            for device_ref in proj.get("owner_device_ids", []):
                self._add_relation(RealityRelation(
                    source_id=proj_id,
                    target_id=f"dev-{device_ref}",
                    relation_type=RealityRelationType.DEPLOYED_TO,
                ))

            if proj.get("projection"):
                self._add_relation(RealityRelation(
                    source_id=proj_id,
                    target_id=f"proj-{proj['projection']}",
                    relation_type=RealityRelationType.OWNED_BY,
                    properties={"relationship": "projection_of"},
                ))

        logger.debug("Seeded %d project entities", count)
        return count

    # ── Ingest from subsystems ────────────────────────────────────────

    def ingest_from_node_topology(self, topology: Any) -> int:
        count = 0
        now = time.time()
        nodes = []
        if hasattr(topology, "list_nodes"):
            nodes = topology.list_nodes()
        elif hasattr(topology, "_nodes"):
            nodes = list(topology._nodes.values())

        for node in nodes:
            node_id = getattr(node, "node_id", "") or getattr(node, "id", "")
            device_id = getattr(node, "device_id", node_id)
            entity = RealityEntity(
                entity_id=f"dev-{device_id}",
                entity_type=RealityEntityType.DEVICE,
                name=getattr(node, "hostname", device_id),
                status=RealityEntityStatus.ACTIVE,
                properties={
                    "node_id": node_id,
                    "roles": [r.value if hasattr(r, "value") else str(r) for r in getattr(node, "roles", [])],
                    "purpose": getattr(node, "purpose", ""),
                },
                source_system="umh_node_topology",
                source_id=node_id,
                last_observed=now,
            )
            if self._add_entity(entity):
                count += 1
        return count

    def ingest_from_workspace_graph(self, graph: Any) -> int:
        count = 0
        now = time.time()
        workspaces = []
        if hasattr(graph, "list_workspaces"):
            workspaces = graph.list_workspaces()
        elif hasattr(graph, "_workspaces"):
            workspaces = list(graph._workspaces.values())

        for ws in workspaces:
            ws_id_raw = getattr(ws, "workspace_id", "")
            ws_entity_id = f"ws-{ws_id_raw}"
            entity = RealityEntity(
                entity_id=ws_entity_id,
                entity_type=RealityEntityType.WORKSPACE,
                name=getattr(ws, "name", ws_id_raw),
                status=RealityEntityStatus.ACTIVE,
                properties={"workspace_type": getattr(ws, "workspace_type", "")},
                source_system="workspace_runtime_graph",
                source_id=ws_id_raw,
                last_observed=now,
            )
            if self._add_entity(entity):
                count += 1

            for repo in getattr(ws, "repositories", []):
                repo_id_raw = getattr(repo, "repository_id", "")
                repo_entity_id = f"repo-{repo_id_raw}"
                repo_entity = RealityEntity(
                    entity_id=repo_entity_id,
                    entity_type=RealityEntityType.REPOSITORY,
                    name=getattr(repo, "name", repo_id_raw),
                    status=RealityEntityStatus.ACTIVE,
                    source_system="workspace_runtime_graph",
                    source_id=repo_id_raw,
                    last_observed=now,
                )
                if self._add_entity(repo_entity):
                    count += 1
                self._add_relation(RealityRelation(
                    source_id=ws_entity_id,
                    target_id=repo_entity_id,
                    relation_type=RealityRelationType.CONTAINS,
                ))
        return count

    def ingest_from_source_registry(self, registry: Any) -> int:
        count = 0
        now = time.time()
        sources = []
        if hasattr(registry, "list_sources"):
            sources = registry.list_sources()
        elif hasattr(registry, "_sources"):
            sources = list(registry._sources.values())

        for source in sources:
            source_type = getattr(source, "source_type", None)
            source_id = getattr(source, "id", "") or getattr(source, "source_id", "")
            name = getattr(source, "name", source_id)

            if source_type and hasattr(source_type, "value"):
                type_val = source_type.value
            else:
                type_val = str(source_type) if source_type else ""

            if type_val in ("GITHUB_REPO", "github_repo"):
                entity_type = RealityEntityType.REPOSITORY
                eid = f"repo-{source_id}"
            else:
                entity_type = RealityEntityType.DOCUMENT
                eid = f"doc-{source_id}"

            entity = RealityEntity(
                entity_id=eid,
                entity_type=entity_type,
                name=name,
                status=RealityEntityStatus.ACTIVE,
                properties={
                    "url": getattr(source, "url", ""),
                    "source_type": type_val,
                },
                source_system="projection_source_registry",
                source_id=source_id,
                last_observed=now,
            )
            if self._add_entity(entity):
                count += 1
        return count

    def ingest_from_delegation_runtime(self, runtime: Any) -> int:
        count = 0
        now = time.time()
        missions = []
        if hasattr(runtime, "list_missions"):
            missions = runtime.list_missions()
        elif hasattr(runtime, "_missions"):
            missions = list(runtime._missions.values())

        for mission in missions:
            m_id = getattr(mission, "mission_id", "") or getattr(mission, "id", "")
            status_raw = getattr(mission, "status", "unknown")
            status_val = status_raw.value if hasattr(status_raw, "value") else str(status_raw)

            entity = RealityEntity(
                entity_id=f"mission-{m_id}",
                entity_type=RealityEntityType.DELEGATION_MISSION,
                name=getattr(mission, "title", m_id),
                status=RealityEntityStatus.ACTIVE if status_val not in ("completed", "cancelled", "failed") else RealityEntityStatus.INACTIVE,
                properties={
                    "mission_status": status_val,
                    "intent": getattr(mission, "intent", ""),
                },
                source_system="delegation_runtime",
                source_id=m_id,
                last_observed=now,
            )
            if self._add_entity(entity):
                count += 1
        return count

    def ingest_from_infrastructure_runtime(self, runtime: Any) -> int:
        count = 0
        now = time.time()
        entities = []
        if hasattr(runtime, "list_entities"):
            entities = runtime.list_entities()
        elif hasattr(runtime, "_entities"):
            entities = list(runtime._entities.values())

        for infra in entities:
            i_id = getattr(infra, "entity_id", "") or getattr(infra, "id", "")
            health = getattr(infra, "health", None)
            health_val = health.value if hasattr(health, "value") else str(health) if health else "unknown"

            status = RealityEntityStatus.ACTIVE
            if health_val in ("degraded",):
                status = RealityEntityStatus.DEGRADED
            elif health_val in ("offline", "unknown"):
                status = RealityEntityStatus.UNKNOWN

            entity = RealityEntity(
                entity_id=f"infra-{i_id}",
                entity_type=RealityEntityType.INFRASTRUCTURE,
                name=getattr(infra, "name", i_id),
                status=status,
                properties={
                    "infra_type": getattr(infra, "infra_type", ""),
                    "health": health_val,
                },
                source_system="infrastructure_runtime",
                source_id=i_id,
                last_observed=now,
            )
            if self._add_entity(entity):
                count += 1
        return count

    def ingest_from_capability_runtime(self, runtime: Any) -> int:
        count = 0
        now = time.time()
        capabilities = []
        if hasattr(runtime, "list_capabilities"):
            capabilities = runtime.list_capabilities()
        elif hasattr(runtime, "_capabilities"):
            capabilities = list(runtime._capabilities.values())

        for cap in capabilities:
            c_id = getattr(cap, "capability_id", "") or getattr(cap, "id", "")
            entity = RealityEntity(
                entity_id=f"cap-{c_id}",
                entity_type=RealityEntityType.CAPABILITY,
                name=getattr(cap, "name", c_id),
                status=RealityEntityStatus.ACTIVE,
                properties={
                    "maturity": getattr(cap, "maturity", ""),
                    "evidence_count": getattr(cap, "evidence_count", 0),
                },
                source_system="capability_runtime",
                source_id=c_id,
                last_observed=now,
            )
            if self._add_entity(entity):
                count += 1
        return count

    def ingest_from_artifact_registry(self, registry: Any) -> int:
        count = 0
        now = time.time()
        artifacts = []
        if hasattr(registry, "list_artifacts"):
            artifacts = registry.list_artifacts()
        elif hasattr(registry, "_artifacts"):
            artifacts = list(registry._artifacts.values())

        for artifact in artifacts:
            a_id = getattr(artifact, "artifact_id", "")
            if not a_id:
                continue

            entity = RealityEntity(
                entity_id=f"art-{a_id}",
                entity_type=RealityEntityType.ARTIFACT,
                name=getattr(artifact, "name", a_id),
                status=RealityEntityStatus.ACTIVE if getattr(artifact, "status", "") == "active" else RealityEntityStatus.INACTIVE,
                properties={
                    "artifact_type": getattr(artifact, "artifact_type", ""),
                    "source_path": getattr(artifact, "source_path", ""),
                    "source_system": getattr(artifact, "source_system", ""),
                },
                source_system="artifact_registry",
                source_id=a_id,
                last_observed=now,
            )
            if self._add_entity(entity):
                count += 1

            for ref in getattr(artifact, "entity_refs", []):
                self._add_relation(RealityRelation(
                    source_id=f"art-{a_id}",
                    target_id=ref,
                    relation_type=RealityRelationType.DOCUMENTS,
                ))
        return count

    # ── Summary ───────────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        for entity in self._entities.values():
            by_type[entity.entity_type.value] = by_type.get(entity.entity_type.value, 0) + 1

        by_relation: dict[str, int] = {}
        for rel in self._relations:
            by_relation[rel.relation_type.value] = by_relation.get(rel.relation_type.value, 0) + 1

        return {
            "entity_count": self.entity_count,
            "relation_count": self.relation_count,
            "entities_by_type": by_type,
            "relations_by_type": by_relation,
            "built_at": self._built_at,
        }
