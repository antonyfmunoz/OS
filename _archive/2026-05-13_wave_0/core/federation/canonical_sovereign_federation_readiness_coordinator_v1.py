"""Canonical Sovereign Federation Readiness Coordinator v1.

Coordinates sovereign federation readiness — runtime identity,
peer recognition, trust exchange, topology manifests, capability
manifests, interoperability reporting, and boundary enforcement.

Must NEVER: transfer authority, execute peer commands, mutate peer
state, accept peer governance, create consensus, create distributed
cognition, create recursive federation.

UMH substrate subsystem. Phase 96.8CN.
"""

from __future__ import annotations

from typing import Any

from core.federation.sovereign_federation_readiness_contracts_v1 import (
    FederationReadinessState,
    FederationVerificationReceipt,
    _now_iso,
    _deterministic_id,
)
from core.federation.federation_lifecycle_engine_v1 import FederationLifecycleEngine
from core.federation.sovereign_runtime_identity_engine_v1 import SovereignRuntimeIdentityEngine
from core.federation.peer_recognition_engine_v1 import PeerRecognitionEngine
from core.federation.federation_trust_exchange_engine_v1 import FederationTrustExchangeEngine
from core.federation.federation_topology_manifest_engine_v1 import FederationTopologyManifestEngine
from core.federation.cross_runtime_capability_manifest_engine_v1 import CrossRuntimeCapabilityManifestEngine
from core.federation.federation_interoperability_engine_v1 import FederationInteroperabilityEngine
from core.federation.federation_observability_pipeline_v1 import FederationObservabilityPipeline
from core.federation.federation_replay_validator_v1 import FederationReplayValidator
from core.federation.federation_boundary_policies_v1 import FederationBoundaryPolicies


MAX_FEDERATION_RUNS = 50


class CanonicalSovereignFederationReadinessCoordinator:
    """Coordinates sovereign federation readiness.

    Cannot transfer authority.
    Cannot execute peer commands.
    Cannot mutate peer state.
    Cannot accept peer governance.
    Cannot create consensus.
    Cannot create distributed cognition.
    Cannot create recursive federation.
    """

    def __init__(self, state_dir: str = "") -> None:
        sd = state_dir or "data/runtime/federation"
        self._lifecycle = FederationLifecycleEngine()
        self._identity = SovereignRuntimeIdentityEngine(
            output_dir=f"{sd}/identity",
        )
        self._recognition = PeerRecognitionEngine()
        self._trust_exchange = FederationTrustExchangeEngine()
        self._topology = FederationTopologyManifestEngine()
        self._capability = CrossRuntimeCapabilityManifestEngine()
        self._interop = FederationInteroperabilityEngine()
        self._obs_pipeline = FederationObservabilityPipeline(output_dir=sd)
        self._replay_validator = FederationReplayValidator()
        self._boundary = FederationBoundaryPolicies()

        self._runs: list[FederationReadinessState] = []
        self._receipts: list[FederationVerificationReceipt] = []

    def start_federation_run(self, run_id: str = "") -> dict[str, Any]:
        if len(self._runs) >= MAX_FEDERATION_RUNS:
            raise ValueError("Max federation runs reached")
        if not run_id:
            run_id = _deterministic_id("fedrun-", _now_iso())
        state = FederationReadinessState(readiness_id=run_id)
        self._runs.append(state)
        return {"run_id": run_id, "status": "started"}

    def register_identity(
        self,
        runtime_id: str = "",
        trust_bundle_ref: str = "",
        constitutional_ref: str = "",
        topology_ref: str = "",
        capability_ref: str = "",
    ) -> dict[str, Any]:
        result = self._identity.create_identity(
            runtime_id=runtime_id,
            trust_bundle_ref=trust_bundle_ref,
            constitutional_ref=constitutional_ref,
            topology_ref=topology_ref,
            capability_ref=capability_ref,
        )
        self._obs_pipeline.emit_runtime_identity_created({"runtime_id": result["runtime_id"]})
        return result

    def recognize_peer(self, peer_manifest: dict[str, Any]) -> dict[str, Any]:
        result = self._recognition.recognize_peer(peer_manifest)
        self._obs_pipeline.emit_peer_manifest_received({"peer_id": peer_manifest.get("runtime_id", "")})
        self._obs_pipeline.emit_peer_recognized({"peer_id": peer_manifest.get("runtime_id", ""), "status": result["trust_status"]})
        return result

    def verify_peer(self, peer_manifest: dict[str, Any]) -> dict[str, Any]:
        result = self._recognition.verify_peer(peer_manifest)
        if result["trust_status"] == "verified":
            self._obs_pipeline.emit_peer_verified({"peer_id": peer_manifest.get("runtime_id", "")})
        else:
            self._obs_pipeline.emit_peer_rejected({"peer_id": peer_manifest.get("runtime_id", "")})
        return result

    def exchange_trust(
        self,
        local_runtime_id: str,
        peer_runtime_id: str,
        peer_trust_bundle: dict[str, Any],
    ) -> dict[str, Any]:
        result = self._trust_exchange.exchange_trust(local_runtime_id, peer_runtime_id, peer_trust_bundle)
        self._obs_pipeline.emit_trust_exchange_validated(
            {"local": local_runtime_id, "peer": peer_runtime_id, "verified": result["verified"]},
        )
        return result

    def generate_topology_manifest(self, runtime_id: str, **kwargs: Any) -> dict[str, Any]:
        result = self._topology.generate_manifest(runtime_id, **kwargs)
        self._obs_pipeline.emit_topology_manifest_validated({"runtime_id": runtime_id})
        return result

    def generate_capability_manifest(self, runtime_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._capability.generate_manifest(runtime_id, **kwargs)

    def generate_interop_report(
        self,
        local_runtime_id: str,
        peer_runtime_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        result = self._interop.generate_report(local_runtime_id, peer_runtime_id, **kwargs)
        self._obs_pipeline.emit_interoperability_report_generated(
            {"local": local_runtime_id, "peer": peer_runtime_id},
        )
        return result

    def validate_replay_determinism(self) -> dict[str, Any]:
        return self._replay_validator.validate_all()

    def check_boundary(self, limit_name: str, current_value: int) -> dict[str, Any]:
        return self._boundary.check_limit(limit_name, current_value)

    def complete_federation_run(self, run_id: str) -> dict[str, Any]:
        identity_stats = self._identity.get_stats()
        recog_stats = self._recognition.get_stats()
        exchange_stats = self._trust_exchange.get_stats()

        all_ready = all([
            identity_stats["total_identities"] > 0,
            self._identity.all_fingerprinted(),
            self._replay_validator.all_deterministic(),
        ])

        outcome = "ready" if all_ready else "incomplete"
        receipt = FederationVerificationReceipt(
            run_id=run_id,
            outcome=outcome,
            peers_verified=recog_stats["verified"],
            peers_rejected=recog_stats["rejected"],
        )
        self._receipts.append(receipt)
        return receipt.to_dict()

    def get_federation_report(self) -> dict[str, Any]:
        return {
            "identity": self._identity.get_stats(),
            "recognition": self._recognition.get_stats(),
            "trust_exchange": self._trust_exchange.get_stats(),
            "topology": self._topology.get_stats(),
            "capability": self._capability.get_stats(),
            "interop": self._interop.get_stats(),
            "replay_validator": self._replay_validator.get_stats(),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "lifecycle": self._lifecycle.get_stats(),
            "identity": self._identity.get_stats(),
            "recognition": self._recognition.get_stats(),
            "trust_exchange": self._trust_exchange.get_stats(),
            "topology": self._topology.get_stats(),
            "capability": self._capability.get_stats(),
            "interop": self._interop.get_stats(),
            "obs_pipeline": self._obs_pipeline.get_stats(),
            "replay_validator": self._replay_validator.get_stats(),
            "boundary": self._boundary.get_stats(),
            "runs": len(self._runs),
            "receipts": len(self._receipts),
        }
