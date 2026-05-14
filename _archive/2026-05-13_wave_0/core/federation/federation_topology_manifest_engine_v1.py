"""Federation Topology Manifest Engine v1.

Generates topology manifests exposing only: runtime identity,
environment classes, capability categories, trust tier declarations,
boundary declarations, interoperability surfaces.

Never exposes: secrets, private runtime state, operator-private data,
unapproved memory, internal cognition state.

UMH substrate subsystem. Phase 96.8CN.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from core.federation.sovereign_federation_readiness_contracts_v1 import (
    FederationTopologyManifest,
    _now_iso,
    _deterministic_id,
)


MAX_MANIFESTS = 100

FORBIDDEN_EXPOSURES = [
    "secrets",
    "private_runtime_state",
    "operator_private_data",
    "unapproved_memory",
    "internal_cognition_state",
]


class FederationTopologyManifestEngine:
    """Generates and validates topology manifests."""

    def __init__(self) -> None:
        self._manifests: list[FederationTopologyManifest] = []

    def generate_manifest(
        self,
        runtime_id: str,
        environment_classes: list[str] | None = None,
        capability_categories: list[str] | None = None,
        trust_tier: str = "standard",
        boundary_declarations: list[str] | None = None,
        interoperability_surfaces: list[str] | None = None,
    ) -> dict[str, Any]:
        if len(self._manifests) >= MAX_MANIFESTS:
            raise ValueError("Max manifests reached")

        manifest = FederationTopologyManifest(
            manifest_id=_deterministic_id("ftopo-", runtime_id, _now_iso()),
            runtime_id=runtime_id,
            environment_classes=environment_classes or ["substrate"],
            capability_categories=capability_categories or ["verification", "attestation"],
            trust_tier=trust_tier,
            boundary_declarations=boundary_declarations or ["no_peer_execution", "no_authority_transfer"],
            interoperability_surfaces=interoperability_surfaces or ["trust_exchange", "manifest_inspection"],
        )
        self._manifests.append(manifest)
        return manifest.to_dict()

    def validate_manifest(self, manifest: dict[str, Any]) -> dict[str, Any]:
        has_id = manifest.get("runtime_id", "") != ""
        has_env = len(manifest.get("environment_classes", [])) > 0
        has_cap = len(manifest.get("capability_categories", [])) > 0
        has_boundary = len(manifest.get("boundary_declarations", [])) > 0

        valid = has_id and has_env and has_cap and has_boundary
        return {
            "valid": valid,
            "has_runtime_id": has_id,
            "has_environment_classes": has_env,
            "has_capability_categories": has_cap,
            "has_boundary_declarations": has_boundary,
            "timestamp": _now_iso(),
        }

    def compute_manifest_hash(self, manifest: dict[str, Any]) -> str:
        canonical = json.dumps(manifest, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def get_stats(self) -> dict[str, Any]:
        return {"total_manifests": len(self._manifests)}
