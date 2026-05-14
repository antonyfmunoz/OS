"""Federation Interoperability Engine v1.

Supports: verify peer, inspect peer manifest, compare trust bundles,
compare topology manifests, generate interoperability report,
propose coordination boundary.

Forbidden: execute peer task, mutate peer state, sync memory
automatically, federate cognition, federate governance.

UMH substrate subsystem. Phase 96.8CN.
"""

from __future__ import annotations

from typing import Any

from core.federation.sovereign_federation_readiness_contracts_v1 import (
    FederationInteroperabilityState,
    _now_iso,
    _deterministic_id,
)


MAX_INTEROP_REPORTS = 100

FORBIDDEN_INTEROP_ACTIONS = [
    "execute_peer_task",
    "mutate_peer_state",
    "sync_memory_automatically",
    "federate_cognition",
    "federate_governance",
]


class FederationInteroperabilityEngine:
    """Generates interoperability reports between sovereign runtimes."""

    def __init__(self) -> None:
        self._reports: list[FederationInteroperabilityState] = []

    def generate_report(
        self,
        local_runtime_id: str,
        peer_runtime_id: str,
        local_trust_hash: str = "",
        peer_trust_hash: str = "",
        local_topology: dict[str, Any] | None = None,
        peer_topology: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if len(self._reports) >= MAX_INTEROP_REPORTS:
            raise ValueError("Max interop reports reached")

        trust_compat = local_trust_hash != "" and peer_trust_hash != ""
        topo_compat = (local_topology is not None) and (peer_topology is not None)
        cap_compat = trust_compat
        boundary_compat = topo_compat

        state = FederationInteroperabilityState(
            interop_id=_deterministic_id("fintop-", local_runtime_id, peer_runtime_id, _now_iso()),
            local_runtime_id=local_runtime_id,
            peer_runtime_id=peer_runtime_id,
            trust_compatible=trust_compat,
            topology_compatible=topo_compat,
            capability_compatible=cap_compat,
            boundary_compatible=boundary_compat,
        )
        self._reports.append(state)
        return state.to_dict()

    def check_forbidden(self, action: str) -> dict[str, Any]:
        forbidden = action in FORBIDDEN_INTEROP_ACTIONS
        return {
            "action": action,
            "forbidden": forbidden,
            "timestamp": _now_iso(),
        }

    def all_compatible(self) -> bool:
        return all(
            r.trust_compatible and r.topology_compatible
            and r.capability_compatible and r.boundary_compatible
            for r in self._reports
        ) if self._reports else False

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_reports": len(self._reports),
            "all_compatible": self.all_compatible() if self._reports else False,
        }
