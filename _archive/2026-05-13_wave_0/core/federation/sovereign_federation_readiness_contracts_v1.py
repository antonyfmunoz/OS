"""Sovereign Federation Readiness Contracts v1.

15 contracts and 4 enums for sovereign federation readiness —
verifiable coordination between sovereign runtimes without
transferring sovereignty, authority, cognition, governance,
or execution control.

UMH substrate subsystem. Phase 96.8CN.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _deterministic_id(prefix: str, *parts: str) -> str:
    raw = "|".join(parts)
    h = hashlib.sha256(raw.encode()).hexdigest()[:12]
    return f"{prefix}{h}"


class FederationPhase(Enum):
    IDENTITY_CREATED = "identity_created"
    MANIFEST_GENERATED = "manifest_generated"
    PEER_RECEIVED = "peer_received"
    PEER_VERIFIED = "peer_verified"
    PEER_REJECTED = "peer_rejected"
    INTEROPERABILITY_REPORTED = "interoperability_reported"
    ARCHIVED = "archived"


class FederationEventType(Enum):
    RUNTIME_IDENTITY_CREATED = "runtime_identity_created"
    PEER_MANIFEST_RECEIVED = "peer_manifest_received"
    PEER_RECOGNIZED = "peer_recognized"
    PEER_VERIFIED = "peer_verified"
    PEER_REJECTED = "peer_rejected"
    TRUST_EXCHANGE_VALIDATED = "trust_exchange_validated"
    TOPOLOGY_MANIFEST_VALIDATED = "topology_manifest_validated"
    FEDERATION_BOUNDARY_DENIED = "federation_boundary_denied"
    INTEROPERABILITY_REPORT_GENERATED = "interoperability_report_generated"


class PeerTrustStatus(Enum):
    UNKNOWN = "unknown"
    RECOGNIZED = "recognized"
    VERIFIED = "verified"
    UNTRUSTED = "untrusted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class FederationDomain(Enum):
    IDENTITY = "identity"
    TRUST_EXCHANGE = "trust_exchange"
    TOPOLOGY = "topology"
    CAPABILITY = "capability"
    INTEROPERABILITY = "interoperability"
    VERIFICATION = "verification"
    BOUNDARY = "boundary"
    CONTINUITY = "continuity"


@dataclass
class SovereignRuntimeIdentity:
    runtime_id: str = ""
    runtime_fingerprint: str = ""
    trust_bundle_reference: str = ""
    constitutional_attestation_reference: str = ""
    topology_reference: str = ""
    capability_manifest_reference: str = ""
    verification_hash: str = ""
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id or _deterministic_id("srid-", self.created_at),
            "runtime_fingerprint": self.runtime_fingerprint,
            "trust_bundle_reference": self.trust_bundle_reference,
            "constitutional_attestation_reference": self.constitutional_attestation_reference,
            "topology_reference": self.topology_reference,
            "capability_manifest_reference": self.capability_manifest_reference,
            "verification_hash": self.verification_hash,
            "created_at": self.created_at,
        }


@dataclass
class FederationReadinessState:
    readiness_id: str = ""
    phase: str = "identity_created"
    local_identity_registered: bool = False
    peers_recognized: int = 0
    peers_verified: int = 0
    peers_rejected: int = 0
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "readiness_id": self.readiness_id or _deterministic_id("fready-", self.created_at),
            "phase": self.phase,
            "local_identity_registered": self.local_identity_registered,
            "peers_recognized": self.peers_recognized,
            "peers_verified": self.peers_verified,
            "peers_rejected": self.peers_rejected,
            "created_at": self.created_at,
        }


@dataclass
class FederationTrustExchange:
    exchange_id: str = ""
    local_runtime_id: str = ""
    peer_runtime_id: str = ""
    trust_bundle_exchanged: bool = False
    attestation_exchanged: bool = False
    verified: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "exchange_id": self.exchange_id or _deterministic_id("ftex-", self.local_runtime_id, self.peer_runtime_id, self.timestamp),
            "local_runtime_id": self.local_runtime_id,
            "peer_runtime_id": self.peer_runtime_id,
            "trust_bundle_exchanged": self.trust_bundle_exchanged,
            "attestation_exchanged": self.attestation_exchanged,
            "verified": self.verified,
            "timestamp": self.timestamp,
        }


@dataclass
class RuntimeRecognitionState:
    recognition_id: str = ""
    peer_runtime_id: str = ""
    trust_status: str = "unknown"
    identity_format_valid: bool = False
    trust_artifacts_valid: bool = False
    boundary_claims_valid: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recognition_id": self.recognition_id or _deterministic_id("rrec-", self.peer_runtime_id, self.timestamp),
            "peer_runtime_id": self.peer_runtime_id,
            "trust_status": self.trust_status,
            "identity_format_valid": self.identity_format_valid,
            "trust_artifacts_valid": self.trust_artifacts_valid,
            "boundary_claims_valid": self.boundary_claims_valid,
            "timestamp": self.timestamp,
        }


@dataclass
class FederationTopologyManifest:
    manifest_id: str = ""
    runtime_id: str = ""
    environment_classes: list[str] = field(default_factory=list)
    capability_categories: list[str] = field(default_factory=list)
    trust_tier: str = ""
    boundary_declarations: list[str] = field(default_factory=list)
    interoperability_surfaces: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id or _deterministic_id("ftopo-", self.runtime_id, self.timestamp),
            "runtime_id": self.runtime_id,
            "environment_classes": self.environment_classes,
            "capability_categories": self.capability_categories,
            "trust_tier": self.trust_tier,
            "boundary_declarations": self.boundary_declarations,
            "interoperability_surfaces": self.interoperability_surfaces,
            "timestamp": self.timestamp,
        }


@dataclass
class FederationBoundaryState:
    boundary_id: str = ""
    action: str = ""
    allowed: bool = False
    reason: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_id": self.boundary_id or _deterministic_id("fbnds-", self.action, self.timestamp),
            "action": self.action,
            "allowed": self.allowed,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class FederationVerificationReceipt:
    receipt_id: str = ""
    run_id: str = ""
    outcome: str = "incomplete"
    peers_verified: int = 0
    peers_rejected: int = 0
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id or _deterministic_id("frcpt-", self.run_id, self.created_at),
            "run_id": self.run_id,
            "outcome": self.outcome,
            "peers_verified": self.peers_verified,
            "peers_rejected": self.peers_rejected,
            "created_at": self.created_at,
        }


@dataclass
class FederationInteroperabilityState:
    interop_id: str = ""
    local_runtime_id: str = ""
    peer_runtime_id: str = ""
    trust_compatible: bool = False
    topology_compatible: bool = False
    capability_compatible: bool = False
    boundary_compatible: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "interop_id": self.interop_id or _deterministic_id("fintop-", self.local_runtime_id, self.peer_runtime_id, self.timestamp),
            "local_runtime_id": self.local_runtime_id,
            "peer_runtime_id": self.peer_runtime_id,
            "trust_compatible": self.trust_compatible,
            "topology_compatible": self.topology_compatible,
            "capability_compatible": self.capability_compatible,
            "boundary_compatible": self.boundary_compatible,
            "timestamp": self.timestamp,
        }


@dataclass
class CrossRuntimeTrustBundle:
    bundle_id: str = ""
    source_runtime_id: str = ""
    trust_bundle_hash: str = ""
    constitutional_proof_hash: str = ""
    chronology_proof_hash: str = ""
    provenance_proof_hash: str = ""
    governance_proof_hash: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id or _deterministic_id("crtb-", self.source_runtime_id, self.timestamp),
            "source_runtime_id": self.source_runtime_id,
            "trust_bundle_hash": self.trust_bundle_hash,
            "constitutional_proof_hash": self.constitutional_proof_hash,
            "chronology_proof_hash": self.chronology_proof_hash,
            "provenance_proof_hash": self.provenance_proof_hash,
            "governance_proof_hash": self.governance_proof_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class CrossRuntimeLineageReference:
    reference_id: str = ""
    source_runtime_id: str = ""
    lineage_type: str = ""
    lineage_hash: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_id": self.reference_id or _deterministic_id("crlin-", self.source_runtime_id, self.lineage_type, self.timestamp),
            "source_runtime_id": self.source_runtime_id,
            "lineage_type": self.lineage_type,
            "lineage_hash": self.lineage_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class FederationContinuityState:
    continuity_id: str = ""
    federation_session_id: str = ""
    peers_active: int = 0
    exchanges_completed: int = 0
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "continuity_id": self.continuity_id or _deterministic_id("fcont-", self.federation_session_id, self.timestamp),
            "federation_session_id": self.federation_session_id,
            "peers_active": self.peers_active,
            "exchanges_completed": self.exchanges_completed,
            "timestamp": self.timestamp,
        }


@dataclass
class FederationReplayState:
    replay_id: str = ""
    check_name: str = ""
    deterministic: bool = True
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_id": self.replay_id or _deterministic_id("frply-", self.check_name, self.timestamp),
            "check_name": self.check_name,
            "deterministic": self.deterministic,
            "timestamp": self.timestamp,
        }


@dataclass
class FederationObservabilityState:
    event_id: str = ""
    event_type: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id or _deterministic_id("fobs-", self.event_type, self.timestamp),
            "event_type": self.event_type,
            "details": self.details,
            "timestamp": self.timestamp,
        }


@dataclass
class FederationCapabilityManifest:
    manifest_id: str = ""
    runtime_id: str = ""
    capability_categories: list[str] = field(default_factory=list)
    required_authority_class: str = ""
    allowed_interaction_types: list[str] = field(default_factory=list)
    boundary_limits: list[str] = field(default_factory=list)
    verification_requirements: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id or _deterministic_id("fcap-", self.runtime_id, self.timestamp),
            "runtime_id": self.runtime_id,
            "capability_categories": self.capability_categories,
            "required_authority_class": self.required_authority_class,
            "allowed_interaction_types": self.allowed_interaction_types,
            "boundary_limits": self.boundary_limits,
            "verification_requirements": self.verification_requirements,
            "timestamp": self.timestamp,
        }


@dataclass
class SovereignPeerManifest:
    manifest_id: str = ""
    runtime_id: str = ""
    runtime_fingerprint: str = ""
    trust_bundle_hash: str = ""
    topology_manifest_hash: str = ""
    capability_manifest_hash: str = ""
    boundary_declarations: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id or _deterministic_id("spman-", self.runtime_id, self.timestamp),
            "runtime_id": self.runtime_id,
            "runtime_fingerprint": self.runtime_fingerprint,
            "trust_bundle_hash": self.trust_bundle_hash,
            "topology_manifest_hash": self.topology_manifest_hash,
            "capability_manifest_hash": self.capability_manifest_hash,
            "boundary_declarations": self.boundary_declarations,
            "timestamp": self.timestamp,
        }
