"""Runtime Certification Contracts v1.

15 contracts, 5 enums for operational runtime certification.

Certification validates SYSTEM-WIDE constitutional truth —
not module-local correctness.

UMH substrate subsystem. Phase 96.8CI.
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


class CertificationPhase(str, Enum):
    DEFINED = "defined"
    STAGED = "staged"
    VALIDATING = "validating"
    CERTIFIED = "certified"
    ARCHIVED = "archived"


class CertificationEventType(str, Enum):
    CERTIFICATION_STARTED = "certification_started"
    CERTIFICATION_COMPLETED = "certification_completed"
    INVARIANT_VERIFIED = "invariant_verified"
    INVARIANT_FAILED = "invariant_failed"
    REPLAY_CERTIFIED = "replay_certified"
    CONTINUITY_CERTIFIED = "continuity_certified"
    TOPOLOGY_CERTIFIED = "topology_certified"
    SEMANTIC_CONSISTENCY_VERIFIED = "semantic_consistency_verified"
    RUNTIME_ATTESTATION_GENERATED = "runtime_attestation_generated"


class CertificationDomain(str, Enum):
    GOVERNANCE = "governance"
    REPLAY = "replay"
    CONTINUITY = "continuity"
    TOPOLOGY = "topology"
    OBSERVABILITY = "observability"
    LIFECYCLE = "lifecycle"
    ORCHESTRATION = "orchestration"
    APPLICATION = "application"
    DEPLOYMENT = "deployment"
    RESILIENCE = "resilience"


class GuaranteeType(str, Enum):
    REPLAY_DETERMINISM = "replay_determinism"
    TOPOLOGY_BOUNDEDNESS = "topology_boundedness"
    GOVERNANCE_ENFORCEMENT = "governance_enforcement"
    CONTINUITY_RESTORATION = "continuity_restoration"
    CONSTITUTIONAL_CONSISTENCY = "constitutional_consistency"
    EXECUTION_ROUTING = "execution_routing"
    OBSERVABILITY_COMPLETENESS = "observability_completeness"
    DEPLOYMENT_BOUNDEDNESS = "deployment_boundedness"


class ViolationSeverity(str, Enum):
    WARNING = "warning"
    VIOLATION = "violation"
    CRITICAL = "critical"


@dataclass
class RuntimeCertificationState:
    run_id: str
    certified: bool = False
    domains_checked: int = 0
    domains_passed: int = 0
    certification_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.certification_id:
            self.certification_id = _deterministic_id(
                "rcert-", self.run_id, str(self.certified), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "certification_id": self.certification_id,
            "run_id": self.run_id,
            "certified": self.certified,
            "domains_checked": self.domains_checked,
            "domains_passed": self.domains_passed,
            "created_at": self.created_at,
        }


@dataclass
class ConstitutionalInvariantState:
    domain: str
    invariant_name: str
    enforced: bool = True
    invariant_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.invariant_id:
            self.invariant_id = _deterministic_id(
                "cinvs-", self.domain, self.invariant_name, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "invariant_id": self.invariant_id,
            "domain": self.domain,
            "invariant_name": self.invariant_name,
            "enforced": self.enforced,
            "created_at": self.created_at,
        }


@dataclass
class CertificationScope:
    scope_name: str
    domains: list[str] = field(default_factory=list)
    scope_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.scope_id:
            self.scope_id = _deterministic_id(
                "cscope-", self.scope_name, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope_id": self.scope_id,
            "scope_name": self.scope_name,
            "domains": self.domains,
            "created_at": self.created_at,
        }


@dataclass
class CertificationBoundaryState:
    limit_name: str
    current_value: int = 0
    max_value: int = 0
    exceeded: bool = False
    boundary_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.boundary_id:
            self.boundary_id = _deterministic_id(
                "cbnd-", self.limit_name, str(self.current_value),
                self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_id": self.boundary_id,
            "limit_name": self.limit_name,
            "current_value": self.current_value,
            "max_value": self.max_value,
            "exceeded": self.exceeded,
            "created_at": self.created_at,
        }


@dataclass
class CertificationReplayState:
    check_name: str
    input_hash: str = ""
    output_hash: str = ""
    deterministic: bool = True
    replay_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.replay_id:
            self.replay_id = _deterministic_id(
                "crplay-", self.check_name, self.input_hash,
                self.output_hash, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_id": self.replay_id,
            "check_name": self.check_name,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "deterministic": self.deterministic,
            "created_at": self.created_at,
        }


@dataclass
class CertificationObservabilityState:
    events_emitted: int = 0
    all_persisted: bool = True
    observability_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.observability_id:
            self.observability_id = _deterministic_id(
                "cobs-", str(self.events_emitted),
                str(self.all_persisted), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "observability_id": self.observability_id,
            "events_emitted": self.events_emitted,
            "all_persisted": self.all_persisted,
            "created_at": self.created_at,
        }


@dataclass
class CertificationLifecycleState:
    phase: str = "defined"
    transitions: int = 0
    lifecycle_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.lifecycle_id:
            self.lifecycle_id = _deterministic_id(
                "clc-", self.phase, str(self.transitions), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "lifecycle_id": self.lifecycle_id,
            "phase": self.phase,
            "transitions": self.transitions,
            "created_at": self.created_at,
        }


@dataclass
class RuntimeAttestation:
    run_id: str
    all_certified: bool = False
    invariants_verified: int = 0
    guarantees_issued: int = 0
    attestation_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.attestation_id:
            self.attestation_id = _deterministic_id(
                "rattest-", self.run_id, str(self.all_certified),
                self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "attestation_id": self.attestation_id,
            "run_id": self.run_id,
            "all_certified": self.all_certified,
            "invariants_verified": self.invariants_verified,
            "guarantees_issued": self.guarantees_issued,
            "created_at": self.created_at,
        }


@dataclass
class RuntimeGuarantee:
    guarantee_type: str
    domain: str
    guaranteed: bool = True
    guarantee_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.guarantee_id:
            self.guarantee_id = _deterministic_id(
                "rguarant-", self.guarantee_type, self.domain, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "guarantee_id": self.guarantee_id,
            "guarantee_type": self.guarantee_type,
            "domain": self.domain,
            "guaranteed": self.guaranteed,
            "created_at": self.created_at,
        }


@dataclass
class RuntimeViolation:
    domain: str
    invariant_name: str
    severity: str = "violation"
    violation_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.violation_id:
            self.violation_id = _deterministic_id(
                "rviol-", self.domain, self.invariant_name, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "violation_id": self.violation_id,
            "domain": self.domain,
            "invariant_name": self.invariant_name,
            "severity": self.severity,
            "created_at": self.created_at,
        }


@dataclass
class RuntimeCertificationReceipt:
    run_id: str
    outcome: str = "certified"
    domains_certified: int = 0
    receipt_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.receipt_id:
            self.receipt_id = _deterministic_id(
                "rcrcpt-", self.run_id, self.outcome, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "run_id": self.run_id,
            "outcome": self.outcome,
            "domains_certified": self.domains_certified,
            "created_at": self.created_at,
        }


@dataclass
class CrossLayerInvariantState:
    source_domain: str
    target_domain: str
    consistent: bool = True
    cross_layer_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.cross_layer_id:
            self.cross_layer_id = _deterministic_id(
                "clinv-", self.source_domain, self.target_domain,
                self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cross_layer_id": self.cross_layer_id,
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "consistent": self.consistent,
            "created_at": self.created_at,
        }


@dataclass
class ConstitutionalSemanticState:
    semantic_domain: str
    coherent: bool = True
    layers_checked: int = 0
    semantic_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.semantic_id:
            self.semantic_id = _deterministic_id(
                "csem-", self.semantic_domain, str(self.coherent),
                self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_id": self.semantic_id,
            "semantic_domain": self.semantic_domain,
            "coherent": self.coherent,
            "layers_checked": self.layers_checked,
            "created_at": self.created_at,
        }


@dataclass
class RuntimeTopologyGuarantee:
    no_orphans: bool = True
    no_hidden_mutation: bool = True
    no_recursive_growth: bool = True
    bounded: bool = True
    topology_guarantee_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.topology_guarantee_id:
            self.topology_guarantee_id = _deterministic_id(
                "rtguar-", str(self.no_orphans), str(self.bounded),
                self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_guarantee_id": self.topology_guarantee_id,
            "no_orphans": self.no_orphans,
            "no_hidden_mutation": self.no_hidden_mutation,
            "no_recursive_growth": self.no_recursive_growth,
            "bounded": self.bounded,
            "created_at": self.created_at,
        }


@dataclass
class RuntimeContinuityGuarantee:
    checkpoint_integrity: bool = True
    session_continuity: bool = True
    workflow_restoration: bool = True
    replay_restoration: bool = True
    chronology_preserved: bool = True
    continuity_guarantee_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.continuity_guarantee_id:
            self.continuity_guarantee_id = _deterministic_id(
                "rcguar-", str(self.checkpoint_integrity),
                str(self.chronology_preserved), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "continuity_guarantee_id": self.continuity_guarantee_id,
            "checkpoint_integrity": self.checkpoint_integrity,
            "session_continuity": self.session_continuity,
            "workflow_restoration": self.workflow_restoration,
            "replay_restoration": self.replay_restoration,
            "chronology_preserved": self.chronology_preserved,
            "created_at": self.created_at,
        }
