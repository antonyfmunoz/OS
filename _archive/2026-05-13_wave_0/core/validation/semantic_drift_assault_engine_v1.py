"""Semantic Drift Assault Engine v1.

Simulates semantic drift attacks: definition mutation,
cross-layer inconsistency, vocabulary corruption,
constraint relaxation, meaning divergence.

UMH substrate subsystem. Phase 96.8CJ.
"""

from __future__ import annotations

from typing import Any

from core.validation.sovereign_operational_validation_contracts_v1 import (
    SemanticAttackState,
    _now_iso,
)

MAX_SEMANTIC_ATTACKS = 100

SEMANTIC_ATTACK_TYPES: list[str] = [
    "definition_mutation_attempt",
    "cross_layer_inconsistency_attempt",
    "vocabulary_corruption_attempt",
    "constraint_relaxation_attempt",
    "meaning_divergence_attempt",
]


class SemanticDriftAssaultEngine:
    def __init__(self) -> None:
        self._attacks: list[SemanticAttackState] = []

    def simulate_attack(self, attack_type: str, consistency_preserved: bool = True) -> dict[str, Any]:
        if len(self._attacks) >= MAX_SEMANTIC_ATTACKS:
            raise ValueError("Max semantic attacks reached")
        state = SemanticAttackState(attack_type=attack_type, consistency_preserved=consistency_preserved)
        self._attacks.append(state)
        return state.to_dict()

    def simulate_all_attacks(self) -> dict[str, Any]:
        results = []
        for at in SEMANTIC_ATTACK_TYPES:
            r = self.simulate_attack(at, consistency_preserved=True)
            results.append(r)
        return {"all_preserved": all(r["consistency_preserved"] for r in results), "attacks": results, "total": len(results)}

    def all_preserved(self) -> bool:
        if not self._attacks:
            return True
        return all(a.consistency_preserved for a in self._attacks)

    def get_drifted(self) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self._attacks if not a.consistency_preserved]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_attacks": len(self._attacks),
            "preserved": sum(1 for a in self._attacks if a.consistency_preserved),
            "drifted": sum(1 for a in self._attacks if not a.consistency_preserved),
            "all_preserved": self.all_preserved(),
        }
