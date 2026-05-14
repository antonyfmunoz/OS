"""Unified Topology Semantics Engine v1.

Unifies environment, application, deployment, orchestration,
and continuity topologies. Prevents hidden topology mutation,
orphan graphs, and topology drift.

UMH substrate subsystem. Phase 96.8CG.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from core.constitutional.constitutional_runtime_contracts_v1 import (
    UnifiedTopologyState,
    _now_iso,
)

KNOWN_TOPOLOGY_DOMAINS = [
    "environment",
    "application",
    "deployment",
    "orchestration",
    "continuity",
]

MAX_TOPOLOGY_DOMAINS = 10


class UnifiedTopologySemanticsEngine:
    """Validates topology semantics across all substrate domains."""

    def __init__(self) -> None:
        self._domain_hashes: dict[str, str] = {}
        self._baseline_hashes: dict[str, str] = {}

    def register_topology(
        self,
        domain: str,
        topology_hash: str,
    ) -> dict[str, Any]:
        if domain not in KNOWN_TOPOLOGY_DOMAINS:
            raise ValueError(
                f"Unknown domain: {domain}. Known: {KNOWN_TOPOLOGY_DOMAINS}"
            )

        self._domain_hashes[domain] = topology_hash

        if domain not in self._baseline_hashes:
            self._baseline_hashes[domain] = topology_hash

        return {
            "domain": domain,
            "topology_hash": topology_hash,
            "baseline_match": topology_hash == self._baseline_hashes.get(domain),
            "timestamp": _now_iso(),
        }

    def detect_drift(self, domain: str) -> bool:
        current = self._domain_hashes.get(domain)
        baseline = self._baseline_hashes.get(domain)
        if current is None or baseline is None:
            return False
        return current != baseline

    def detect_all_drift(self) -> list[str]:
        return [d for d in self._domain_hashes if self.detect_drift(d)]

    def get_unified_hash(self) -> str:
        content = json.dumps(
            dict(sorted(self._domain_hashes.items())),
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get_unified_state(self) -> UnifiedTopologyState:
        drifted = self.detect_all_drift()
        return UnifiedTopologyState(
            topologies_validated=len(self._domain_hashes),
            topology_coherent=len(drifted) == 0,
            drift_detected=len(drifted) > 0,
        )

    def update_baseline(self, domain: str) -> None:
        current = self._domain_hashes.get(domain)
        if current is not None:
            self._baseline_hashes[domain] = current

    def get_stats(self) -> dict[str, object]:
        return {
            "domains_registered": len(self._domain_hashes),
            "drift_count": len(self.detect_all_drift()),
        }
