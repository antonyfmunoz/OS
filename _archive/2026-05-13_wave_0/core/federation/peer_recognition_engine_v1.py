"""Peer Recognition Engine v1.

Parses peer manifests, verifies peer identity format, trust artifact
references, and boundary claims. Classifies peer trust status:
unknown → recognized → verified → untrusted/rejected/expired.

UMH substrate subsystem. Phase 96.8CN.
"""

from __future__ import annotations

from typing import Any

from core.federation.sovereign_federation_readiness_contracts_v1 import (
    RuntimeRecognitionState,
    PeerTrustStatus,
    _now_iso,
    _deterministic_id,
)


MAX_RECOGNITIONS = 200


class PeerRecognitionEngine:
    """Recognizes and classifies peer runtimes."""

    def __init__(self) -> None:
        self._recognitions: list[RuntimeRecognitionState] = []

    def recognize_peer(self, peer_manifest: dict[str, Any]) -> dict[str, Any]:
        if len(self._recognitions) >= MAX_RECOGNITIONS:
            raise ValueError("Max recognitions reached")

        peer_id = peer_manifest.get("runtime_id", "")
        has_id = peer_id != ""
        has_fingerprint = peer_manifest.get("runtime_fingerprint", "") != ""
        has_trust_hash = peer_manifest.get("trust_bundle_hash", "") != ""
        has_boundary = len(peer_manifest.get("boundary_declarations", [])) > 0

        identity_valid = has_id and has_fingerprint
        trust_valid = has_trust_hash
        boundary_valid = has_boundary

        if not identity_valid:
            status = PeerTrustStatus.REJECTED.value
        elif not trust_valid:
            status = PeerTrustStatus.UNTRUSTED.value
        elif not boundary_valid:
            status = PeerTrustStatus.RECOGNIZED.value
        else:
            status = PeerTrustStatus.RECOGNIZED.value

        state = RuntimeRecognitionState(
            recognition_id=_deterministic_id("rrec-", peer_id, _now_iso()),
            peer_runtime_id=peer_id,
            trust_status=status,
            identity_format_valid=identity_valid,
            trust_artifacts_valid=trust_valid,
            boundary_claims_valid=boundary_valid,
        )
        self._recognitions.append(state)
        return state.to_dict()

    def verify_peer(self, peer_manifest: dict[str, Any]) -> dict[str, Any]:
        if len(self._recognitions) >= MAX_RECOGNITIONS:
            raise ValueError("Max recognitions reached")

        peer_id = peer_manifest.get("runtime_id", "")
        has_fingerprint = peer_manifest.get("runtime_fingerprint", "") != ""
        has_trust = peer_manifest.get("trust_bundle_hash", "") != ""
        has_topo = peer_manifest.get("topology_manifest_hash", "") != ""
        has_cap = peer_manifest.get("capability_manifest_hash", "") != ""
        has_boundary = len(peer_manifest.get("boundary_declarations", [])) > 0

        all_valid = has_fingerprint and has_trust and has_topo and has_cap and has_boundary

        status = PeerTrustStatus.VERIFIED.value if all_valid else PeerTrustStatus.UNTRUSTED.value

        state = RuntimeRecognitionState(
            recognition_id=_deterministic_id("rrec-", peer_id, _now_iso()),
            peer_runtime_id=peer_id,
            trust_status=status,
            identity_format_valid=has_fingerprint,
            trust_artifacts_valid=has_trust,
            boundary_claims_valid=has_boundary,
        )
        self._recognitions.append(state)
        return state.to_dict()

    def reject_expired_peer(self, peer_id: str) -> dict[str, Any]:
        if len(self._recognitions) >= MAX_RECOGNITIONS:
            raise ValueError("Max recognitions reached")
        state = RuntimeRecognitionState(
            recognition_id=_deterministic_id("rrec-", peer_id, _now_iso()),
            peer_runtime_id=peer_id,
            trust_status=PeerTrustStatus.EXPIRED.value,
        )
        self._recognitions.append(state)
        return state.to_dict()

    def get_by_status(self, status: str) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._recognitions if r.trust_status == status]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_recognitions": len(self._recognitions),
            "verified": len([r for r in self._recognitions if r.trust_status == "verified"]),
            "rejected": len([r for r in self._recognitions if r.trust_status == "rejected"]),
            "untrusted": len([r for r in self._recognitions if r.trust_status == "untrusted"]),
            "expired": len([r for r in self._recognitions if r.trust_status == "expired"]),
        }
