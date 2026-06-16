"""State Coherence Engine — detects state authority coherence across nodes.

Composes StateRegistry + UMHNodeRegistry to determine whether each
state domain's authority node is online, reachable, and version-coherent.

No replication. No synchronization. No repair. Observation only.

Phase 29. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from substrate.organism.state_authority_graph import (
    StateCoherenceStatus,
    StateDomainStatus,
)
from substrate.organism.state_registry import StateRegistry

logger = logging.getLogger(__name__)

STALENESS_THRESHOLD_SECONDS = 3600


class StateCoherenceEngine:
    """Detects whether state domain authorities are coherent."""

    def __init__(
        self,
        state_registry: StateRegistry | None = None,
        node_registry: Any | None = None,
    ) -> None:
        self._state_registry = state_registry
        self._node_registry = node_registry

    @property
    def state_registry(self) -> StateRegistry:
        if self._state_registry is None:
            self._state_registry = StateRegistry()
        return self._state_registry

    @property
    def node_registry(self) -> Any:
        if self._node_registry is None:
            from substrate.organism.umh_node_registry import UMHNodeRegistry

            self._node_registry = UMHNodeRegistry()
        return self._node_registry

    def domain_status(self, domain: str) -> StateDomainStatus:
        """Check coherence status for a single state domain."""
        auth = self.state_registry.get_domain(domain)
        if auth is None:
            return StateDomainStatus(
                domain=domain,
                status=StateCoherenceStatus.UNKNOWN.value,
            )

        node = self.node_registry.get_node(auth.node_id)
        if node is None:
            return StateDomainStatus(
                domain=domain,
                authority_node=auth.node_id,
                status=StateCoherenceStatus.UNKNOWN.value,
            )

        if node.status == "offline":
            return StateDomainStatus(
                domain=domain,
                authority_node=auth.node_id,
                status=StateCoherenceStatus.STALE.value,
                last_updated=node.last_seen,
            )

        if node.last_seen > 0:
            age = time.time() - node.last_seen
            if age > STALENESS_THRESHOLD_SECONDS:
                return StateDomainStatus(
                    domain=domain,
                    authority_node=auth.node_id,
                    status=StateCoherenceStatus.STALE.value,
                    last_updated=node.last_seen,
                )

        version_engine = self._get_version_engine()
        if version_engine is not None:
            try:
                node_vs = version_engine.node_version_status(auth.node_id)
                if node_vs.get("status") == "drifted":
                    return StateDomainStatus(
                        domain=domain,
                        authority_node=auth.node_id,
                        status=StateCoherenceStatus.DRIFTED.value,
                        last_updated=node.last_seen,
                    )
            except Exception:
                logger.debug("Version check failed for %s", auth.node_id)

        return StateDomainStatus(
            domain=domain,
            authority_node=auth.node_id,
            status=StateCoherenceStatus.COHERENT.value,
            last_updated=node.last_seen,
        )

    def coherence_report(self) -> dict[str, Any]:
        """Per-domain coherence status."""
        authorities = self.state_registry.all_domains()
        domain_reports: list[dict[str, Any]] = []

        for auth in authorities:
            status = self.domain_status(auth.domain)
            report = status.to_dict()
            report["storage_location"] = auth.storage_location
            report["service_owner"] = auth.service_owner
            domain_reports.append(report)

        health = self._compute_health(domain_reports)

        return {
            "overall_health": health,
            "domain_count": len(domain_reports),
            "domains": domain_reports,
        }

    def organism_health(self) -> dict[str, Any]:
        """Summary health counts across all state domains."""
        authorities = self.state_registry.all_domains()
        counts: dict[str, int] = {
            "coherent": 0,
            "stale": 0,
            "drifted": 0,
            "unknown": 0,
        }

        for auth in authorities:
            status = self.domain_status(auth.domain)
            s = status.status
            if s in counts:
                counts[s] += 1
            else:
                counts["unknown"] += 1

        total = sum(counts.values())
        return {
            "total_domains": total,
            **counts,
            "healthy": counts["coherent"] == total,
        }

    def _compute_health(self, reports: list[dict[str, Any]]) -> str:
        statuses = {r.get("status", "unknown") for r in reports}
        if not statuses:
            return "unknown"
        if statuses == {"coherent"}:
            return "healthy"
        if "drifted" in statuses:
            return "degraded"
        if "stale" in statuses:
            return "degraded"
        return "unknown"

    def _get_version_engine(self) -> Any | None:
        try:
            from substrate.organism.umh_version_coherence import (
                UMHVersionCoherenceEngine,
            )

            return UMHVersionCoherenceEngine(registry=self.node_registry)
        except Exception:
            return None
