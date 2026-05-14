"""Constitutional Runtime Contracts v1.

15 contracts, 5 enums for constitutional runtime consolidation.

The substrate must behave as ONE governed constitutional runtime —
not many loosely aligned subsystems.

This is consolidation/hardening — not a new layer.

UMH substrate subsystem. Phase 96.8CG.
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


class ConstitutionalPhase(str, Enum):
    DEFINED = "defined"
    VALIDATED = "validated"
    CONSOLIDATED = "consolidated"
    HARDENED = "hardened"
    VERIFIED = "verified"
    OPERATIONAL = "operational"
    ARCHIVED = "archived"


class ConstitutionalEventType(str, Enum):
    INVARIANT_VALIDATED = "invariant_validated"
    INVARIANT_VIOLATED = "invariant_violated"
    REPLAY_SEMANTICS_VALIDATED = "replay_semantics_validated"
    LIFECYCLE_SEMANTICS_VALIDATED = "lifecycle_semantics_validated"
    TOPOLOGY_SEMANTICS_VALIDATED = "topology_semantics_validated"
    CONTINUITY_SEMANTICS_VALIDATED = "continuity_semantics_validated"
    CONSTITUTIONAL_REPLAY_VALIDATED = "constitutional_replay_validated"


class InvariantDomain(str, Enum):
    GOVERNANCE = "governance"
    REPLAY = "replay"
    CONTINUITY = "continuity"
    LIFECYCLE = "lifecycle"
    TOPOLOGY = "topology"
    OBSERVABILITY = "observability"
    SCALING = "scaling"
    RESILIENCE = "resilience"


class SemanticDriftType(str, Enum):
    REPLAY_DRIFT = "replay_drift"
    LIFECYCLE_DRIFT = "lifecycle_drift"
    TOPOLOGY_DRIFT = "topology_drift"
    CONTINUITY_DRIFT = "continuity_drift"
    OBSERVABILITY_DRIFT = "observability_drift"
    GOVERNANCE_DRIFT = "governance_drift"


class ViolationSeverity(str, Enum):
    WARNING = "warning"
    VIOLATION = "violation"
    CRITICAL = "critical"


@dataclass
class ConstitutionalInvariant:
    domain: str
    name: str
    description: str = ""
    enforced: bool = True
    invariant_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.invariant_id:
            self.invariant_id = _deterministic_id(
                "cinv-", self.domain, self.name,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "invariant_id": self.invariant_id,
            "domain": self.domain,
            "name": self.name,
            "description": self.description,
            "enforced": self.enforced,
            "created_at": self.created_at,
        }


@dataclass
class RuntimeConstitutionState:
    phase: str = "defined"
    invariants_validated: int = 0
    invariants_violated: int = 0
    state_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.state_id:
            self.state_id = _deterministic_id(
                "rcst-", self.phase, str(self.invariants_validated),
                self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "phase": self.phase,
            "invariants_validated": self.invariants_validated,
            "invariants_violated": self.invariants_violated,
            "created_at": self.created_at,
        }


@dataclass
class UnifiedGovernanceState:
    layers_validated: int = 0
    governance_coherent: bool = True
    governance_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.governance_id:
            self.governance_id = _deterministic_id(
                "ugov-", str(self.layers_validated),
                str(self.governance_coherent), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "governance_id": self.governance_id,
            "layers_validated": self.layers_validated,
            "governance_coherent": self.governance_coherent,
            "created_at": self.created_at,
        }


@dataclass
class UnifiedReplayState:
    checks_passed: int = 0
    checks_failed: int = 0
    deterministic: bool = True
    replay_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.replay_id:
            self.replay_id = _deterministic_id(
                "ureplay-", str(self.checks_passed),
                str(self.deterministic), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_id": self.replay_id,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "deterministic": self.deterministic,
            "created_at": self.created_at,
        }


@dataclass
class UnifiedContinuityState:
    layers_synchronized: int = 0
    continuity_coherent: bool = True
    continuity_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.continuity_id:
            self.continuity_id = _deterministic_id(
                "ucont-", str(self.layers_synchronized),
                str(self.continuity_coherent), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "continuity_id": self.continuity_id,
            "layers_synchronized": self.layers_synchronized,
            "continuity_coherent": self.continuity_coherent,
            "created_at": self.created_at,
        }


@dataclass
class UnifiedTopologyState:
    topologies_validated: int = 0
    topology_coherent: bool = True
    drift_detected: bool = False
    topology_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.topology_id:
            self.topology_id = _deterministic_id(
                "utopo-", str(self.topologies_validated),
                str(self.topology_coherent), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_id": self.topology_id,
            "topologies_validated": self.topologies_validated,
            "topology_coherent": self.topology_coherent,
            "drift_detected": self.drift_detected,
            "created_at": self.created_at,
        }


@dataclass
class UnifiedLifecycleState:
    layers_validated: int = 0
    lifecycle_coherent: bool = True
    lifecycle_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.lifecycle_id:
            self.lifecycle_id = _deterministic_id(
                "ulife-", str(self.layers_validated),
                str(self.lifecycle_coherent), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "lifecycle_id": self.lifecycle_id,
            "layers_validated": self.layers_validated,
            "lifecycle_coherent": self.lifecycle_coherent,
            "created_at": self.created_at,
        }


@dataclass
class UnifiedObservabilityState:
    pipelines_validated: int = 0
    observability_coherent: bool = True
    observability_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.observability_id:
            self.observability_id = _deterministic_id(
                "uobs-", str(self.pipelines_validated),
                str(self.observability_coherent), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "observability_id": self.observability_id,
            "pipelines_validated": self.pipelines_validated,
            "observability_coherent": self.observability_coherent,
            "created_at": self.created_at,
        }


@dataclass
class UnifiedBoundaryState:
    policies_validated: int = 0
    boundaries_coherent: bool = True
    boundary_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.boundary_id:
            self.boundary_id = _deterministic_id(
                "ubnd-", str(self.policies_validated),
                str(self.boundaries_coherent), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_id": self.boundary_id,
            "policies_validated": self.policies_validated,
            "boundaries_coherent": self.boundaries_coherent,
            "created_at": self.created_at,
        }


@dataclass
class UnifiedTrustState:
    trust_tiers_validated: int = 0
    trust_coherent: bool = True
    trust_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.trust_id:
            self.trust_id = _deterministic_id(
                "utrust-", str(self.trust_tiers_validated),
                str(self.trust_coherent), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "trust_id": self.trust_id,
            "trust_tiers_validated": self.trust_tiers_validated,
            "trust_coherent": self.trust_coherent,
            "created_at": self.created_at,
        }


@dataclass
class ConstitutionalReceipt:
    action: str
    outcome: str = "validated"
    receipt_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.receipt_id:
            self.receipt_id = _deterministic_id(
                "crcpt-", self.action, self.outcome, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "action": self.action,
            "outcome": self.outcome,
            "created_at": self.created_at,
        }


@dataclass
class ConstitutionalReplayState:
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
class ConstitutionalViolationState:
    invariant_id: str
    domain: str
    severity: str = "violation"
    description: str = ""
    violation_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.violation_id:
            self.violation_id = _deterministic_id(
                "cviol-", self.invariant_id, self.domain,
                self.severity, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "violation_id": self.violation_id,
            "invariant_id": self.invariant_id,
            "domain": self.domain,
            "severity": self.severity,
            "description": self.description,
            "created_at": self.created_at,
        }


@dataclass
class ConstitutionalProofState:
    domain: str
    proof_type: str = "invariant_validation"
    content_hash: str = ""
    proof_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.proof_id:
            self.proof_id = _deterministic_id(
                "cproof-", self.domain, self.proof_type,
                self.content_hash, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "domain": self.domain,
            "proof_type": self.proof_type,
            "content_hash": self.content_hash,
            "created_at": self.created_at,
        }


@dataclass
class RuntimeCoherenceState:
    layers_checked: int = 0
    coherent: bool = True
    drift_domains: list[str] = field(default_factory=list)
    coherence_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.coherence_id:
            self.coherence_id = _deterministic_id(
                "rcoher-", str(self.layers_checked),
                str(self.coherent), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "coherence_id": self.coherence_id,
            "layers_checked": self.layers_checked,
            "coherent": self.coherent,
            "drift_domains": list(self.drift_domains),
            "created_at": self.created_at,
        }
