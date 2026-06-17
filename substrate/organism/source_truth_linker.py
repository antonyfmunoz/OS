"""Source Truth Linker — cross-domain edge builder for the Reality Graph.

Creates typed edges linking projects ↔ docs ↔ repos ↔ projections ↔
work_packets ↔ approvals in the Reality Graph. Read-only — only adds
edges to the in-memory graph. Never mutates canonical reality directly;
any state mutation routes through CanonicalRealityWritePath.

Campaign 5.4. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Any

from substrate.organism.reality_graph import (
    RealityEntity,
    RealityEntityStatus,
    RealityEntityType,
    RealityGraph,
    RealityRelation,
    RealityRelationType,
)

logger = logging.getLogger(__name__)


class SourceTruthLinker:
    """Builds cross-domain edges in the Reality Graph.

    Composes ProjectRegistry and ProjectionSourceRegistry data into
    typed relationships that connect projects, repos, workspaces,
    devices, documents, projections, and infrastructure.
    """

    def __init__(
        self,
        reality_graph: RealityGraph,
        project_registry: Any | None = None,
        source_registry: Any | None = None,
    ) -> None:
        self._graph = reality_graph
        self._project_registry = project_registry
        self._source_registry = source_registry

    # ── Main Entry ────────────────────────────────────────────────────

    def link_all(self) -> int:
        """Run all linking passes. Returns total edges added."""
        count = 0
        count += self._link_projects_to_repos()
        count += self._link_projects_to_docs()
        count += self._link_repos_to_workspaces()
        count += self._link_services_to_devices()
        count += self._link_workspaces_to_devices()
        count += self._link_projects_to_projections()
        logger.debug("SourceTruthLinker: added %d edges", count)
        return count

    # ── Linking Passes ────────────────────────────────────────────────

    def _link_projects_to_repos(self) -> int:
        if self._project_registry is None:
            return 0
        count = 0
        projects = self._project_registry.list_projects()
        for proj in projects:
            proj_id = f"proj-{proj.project_id}"
            for repo_ref in proj.repositories:
                repo_id = f"repo-{repo_ref}"
                if self._graph._add_relation(RealityRelation(
                    source_id=proj_id,
                    target_id=repo_id,
                    relation_type=RealityRelationType.CONTAINS,
                )):
                    count += 1
        return count

    def _link_projects_to_docs(self) -> int:
        if self._source_registry is None or self._project_registry is None:
            return 0
        count = 0
        now = time.time()

        sources = []
        if hasattr(self._source_registry, "list_sources"):
            sources = self._source_registry.list_sources()
        elif hasattr(self._source_registry, "_sources"):
            sources = list(self._source_registry._sources.values())

        doc_source_types = {"GWS_DOCUMENT", "gws_document", "GOOGLE_DOCS", "google_docs",
                            "NOTION_DATABASE", "notion_database"}

        for source in sources:
            source_type = getattr(source, "source_type", None)
            if source_type and hasattr(source_type, "value"):
                type_val = source_type.value
            else:
                type_val = str(source_type) if source_type else ""

            if type_val not in doc_source_types:
                continue

            source_id = getattr(source, "id", "") or getattr(source, "source_id", "")
            name = getattr(source, "name", source_id)
            doc_entity_id = f"doc-{source_id}"

            doc_entity = RealityEntity(
                entity_id=doc_entity_id,
                entity_type=RealityEntityType.DOCUMENT,
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
            self._graph._add_entity(doc_entity)

            projection = getattr(source, "projection", "") or ""
            if projection:
                proj_def = self._project_registry.find_by_projection(projection)
                if proj_def:
                    if self._graph._add_relation(RealityRelation(
                        source_id=f"proj-{proj_def.project_id}",
                        target_id=doc_entity_id,
                        relation_type=RealityRelationType.DOCUMENTS,
                    )):
                        count += 1

        return count

    def _link_repos_to_workspaces(self) -> int:
        count = 0
        workspaces = self._graph.find_by_type(RealityEntityType.WORKSPACE)
        repos = self._graph.find_by_type(RealityEntityType.REPOSITORY)

        ws_repo_pairs: set[tuple[str, str]] = set()
        for rel in self._graph.all_relations():
            if rel.relation_type == RealityRelationType.CONTAINS:
                src = self._graph.get(rel.source_id)
                tgt = self._graph.get(rel.target_id)
                if (src and src.entity_type == RealityEntityType.WORKSPACE
                        and tgt and tgt.entity_type == RealityEntityType.REPOSITORY):
                    ws_repo_pairs.add((rel.source_id, rel.target_id))

        for ws in workspaces:
            for repo in repos:
                if ws.source_id and repo.source_id:
                    ws_name_lower = ws.name.lower()
                    repo_name_lower = repo.name.lower()
                    if (ws_name_lower in repo_name_lower or repo_name_lower in ws_name_lower):
                        pair = (ws.entity_id, repo.entity_id)
                        if pair not in ws_repo_pairs:
                            if self._graph._add_relation(RealityRelation(
                                source_id=ws.entity_id,
                                target_id=repo.entity_id,
                                relation_type=RealityRelationType.CONTAINS,
                            )):
                                ws_repo_pairs.add(pair)
                                count += 1

        return count

    def _link_services_to_devices(self) -> int:
        count = 0
        infra_entities = self._graph.find_by_type(RealityEntityType.INFRASTRUCTURE)
        for infra in infra_entities:
            host_device = infra.properties.get("host_device_id", "")
            if host_device:
                dev_id = f"dev-{host_device}"
                if self._graph.get(dev_id):
                    if self._graph._add_relation(RealityRelation(
                        source_id=infra.entity_id,
                        target_id=dev_id,
                        relation_type=RealityRelationType.RUNS_ON,
                    )):
                        count += 1
        return count

    def _link_workspaces_to_devices(self) -> int:
        count = 0
        workspaces = self._graph.find_by_type(RealityEntityType.WORKSPACE)
        for ws in workspaces:
            existing_devs = {
                n.entity_id
                for n in self._graph.neighbors(ws.entity_id, RealityRelationType.DEPLOYED_TO)
            }
            device_ids = ws.properties.get("device_ids", [])
            for dev_ref in device_ids:
                dev_id = f"dev-{dev_ref}"
                if dev_id not in existing_devs and self._graph.get(dev_id):
                    if self._graph._add_relation(RealityRelation(
                        source_id=ws.entity_id,
                        target_id=dev_id,
                        relation_type=RealityRelationType.DEPLOYED_TO,
                    )):
                        count += 1
        return count

    def _link_projects_to_projections(self) -> int:
        if self._project_registry is None:
            return 0
        count = 0
        now = time.time()
        for proj in self._project_registry.list_projects():
            if not proj.projection:
                continue
            projection_id = f"projection-{proj.projection}"
            proj_entity = RealityEntity(
                entity_id=projection_id,
                entity_type=RealityEntityType.PROJECTION,
                name=proj.projection,
                status=RealityEntityStatus.ACTIVE,
                properties={"source_project": proj.project_id},
                source_system="project_registry",
                source_id=proj.projection,
                last_observed=now,
            )
            self._graph._add_entity(proj_entity)
            if self._graph._add_relation(RealityRelation(
                source_id=f"proj-{proj.project_id}",
                target_id=projection_id,
                relation_type=RealityRelationType.OWNED_BY,
                properties={"relationship": "projection_of"},
            )):
                count += 1
        return count

    # ── Trace ─────────────────────────────────────────────────────────

    def trace_from_entity(self, entity_id: str) -> dict[str, list[dict[str, Any]]]:
        """BFS from entity, returns reachable entities grouped by relation type."""
        result: dict[str, list[dict[str, Any]]] = {}
        if self._graph.get(entity_id) is None:
            return result

        visited: set[str] = {entity_id}
        queue: deque[str] = deque([entity_id])

        while queue:
            current = queue.popleft()
            for rel in self._graph.all_relations():
                neighbor_id: str | None = None
                if rel.source_id == current and rel.target_id not in visited:
                    neighbor_id = rel.target_id
                elif rel.target_id == current and rel.source_id not in visited:
                    neighbor_id = rel.source_id

                if neighbor_id is None:
                    continue

                entity = self._graph.get(neighbor_id)
                if entity is None:
                    continue

                visited.add(neighbor_id)
                queue.append(neighbor_id)

                rel_key = rel.relation_type.value
                if rel_key not in result:
                    result[rel_key] = []
                result[rel_key].append(entity.to_dict())

        return result

    # ── Summary ───────────────────────────────────────────────────────

    def link_summary(self) -> dict[str, Any]:
        """Return edge counts by type, total linked, unlinked entities."""
        edge_counts: dict[str, int] = {}
        for rel in self._graph.all_relations():
            key = rel.relation_type.value
            edge_counts[key] = edge_counts.get(key, 0) + 1

        linked_ids: set[str] = set()
        for rel in self._graph.all_relations():
            linked_ids.add(rel.source_id)
            linked_ids.add(rel.target_id)

        all_ids = {e.entity_id for e in self._graph.all_entities()}
        unlinked = all_ids - linked_ids

        return {
            "edge_counts_by_type": edge_counts,
            "total_edges": self._graph.relation_count,
            "total_entities": self._graph.entity_count,
            "linked_entities": len(linked_ids & all_ids),
            "unlinked_entities": sorted(unlinked),
        }
