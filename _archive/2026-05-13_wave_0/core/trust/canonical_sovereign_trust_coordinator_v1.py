"""Canonical Sovereign Trust Coordinator v1.

Coordinates portable, externally verifiable sovereign trust artifact
generation, bundling, verification, and proof production.

Must NEVER: fabricate trust evidence, mutate source artifacts,
generate unsupported attestations, bypass accountability lineage,
bypass replay lineage.

All trust derives ONLY from: persisted artifacts, persisted hashes,
persisted lineage, persisted proofs, persisted observability events.

UMH substrate subsystem. Phase 96.8CM.
"""

from __future__ import annotations

from typing import Any

from core.trust.sovereign_operational_trust_contracts_v1 import (
    SovereignTrustState,
    TrustProofReceipt,
    _now_iso,
    _deterministic_id,
)
from core.trust.trust_lifecycle_engine_v1 import TrustLifecycleEngine
from core.trust.trust_artifact_engine_v1 import TrustArtifactEngine
from core.trust.trust_bundle_engine_v1 import TrustBundleEngine, BUNDLE_DOMAINS
from core.trust.external_verification_engine_v1 import ExternalVerificationEngine
from core.trust.trust_replay_validator_v1 import TrustReplayValidator
from core.trust.constitutional_trust_proof_engine_v1 import ConstitutionalTrustProofEngine
from core.trust.chronology_trust_proof_engine_v1 import ChronologyTrustProofEngine
from core.trust.provenance_trust_proof_engine_v1 import ProvenanceTrustProofEngine
from core.trust.trust_observability_pipeline_v1 import TrustObservabilityPipeline
from core.trust.trust_boundary_policies_v1 import TrustBoundaryPolicies


MAX_TRUST_RUNS = 50


class CanonicalSovereignTrustCoordinator:
    """Coordinates sovereign trust proving.

    Cannot fabricate trust evidence.
    Cannot mutate source artifacts.
    Cannot generate unsupported attestations.
    Cannot bypass accountability lineage.
    Cannot bypass replay lineage.
    """

    def __init__(self, state_dir: str = "") -> None:
        self._lifecycle = TrustLifecycleEngine()
        self._artifacts = TrustArtifactEngine()
        self._bundles = TrustBundleEngine(
            output_dir=state_dir or "data/runtime/trust/bundles",
        )
        self._verifier = ExternalVerificationEngine()
        self._replay_validator = TrustReplayValidator()
        self._constitutional = ConstitutionalTrustProofEngine()
        self._chronology = ChronologyTrustProofEngine()
        self._provenance = ProvenanceTrustProofEngine()
        self._obs_pipeline = TrustObservabilityPipeline(
            output_dir=state_dir or "data/runtime/trust",
        )
        self._boundary = TrustBoundaryPolicies()

        self._runs: list[SovereignTrustState] = []
        self._receipts: list[TrustProofReceipt] = []

    def start_trust_run(self, run_id: str = "") -> dict[str, Any]:
        if len(self._runs) >= MAX_TRUST_RUNS:
            raise ValueError("Max trust runs reached")
        if not run_id:
            run_id = _deterministic_id("trustrun-", _now_iso())
        state = SovereignTrustState(trust_id=run_id)
        self._runs.append(state)
        self._obs_pipeline.emit_trust_bundle_created({"run_id": run_id})
        return {"run_id": run_id, "status": "started"}

    def generate_artifacts(self) -> dict[str, Any]:
        result = self._artifacts.generate_all_types()
        self._obs_pipeline.emit_trust_artifact_hashed({"total": result["total"]})
        return result

    def create_trust_bundle(self, artifacts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        arts = artifacts or []
        if not arts:
            gen = self._artifacts.generate_all_types()
            arts = gen["artifacts"]
        result = self._bundles.create_bundle(arts, domains_included=list(BUNDLE_DOMAINS))
        self._obs_pipeline.emit_trust_bundle_created({"bundle_id": result.get("bundle_id", "")})
        return result

    def verify_bundle(self, bundle: dict[str, Any], artifacts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        result = self._verifier.verify_bundle(bundle, artifacts)
        self._obs_pipeline.emit_trust_bundle_verified({"bundle_id": bundle.get("bundle_id", "")})
        return result

    def verify_externally(self, bundle: dict[str, Any], artifacts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        result = self._verifier.verify_bundle(bundle, artifacts)
        self._obs_pipeline.emit_external_verification_completed(
            {"bundle_id": bundle.get("bundle_id", ""), "score": result.get("trust_integrity_score", 0)},
        )
        return result

    def prove_constitutional(self, **overrides: bool) -> dict[str, Any]:
        return self._constitutional.generate_proof(**overrides)

    def prove_chronology(self, **overrides: bool) -> dict[str, Any]:
        return self._chronology.generate_proof(**overrides)

    def prove_provenance(self, **overrides: bool) -> dict[str, Any]:
        return self._provenance.generate_proof(**overrides)

    def validate_replay_determinism(self) -> dict[str, Any]:
        result = self._replay_validator.validate_all()
        self._obs_pipeline.emit_trust_replay_validated({"total": result["total"]})
        return result

    def check_boundary(self, limit_name: str, current_value: int) -> dict[str, Any]:
        return self._boundary.check_limit(limit_name, current_value)

    def complete_trust_run(self, run_id: str) -> dict[str, Any]:
        all_trusted = all([
            self._artifacts.all_hashed(),
            self._bundles.all_hashed() if self._bundles.get_stats()["total_bundles"] > 0 else True,
            self._verifier.all_verified() if self._verifier.get_stats()["total_verifications"] > 0 else True,
            self._constitutional.all_certified() if self._constitutional.get_stats()["total_proofs"] > 0 else True,
            self._chronology.all_proven() if self._chronology.get_stats()["total_proofs"] > 0 else True,
            self._provenance.all_proven() if self._provenance.get_stats()["total_proofs"] > 0 else True,
            self._replay_validator.all_deterministic(),
        ])

        outcome = "trusted" if all_trusted else "incomplete"
        receipt = TrustProofReceipt(
            run_id=run_id,
            outcome=outcome,
            bundles_generated=self._bundles.get_stats()["total_bundles"],
            verifications_passed=self._verifier.get_stats()["total_verifications"],
        )
        self._receipts.append(receipt)
        return receipt.to_dict()

    def get_trust_report(self) -> dict[str, Any]:
        return {
            "artifacts": self._artifacts.get_stats(),
            "bundles": self._bundles.get_stats(),
            "verifier": self._verifier.get_stats(),
            "constitutional": self._constitutional.get_stats(),
            "chronology": self._chronology.get_stats(),
            "provenance": self._provenance.get_stats(),
            "replay_validator": self._replay_validator.get_stats(),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "lifecycle": self._lifecycle.get_stats(),
            "artifacts": self._artifacts.get_stats(),
            "bundles": self._bundles.get_stats(),
            "verifier": self._verifier.get_stats(),
            "replay_validator": self._replay_validator.get_stats(),
            "constitutional": self._constitutional.get_stats(),
            "chronology": self._chronology.get_stats(),
            "provenance": self._provenance.get_stats(),
            "obs_pipeline": self._obs_pipeline.get_stats(),
            "boundary": self._boundary.get_stats(),
            "runs": len(self._runs),
            "receipts": len(self._receipts),
        }
