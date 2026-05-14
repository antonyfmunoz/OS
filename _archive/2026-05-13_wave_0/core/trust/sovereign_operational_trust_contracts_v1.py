"""Sovereign Operational Trust Contracts v1.

15 contracts and 4 enums for portable, externally verifiable
sovereign trust artifacts.

Trust must be independently verifiable from signed/hashed/lineage-linked
artifacts, not merely asserted by the substrate.

UMH substrate subsystem. Phase 96.8CM.
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


class TrustPhase(Enum):
    DEFINED = "defined"
    COLLECTED = "collected"
    HASHED = "hashed"
    BUNDLED = "bundled"
    VERIFIED = "verified"
    EXPORTED = "exported"
    ARCHIVED = "archived"


class TrustEventType(Enum):
    TRUST_BUNDLE_CREATED = "trust_bundle_created"
    TRUST_ARTIFACT_HASHED = "trust_artifact_hashed"
    TRUST_BUNDLE_VERIFIED = "trust_bundle_verified"
    EXTERNAL_VERIFICATION_COMPLETED = "external_verification_completed"
    TRUST_BOUNDARY_DENIED = "trust_boundary_denied"
    TRUST_REPLAY_VALIDATED = "trust_replay_validated"


class TrustDomain(Enum):
    CONSTITUTIONAL = "constitutional"
    CHRONOLOGY = "chronology"
    GOVERNANCE = "governance"
    PROVENANCE = "provenance"
    REPLAY = "replay"
    CONTINUITY = "continuity"
    TOPOLOGY = "topology"
    ACCOUNTABILITY = "accountability"
    EXPLAINABILITY = "explainability"
    VALIDATION = "validation"


class TrustIntegrityDimension(Enum):
    HASH_INTEGRITY = "hash_integrity"
    LINEAGE_INTEGRITY = "lineage_integrity"
    CHRONOLOGY_INTEGRITY = "chronology_integrity"
    GOVERNANCE_INTEGRITY = "governance_integrity"
    REPLAY_INTEGRITY = "replay_integrity"
    PROVENANCE_INTEGRITY = "provenance_integrity"
    BUNDLE_COMPLETENESS = "bundle_completeness"


@dataclass
class SovereignTrustState:
    trust_id: str = ""
    phase: str = "defined"
    created_at: str = field(default_factory=_now_iso)
    domains_collected: list[str] = field(default_factory=list)
    artifacts_hashed: int = 0
    bundles_generated: int = 0
    verifications_completed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "trust_id": self.trust_id or _deterministic_id("strust-", self.created_at),
            "phase": self.phase,
            "created_at": self.created_at,
            "domains_collected": self.domains_collected,
            "artifacts_hashed": self.artifacts_hashed,
            "bundles_generated": self.bundles_generated,
            "verifications_completed": self.verifications_completed,
        }


@dataclass
class TrustArtifact:
    artifact_id: str = ""
    artifact_type: str = ""
    source_path: str = ""
    artifact_hash: str = ""
    timestamp: str = field(default_factory=_now_iso)
    lineage_references: list[str] = field(default_factory=list)
    verification_status: str = "unverified"

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id or _deterministic_id("tart-", self.timestamp, self.artifact_type),
            "artifact_type": self.artifact_type,
            "source_path": self.source_path,
            "artifact_hash": self.artifact_hash,
            "timestamp": self.timestamp,
            "lineage_references": self.lineage_references,
            "verification_status": self.verification_status,
        }


@dataclass
class TrustBundle:
    bundle_id: str = ""
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    bundle_hash: str = ""
    created_at: str = field(default_factory=_now_iso)
    domains_included: list[str] = field(default_factory=list)
    complete: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id or _deterministic_id("tbund-", self.created_at),
            "artifacts_count": len(self.artifacts),
            "bundle_hash": self.bundle_hash,
            "created_at": self.created_at,
            "domains_included": self.domains_included,
            "complete": self.complete,
        }


@dataclass
class TrustProofReceipt:
    receipt_id: str = ""
    run_id: str = ""
    outcome: str = "incomplete"
    bundles_generated: int = 0
    verifications_passed: int = 0
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id or _deterministic_id("trcpt-", self.run_id, self.created_at),
            "run_id": self.run_id,
            "outcome": self.outcome,
            "bundles_generated": self.bundles_generated,
            "verifications_passed": self.verifications_passed,
            "created_at": self.created_at,
        }


@dataclass
class TrustVerificationState:
    verification_id: str = ""
    bundle_id: str = ""
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)
    verified: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verification_id": self.verification_id or _deterministic_id("tvrf-", self.bundle_id, self.timestamp),
            "bundle_id": self.bundle_id,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "verified": self.verified,
            "timestamp": self.timestamp,
        }


@dataclass
class TrustLineageState:
    lineage_id: str = ""
    domain: str = ""
    entries: list[dict[str, Any]] = field(default_factory=list)
    monotonic: bool = True
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lineage_id": self.lineage_id or _deterministic_id("tlin-", self.domain, self.timestamp),
            "domain": self.domain,
            "entries_count": len(self.entries),
            "monotonic": self.monotonic,
            "timestamp": self.timestamp,
        }


@dataclass
class TrustHashState:
    hash_id: str = ""
    source: str = ""
    algorithm: str = "sha256"
    digest: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hash_id": self.hash_id or _deterministic_id("thash-", self.source, self.timestamp),
            "source": self.source,
            "algorithm": self.algorithm,
            "digest": self.digest,
            "timestamp": self.timestamp,
        }


@dataclass
class TrustAttestationState:
    attestation_id: str = ""
    domain: str = ""
    evidence_references: list[str] = field(default_factory=list)
    attested: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "attestation_id": self.attestation_id or _deterministic_id("tatst-", self.domain, self.timestamp),
            "domain": self.domain,
            "evidence_references": self.evidence_references,
            "attested": self.attested,
            "timestamp": self.timestamp,
        }


@dataclass
class TrustBoundaryState:
    boundary_id: str = ""
    action: str = ""
    allowed: bool = False
    reason: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_id": self.boundary_id or _deterministic_id("tbnds-", self.action, self.timestamp),
            "action": self.action,
            "allowed": self.allowed,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class TrustReplayState:
    replay_id: str = ""
    check_name: str = ""
    deterministic: bool = True
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_id": self.replay_id or _deterministic_id("trply-", self.check_name, self.timestamp),
            "check_name": self.check_name,
            "deterministic": self.deterministic,
            "timestamp": self.timestamp,
        }


@dataclass
class ExternalVerificationState:
    verification_id: str = ""
    bundle_id: str = ""
    hash_verified: bool = False
    lineage_verified: bool = False
    chronology_verified: bool = False
    governance_verified: bool = False
    replay_verified: bool = False
    provenance_verified: bool = False
    completeness_verified: bool = False
    timestamp: str = field(default_factory=_now_iso)

    @property
    def trust_integrity_score(self) -> float:
        checks = [
            self.hash_verified,
            self.lineage_verified,
            self.chronology_verified,
            self.governance_verified,
            self.replay_verified,
            self.provenance_verified,
            self.completeness_verified,
        ]
        return sum(1 for c in checks if c) / len(checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verification_id": self.verification_id or _deterministic_id("exvrf-", self.bundle_id, self.timestamp),
            "bundle_id": self.bundle_id,
            "hash_verified": self.hash_verified,
            "lineage_verified": self.lineage_verified,
            "chronology_verified": self.chronology_verified,
            "governance_verified": self.governance_verified,
            "replay_verified": self.replay_verified,
            "provenance_verified": self.provenance_verified,
            "completeness_verified": self.completeness_verified,
            "trust_integrity_score": self.trust_integrity_score,
            "timestamp": self.timestamp,
        }


@dataclass
class ConstitutionalTrustProof:
    proof_id: str = ""
    invariant_certified: bool = False
    governance_preserved: bool = False
    no_execution_outside_spine: bool = False
    no_fabricated_proofs: bool = False
    no_hidden_mutation: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id or _deterministic_id("ctprf-", self.timestamp),
            "invariant_certified": self.invariant_certified,
            "governance_preserved": self.governance_preserved,
            "no_execution_outside_spine": self.no_execution_outside_spine,
            "no_fabricated_proofs": self.no_fabricated_proofs,
            "no_hidden_mutation": self.no_hidden_mutation,
            "timestamp": self.timestamp,
        }


@dataclass
class ProvenanceTrustProof:
    proof_id: str = ""
    causal_lineage_proven: bool = False
    evidence_lineage_proven: bool = False
    source_artifact_lineage_proven: bool = False
    explanation_lineage_proven: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id or _deterministic_id("pvprf-", self.timestamp),
            "causal_lineage_proven": self.causal_lineage_proven,
            "evidence_lineage_proven": self.evidence_lineage_proven,
            "source_artifact_lineage_proven": self.source_artifact_lineage_proven,
            "explanation_lineage_proven": self.explanation_lineage_proven,
            "timestamp": self.timestamp,
        }


@dataclass
class ChronologyTrustProof:
    proof_id: str = ""
    monotonic_proven: bool = False
    no_retroactive_mutation: bool = False
    temporal_integrity_proven: bool = False
    historical_continuity_proven: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id or _deterministic_id("chprf-", self.timestamp),
            "monotonic_proven": self.monotonic_proven,
            "no_retroactive_mutation": self.no_retroactive_mutation,
            "temporal_integrity_proven": self.temporal_integrity_proven,
            "historical_continuity_proven": self.historical_continuity_proven,
            "timestamp": self.timestamp,
        }


@dataclass
class GovernanceTrustProof:
    proof_id: str = ""
    governance_lineage_proven: bool = False
    approval_chain_proven: bool = False
    escalation_lineage_proven: bool = False
    policy_application_proven: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id or _deterministic_id("gvprf-", self.timestamp),
            "governance_lineage_proven": self.governance_lineage_proven,
            "approval_chain_proven": self.approval_chain_proven,
            "escalation_lineage_proven": self.escalation_lineage_proven,
            "policy_application_proven": self.policy_application_proven,
            "timestamp": self.timestamp,
        }
