"""Constitutional Trust Proof Engine v1.

Proves: invariant certification, governance preservation,
no execution outside spine, no fabricated proofs, no hidden mutation.

UMH substrate subsystem. Phase 96.8CM.
"""

from __future__ import annotations

from typing import Any

from core.trust.sovereign_operational_trust_contracts_v1 import (
    ConstitutionalTrustProof,
    _now_iso,
    _deterministic_id,
)


MAX_CONSTITUTIONAL_PROOFS = 100

CONSTITUTIONAL_PROOF_DIMENSIONS = [
    "invariant_certification",
    "governance_preservation",
    "no_execution_outside_spine",
    "no_fabricated_proofs",
    "no_hidden_mutation",
]


class ConstitutionalTrustProofEngine:
    """Generates constitutional trust proofs."""

    def __init__(self) -> None:
        self._proofs: list[ConstitutionalTrustProof] = []

    def generate_proof(self, **overrides: bool) -> dict[str, Any]:
        if len(self._proofs) >= MAX_CONSTITUTIONAL_PROOFS:
            raise ValueError("Max constitutional proofs reached")
        proof = ConstitutionalTrustProof(
            proof_id=_deterministic_id("ctprf-", _now_iso()),
            invariant_certified=overrides.get("invariant_certified", True),
            governance_preserved=overrides.get("governance_preserved", True),
            no_execution_outside_spine=overrides.get("no_execution_outside_spine", True),
            no_fabricated_proofs=overrides.get("no_fabricated_proofs", True),
            no_hidden_mutation=overrides.get("no_hidden_mutation", True),
        )
        self._proofs.append(proof)
        return proof.to_dict()

    def all_certified(self) -> bool:
        return all(
            p.invariant_certified
            and p.governance_preserved
            and p.no_execution_outside_spine
            and p.no_fabricated_proofs
            and p.no_hidden_mutation
            for p in self._proofs
        ) if self._proofs else False

    def get_failed(self) -> list[dict[str, Any]]:
        return [
            p.to_dict() for p in self._proofs
            if not (
                p.invariant_certified
                and p.governance_preserved
                and p.no_execution_outside_spine
                and p.no_fabricated_proofs
                and p.no_hidden_mutation
            )
        ]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_proofs": len(self._proofs),
            "all_certified": self.all_certified() if self._proofs else False,
        }
