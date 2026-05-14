"""Trust Boundary Policies v1.

8 limits and 8 forbidden actions for trust operations.

UMH substrate subsystem. Phase 96.8CM.
"""

from __future__ import annotations

from typing import Any

from core.trust.sovereign_operational_trust_contracts_v1 import _now_iso


TRUST_LIMITS: dict[str, int] = {
    "max_trust_runs": 50,
    "max_artifacts": 500,
    "max_bundles": 100,
    "max_verifications": 100,
    "max_constitutional_proofs": 100,
    "max_chronology_proofs": 100,
    "max_provenance_proofs": 100,
    "max_replay_checks": 50,
}

FORBIDDEN_TRUST_ACTIONS = [
    "unsupported_trust_claims",
    "missing_evidence_bundles",
    "unverifiable_attestations",
    "hidden_trust_mutation",
    "trust_owned_execution",
    "self_attestation_without_lineage",
    "governance_bypass",
    "replay_bypass",
]


class TrustBoundaryPolicies:
    """Enforces trust operation boundaries."""

    def __init__(self) -> None:
        self._denied: list[dict[str, Any]] = []

    def check_limit(self, limit_name: str, current_value: int, override: int | None = None) -> dict[str, Any]:
        default = TRUST_LIMITS.get(limit_name)
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
        forbidden = action in FORBIDDEN_TRUST_ACTIONS
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
            "total_limits": len(TRUST_LIMITS),
            "total_forbidden": len(FORBIDDEN_TRUST_ACTIONS),
            "total_denied": len(self._denied),
        }
