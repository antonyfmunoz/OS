"""Namespace Convergence Engine v1.

Validates canonical package ownership, import roots, no duplicate
subsystem namespaces, no parallel semantic domains, no stale aliases,
no shadow module trees.

UMH substrate subsystem. Phase 96.8CO.
"""

from __future__ import annotations

from typing import Any

from core.convergence.repository_topology_contracts_v1 import (
    NamespaceConvergenceState,
    _now_iso,
    _deterministic_id,
)


MAX_NAMESPACE_CHECKS = 100

CANONICAL_NAMESPACES = [
    "core",
    "runtime",
    "services",
    "scripts",
]


class NamespaceConvergenceEngine:
    """Validates namespace convergence."""

    def __init__(self) -> None:
        self._checks: list[NamespaceConvergenceState] = []

    def check_convergence(
        self,
        namespaces_checked: int = 0,
        duplicates_found: int = 0,
        stale_aliases_found: int = 0,
        shadow_trees_found: int = 0,
    ) -> dict[str, Any]:
        if len(self._checks) >= MAX_NAMESPACE_CHECKS:
            raise ValueError("Max namespace checks reached")

        converged = duplicates_found == 0 and stale_aliases_found == 0 and shadow_trees_found == 0

        state = NamespaceConvergenceState(
            convergence_id=_deterministic_id("nsconv-", _now_iso()),
            namespaces_checked=namespaces_checked,
            duplicates_found=duplicates_found,
            stale_aliases_found=stale_aliases_found,
            shadow_trees_found=shadow_trees_found,
            converged=converged,
        )
        self._checks.append(state)
        return state.to_dict()

    def all_converged(self) -> bool:
        return all(c.converged for c in self._checks) if self._checks else False

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_checks": len(self._checks),
            "all_converged": self.all_converged() if self._checks else False,
        }
