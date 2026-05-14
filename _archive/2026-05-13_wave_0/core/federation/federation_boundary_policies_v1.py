"""Federation Boundary Policies v1.

8 limits and 10 forbidden actions for federation operations.

UMH substrate subsystem. Phase 96.8CN.
"""

from __future__ import annotations

from typing import Any

from core.federation.sovereign_federation_readiness_contracts_v1 import _now_iso


FEDERATION_LIMITS: dict[str, int] = {
    "max_federation_runs": 50,
    "max_identities": 10,
    "max_recognitions": 200,
    "max_exchanges": 200,
    "max_topology_manifests": 100,
    "max_capability_manifests": 100,
    "max_interop_reports": 100,
    "max_replay_checks": 50,
}

FORBIDDEN_FEDERATION_ACTIONS = [
    "authority_transfer",
    "peer_owned_execution",
    "peer_owned_governance",
    "peer_owned_cognition",
    "recursive_federation",
    "autonomous_consensus",
    "hidden_synchronization",
    "cross_runtime_memory_mutation",
    "cross_runtime_topology_mutation",
    "distributed_self_direction",
]


class FederationBoundaryPolicies:
    """Enforces federation operation boundaries."""

    def __init__(self) -> None:
        self._denied: list[dict[str, Any]] = []

    def check_limit(self, limit_name: str, current_value: int, override: int | None = None) -> dict[str, Any]:
        default = FEDERATION_LIMITS.get(limit_name)
        if default is None:
            raise ValueError(f"Unknown limit: {limit_name}")
        effective = min(override, default) if override is not None else default
        allowed = current_value < effective
        result = {
            "limit_name": limit_name,
            "current_value": current_value,
            "effective_limit": effective,
            "allowed": allowed,
            "timestamp": _now_iso(),
        }
        if not allowed:
            self._denied.append(result)
        return result

    def check_forbidden(self, action: str) -> dict[str, Any]:
        forbidden = action in FORBIDDEN_FEDERATION_ACTIONS
        result = {
            "action": action,
            "forbidden": forbidden,
            "timestamp": _now_iso(),
        }
        if forbidden:
            self._denied.append(result)
        return result

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_limits": len(FEDERATION_LIMITS),
            "total_forbidden": len(FORBIDDEN_FEDERATION_ACTIONS),
            "total_denied": len(self._denied),
        }
