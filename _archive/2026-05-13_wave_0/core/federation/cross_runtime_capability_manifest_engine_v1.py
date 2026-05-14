"""Cross-Runtime Capability Manifest Engine v1.

Exposes capability categories, required authority class,
allowed interaction types, boundary limits, verification requirements.

Prevents: peer direct execution, peer adapter invocation,
peer governance mutation, hidden capability escalation.

UMH substrate subsystem. Phase 96.8CN.
"""

from __future__ import annotations

from typing import Any

from core.federation.sovereign_federation_readiness_contracts_v1 import (
    FederationCapabilityManifest,
    _now_iso,
    _deterministic_id,
)


MAX_CAPABILITY_MANIFESTS = 100

FORBIDDEN_CAPABILITIES = [
    "peer_direct_execution",
    "peer_adapter_invocation",
    "peer_governance_mutation",
    "hidden_capability_escalation",
]

ALLOWED_INTERACTION_TYPES = [
    "manifest_inspection",
    "trust_verification",
    "topology_comparison",
    "capability_comparison",
    "interoperability_reporting",
]


class CrossRuntimeCapabilityManifestEngine:
    """Generates and validates capability manifests."""

    def __init__(self) -> None:
        self._manifests: list[FederationCapabilityManifest] = []

    def generate_manifest(
        self,
        runtime_id: str,
        capability_categories: list[str] | None = None,
        required_authority_class: str = "sovereign_local",
        allowed_interaction_types: list[str] | None = None,
        boundary_limits: list[str] | None = None,
        verification_requirements: list[str] | None = None,
    ) -> dict[str, Any]:
        if len(self._manifests) >= MAX_CAPABILITY_MANIFESTS:
            raise ValueError("Max capability manifests reached")

        manifest = FederationCapabilityManifest(
            manifest_id=_deterministic_id("fcap-", runtime_id, _now_iso()),
            runtime_id=runtime_id,
            capability_categories=capability_categories or ["verification", "attestation", "trust_exchange"],
            required_authority_class=required_authority_class,
            allowed_interaction_types=allowed_interaction_types or list(ALLOWED_INTERACTION_TYPES),
            boundary_limits=boundary_limits or ["no_peer_execution", "no_authority_transfer"],
            verification_requirements=verification_requirements or ["trust_bundle_hash", "constitutional_proof"],
        )
        self._manifests.append(manifest)
        return manifest.to_dict()

    def validate_manifest(self, manifest: dict[str, Any]) -> dict[str, Any]:
        has_id = manifest.get("runtime_id", "") != ""
        has_caps = len(manifest.get("capability_categories", [])) > 0
        has_interactions = len(manifest.get("allowed_interaction_types", [])) > 0
        has_boundaries = len(manifest.get("boundary_limits", [])) > 0

        interactions = manifest.get("allowed_interaction_types", [])
        no_forbidden = not any(fc in interactions for fc in FORBIDDEN_CAPABILITIES)

        valid = has_id and has_caps and has_interactions and has_boundaries and no_forbidden
        return {
            "valid": valid,
            "has_runtime_id": has_id,
            "has_capabilities": has_caps,
            "has_interactions": has_interactions,
            "has_boundaries": has_boundaries,
            "no_forbidden_capabilities": no_forbidden,
            "timestamp": _now_iso(),
        }

    def check_forbidden(self, capability: str) -> bool:
        return capability in FORBIDDEN_CAPABILITIES

    def get_stats(self) -> dict[str, Any]:
        return {"total_manifests": len(self._manifests)}
