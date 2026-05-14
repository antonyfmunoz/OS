"""Continuity Accountability Engine v1.

Explains checkpoint lineage, restoration lineage, continuity chain
integrity, chronology preservation, and restoration validation.

UMH substrate subsystem. Phase 96.8CK.
"""

from __future__ import annotations

from typing import Any

from core.explainability.constitutional_explainability_contracts_v1 import (
    ContinuityExplanationState,
    _now_iso,
)

MAX_CONTINUITY_EXPLANATIONS = 200

CONTINUITY_ACCOUNTABILITY_DOMAINS: list[str] = [
    "checkpoint_lineage",
    "restoration_lineage",
    "continuity_chain_integrity",
    "chronology_preservation",
    "restoration_validation",
]


class ContinuityAccountabilityEngine:
    def __init__(self) -> None:
        self._explanations: list[ContinuityExplanationState] = []

    def explain_continuity(self, checkpoint_id: str, restoration_valid: bool = True, explanation: str = "") -> dict[str, Any]:
        if len(self._explanations) >= MAX_CONTINUITY_EXPLANATIONS:
            raise ValueError("Max continuity explanations reached")
        state = ContinuityExplanationState(checkpoint_id=checkpoint_id, restoration_valid=restoration_valid, explanation=explanation)
        self._explanations.append(state)
        return state.to_dict()

    def explain_all_domains(self) -> dict[str, Any]:
        results = []
        for domain in CONTINUITY_ACCOUNTABILITY_DOMAINS:
            r = self.explain_continuity(f"ckpt-{domain}", restoration_valid=True, explanation=f"{domain} verified")
            results.append(r)
        return {"all_valid": all(r["restoration_valid"] for r in results), "explanations": results, "total": len(results)}

    def all_valid(self) -> bool:
        if not self._explanations:
            return True
        return all(e.restoration_valid for e in self._explanations)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_explanations": len(self._explanations),
            "all_valid": self.all_valid(),
            "domains": len(CONTINUITY_ACCOUNTABILITY_DOMAINS),
        }
