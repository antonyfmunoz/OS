"""UMH Version Coherence Engine — detects version drift across nodes.

All UMH nodes should run the same substrate version. Capability drift
is expected (VPS has governance, Beast has electron build). Version
drift is detected and surfaced so the organism knows when coordination
is unsafe.

Phase 28. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from substrate.organism.umh_node_registry import UMHNodeRegistry
from substrate.organism.umh_node_topology import (
    UMHNodeStatus,
    UMHVersionInfo,
    UMHVersionStatus,
)

logger = logging.getLogger(__name__)


class UMHVersionCoherenceEngine:
    """Detects whether all UMH nodes run the same substrate version."""

    def __init__(self, registry: UMHNodeRegistry | None = None) -> None:
        self._registry = registry

    @property
    def registry(self) -> UMHNodeRegistry:
        if self._registry is None:
            self._registry = UMHNodeRegistry()
        return self._registry

    def canonical_version(self) -> UMHVersionInfo | None:
        """Return version info from the primary node."""
        primary = self.registry.primary_node()
        if primary is None:
            return None
        if not primary.version.git_commit:
            return None
        return primary.version

    def node_version_status(self, node_id: str) -> dict[str, Any]:
        """Check a single node's version against canonical."""
        node = self.registry.get_node(node_id)
        if node is None:
            return {"node_id": node_id, "found": False}

        canonical = self.canonical_version()
        if canonical is None:
            return {
                "node_id": node_id,
                "found": True,
                "status": UMHVersionStatus.UNKNOWN.value,
                "reason": "no canonical version available",
                "version": node.version.to_dict(),
            }

        matches = canonical.matches(node.version)
        drift_fields: list[str] = []
        if not matches and node.version.git_commit:
            if node.version.git_commit != canonical.git_commit:
                drift_fields.append("git_commit")
            if node.version.schema_version != canonical.schema_version:
                drift_fields.append("schema_version")
            if node.version.migration_version != canonical.migration_version:
                drift_fields.append("migration_version")

        return {
            "node_id": node_id,
            "found": True,
            "status": UMHVersionStatus.COHERENT.value
            if matches
            else UMHVersionStatus.DRIFTED.value,
            "matches_canonical": matches,
            "drift_fields": drift_fields,
            "version": node.version.to_dict(),
            "canonical": canonical.to_dict(),
        }

    def overall_status(self) -> UMHVersionStatus:
        """Determine organism-wide version coherence."""
        nodes = self.registry.list_nodes()
        if not nodes:
            return UMHVersionStatus.UNKNOWN

        online_nodes = [
            n
            for n in nodes
            if n.status not in (UMHNodeStatus.OFFLINE.value, UMHNodeStatus.UNKNOWN.value)
        ]
        if not online_nodes:
            known_versions = [n for n in nodes if n.version.git_commit]
            if not known_versions:
                return UMHVersionStatus.UNKNOWN
            online_nodes = known_versions

        canonical = self.canonical_version()
        if canonical is None:
            has_any_version = any(n.version.git_commit for n in online_nodes)
            if not has_any_version:
                return UMHVersionStatus.UNKNOWN
            commits = {n.version.git_commit for n in online_nodes if n.version.git_commit}
            if len(commits) <= 1:
                return UMHVersionStatus.COHERENT
            return UMHVersionStatus.DRIFTED

        for node in online_nodes:
            if node.version.git_commit and not canonical.matches(node.version):
                return UMHVersionStatus.DRIFTED

        return UMHVersionStatus.COHERENT

    def drift_report(self) -> dict[str, Any]:
        """Per-node version comparison against canonical."""
        canonical = self.canonical_version()
        nodes = self.registry.list_nodes()

        node_reports: list[dict[str, Any]] = []
        for node in nodes:
            node_reports.append(self.node_version_status(node.node_id))

        return {
            "overall_status": self.overall_status().value,
            "canonical_version": canonical.to_dict() if canonical else None,
            "node_count": len(nodes),
            "nodes": node_reports,
        }
