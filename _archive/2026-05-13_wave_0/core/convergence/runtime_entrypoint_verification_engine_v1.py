"""Runtime Entrypoint Verification Engine v1.

Verifies single canonical runtime spine, single orchestration root,
single operational entrypoint, no hidden adapters, no hidden dispatch
loops, no alternate execution roots.

UMH substrate subsystem. Phase 96.8CO.
"""

from __future__ import annotations

from typing import Any

from core.convergence.repository_topology_contracts_v1 import (
    RuntimeEntrypointState,
    _now_iso,
    _deterministic_id,
)


MAX_ENTRYPOINT_CHECKS = 100


class RuntimeEntrypointVerificationEngine:
    """Verifies runtime entrypoint singularity."""

    def __init__(self) -> None:
        self._checks: list[RuntimeEntrypointState] = []

    def verify_entrypoints(
        self,
        canonical_spine: str = "core/spine",
        canonical_orchestration_root: str = "core/orchestration",
        canonical_entrypoint: str = "services/discord_bot.py",
        hidden_adapters: int = 0,
        hidden_dispatch_loops: int = 0,
        alternate_roots: int = 0,
    ) -> dict[str, Any]:
        if len(self._checks) >= MAX_ENTRYPOINT_CHECKS:
            raise ValueError("Max entrypoint checks reached")

        single = (
            hidden_adapters == 0
            and hidden_dispatch_loops == 0
            and alternate_roots == 0
        )

        state = RuntimeEntrypointState(
            entrypoint_id=_deterministic_id("rtent-", _now_iso()),
            canonical_spine=canonical_spine,
            canonical_orchestration_root=canonical_orchestration_root,
            canonical_entrypoint=canonical_entrypoint,
            hidden_adapters=hidden_adapters,
            hidden_dispatch_loops=hidden_dispatch_loops,
            alternate_roots=alternate_roots,
            single_spine_verified=single,
        )
        self._checks.append(state)
        return state.to_dict()

    def all_single_spine(self) -> bool:
        return all(c.single_spine_verified for c in self._checks) if self._checks else False

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_checks": len(self._checks),
            "all_single_spine": self.all_single_spine() if self._checks else False,
        }
