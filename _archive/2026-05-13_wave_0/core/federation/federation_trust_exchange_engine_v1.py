"""Federation Trust Exchange Engine v1.

Exchanges trust bundle manifests, runtime attestations,
constitutional/chronology/provenance/governance proofs between
sovereign runtimes. Uses artifact-based verification only.

UMH substrate subsystem. Phase 96.8CN.
"""

from __future__ import annotations

from typing import Any

from core.federation.sovereign_federation_readiness_contracts_v1 import (
    FederationTrustExchange,
    CrossRuntimeTrustBundle,
    _now_iso,
    _deterministic_id,
)


MAX_EXCHANGES = 200

EXCHANGE_PROOF_TYPES = [
    "trust_bundle",
    "runtime_attestation",
    "constitutional_proof",
    "chronology_proof",
    "provenance_proof",
    "governance_proof",
]


class FederationTrustExchangeEngine:
    """Manages trust exchanges between sovereign runtimes."""

    def __init__(self) -> None:
        self._exchanges: list[FederationTrustExchange] = []
        self._cross_bundles: list[CrossRuntimeTrustBundle] = []

    def exchange_trust(
        self,
        local_runtime_id: str,
        peer_runtime_id: str,
        peer_trust_bundle: dict[str, Any],
    ) -> dict[str, Any]:
        if len(self._exchanges) >= MAX_EXCHANGES:
            raise ValueError("Max exchanges reached")

        has_bundle = peer_trust_bundle.get("trust_bundle_hash", "") != ""
        has_attestation = peer_trust_bundle.get("constitutional_proof_hash", "") != ""

        exchange = FederationTrustExchange(
            exchange_id=_deterministic_id("ftex-", local_runtime_id, peer_runtime_id, _now_iso()),
            local_runtime_id=local_runtime_id,
            peer_runtime_id=peer_runtime_id,
            trust_bundle_exchanged=has_bundle,
            attestation_exchanged=has_attestation,
            verified=has_bundle and has_attestation,
        )
        self._exchanges.append(exchange)

        cross_bundle = CrossRuntimeTrustBundle(
            source_runtime_id=peer_runtime_id,
            trust_bundle_hash=peer_trust_bundle.get("trust_bundle_hash", ""),
            constitutional_proof_hash=peer_trust_bundle.get("constitutional_proof_hash", ""),
            chronology_proof_hash=peer_trust_bundle.get("chronology_proof_hash", ""),
            provenance_proof_hash=peer_trust_bundle.get("provenance_proof_hash", ""),
            governance_proof_hash=peer_trust_bundle.get("governance_proof_hash", ""),
        )
        self._cross_bundles.append(cross_bundle)

        return exchange.to_dict()

    def all_verified(self) -> bool:
        return all(e.verified for e in self._exchanges) if self._exchanges else False

    def get_unverified(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._exchanges if not e.verified]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_exchanges": len(self._exchanges),
            "total_cross_bundles": len(self._cross_bundles),
            "all_verified": self.all_verified() if self._exchanges else False,
        }
