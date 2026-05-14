"""Runtime Certification Boundary Policies v1.

8 limits and 8 forbidden actions for runtime certification.
Override capping via min(override, default).

UMH substrate subsystem. Phase 96.8CI.
"""

from __future__ import annotations

from typing import Any

from core.certification.runtime_certification_contracts_v1 import (
    CertificationBoundaryState,
    _now_iso,
)


CERTIFICATION_LIMITS: dict[str, int] = {
    "max_certification_runs": 50,
    "max_invariants": 200,
    "max_guarantees": 200,
    "max_topology_certifications": 50,
    "max_continuity_certifications": 50,
    "max_replay_certifications": 100,
    "max_semantic_checks": 100,
    "max_cross_layer_checks": 100,
}

FORBIDDEN_CERTIFICATION_ACTIONS: list[str] = [
    "hidden_certification_mutation",
    "certification_owned_execution",
    "certification_owned_repair",
    "governance_bypass",
    "replay_bypass",
    "observability_bypass",
    "recursive_certification",
    "execution_outside_spine",
]


class RuntimeCertificationBoundaryPolicies:
    """Enforces certification boundary policies."""

    def __init__(
        self, overrides: dict[str, int] | None = None,
    ) -> None:
        self._limits = dict(CERTIFICATION_LIMITS)
        if overrides:
            for key, value in overrides.items():
                if key in self._limits:
                    self._limits[key] = min(value, CERTIFICATION_LIMITS[key])
        self._checks: list[CertificationBoundaryState] = []

    def check_limit(
        self, limit_name: str, current_value: int,
    ) -> dict[str, Any]:
        max_value = self._limits.get(limit_name, 0)
        exceeded = current_value >= max_value

        state = CertificationBoundaryState(
            limit_name=limit_name,
            current_value=current_value,
            max_value=max_value,
            exceeded=exceeded,
        )
        self._checks.append(state)
        return state.to_dict()

    def is_forbidden(self, action: str) -> bool:
        return action in FORBIDDEN_CERTIFICATION_ACTIONS

    def get_limits(self) -> dict[str, int]:
        return dict(self._limits)

    def get_forbidden_actions(self) -> list[str]:
        return list(FORBIDDEN_CERTIFICATION_ACTIONS)

    def get_all_checks(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._checks]

    def get_exceeded_checks(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._checks if c.exceeded]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_limits": len(self._limits),
            "total_forbidden": len(FORBIDDEN_CERTIFICATION_ACTIONS),
            "total_checks": len(self._checks),
            "exceeded_checks": len(self.get_exceeded_checks()),
        }
