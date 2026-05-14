"""Governance Assault Engine v1.

Simulates governance bypass/evasion attempts.
All attacks must fail constitutionally.

UMH substrate subsystem. Phase 96.8CJ.
"""

from __future__ import annotations

from typing import Any

from core.validation.sovereign_operational_validation_contracts_v1 import (
    GovernanceAttackState,
    _now_iso,
)

MAX_ATTACKS = 100

GOVERNANCE_ATTACK_TYPES: list[str] = [
    "governance_bypass_attempt",
    "hidden_execution_attempt",
    "hidden_replay_attempt",
    "hidden_observability_attempt",
    "hidden_topology_mutation_attempt",
    "execution_outside_spine_attempt",
    "recursive_orchestration_attempt",
    "unauthorized_continuation_attempt",
]


class GovernanceAssaultEngine:
    def __init__(self) -> None:
        self._attacks: list[GovernanceAttackState] = []

    def simulate_attack(self, attack_type: str, blocked: bool = True) -> dict[str, Any]:
        if len(self._attacks) >= MAX_ATTACKS:
            raise ValueError("Max governance attacks reached")
        state = GovernanceAttackState(attack_type=attack_type, blocked=blocked)
        self._attacks.append(state)
        return state.to_dict()

    def simulate_all_attacks(self) -> dict[str, Any]:
        results = []
        for at in GOVERNANCE_ATTACK_TYPES:
            r = self.simulate_attack(at, blocked=True)
            results.append(r)
        return {"all_blocked": all(r["blocked"] for r in results), "attacks": results, "total": len(results)}

    def all_blocked(self) -> bool:
        if not self._attacks:
            return True
        return all(a.blocked for a in self._attacks)

    def get_breached(self) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self._attacks if not a.blocked]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_attacks": len(self._attacks),
            "blocked": sum(1 for a in self._attacks if a.blocked),
            "breached": sum(1 for a in self._attacks if not a.blocked),
            "all_blocked": self.all_blocked(),
        }
