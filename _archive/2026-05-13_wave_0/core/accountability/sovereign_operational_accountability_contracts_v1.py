"""Sovereign Operational Accountability Contracts v1.

15 contracts, 4 enums for temporal constitutional accountability.

The substrate must preserve provable constitutional accountability
across time — not merely within isolated runtime executions.

UMH substrate subsystem. Phase 96.8CL.
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


class AccountabilityPhase(str, Enum):
    DEFINED = "defined"
    RECONSTRUCTING = "reconstructing"
    AUDITING = "auditing"
    VALIDATED = "validated"
    ARCHIVED = "archived"


class AccountabilityEventType(str, Enum):
    ACCOUNTABILITY_STARTED = "accountability_started"
    CHRONOLOGY_RECONSTRUCTED = "chronology_reconstructed"
    GOVERNANCE_HISTORY_RECONSTRUCTED = "governance_history_reconstructed"
    REPLAY_HISTORY_RECONSTRUCTED = "replay_history_reconstructed"
    CONTINUITY_HISTORY_RECONSTRUCTED = "continuity_history_reconstructed"
    PROVENANCE_HISTORY_GENERATED = "provenance_history_generated"
    CONSTITUTIONAL_AUDIT_GENERATED = "constitutional_audit_generated"
    ACCOUNTABILITY_COMPLETED = "accountability_completed"


class AccountabilityDomain(str, Enum):
    GOVERNANCE = "governance"
    REPLAY = "replay"
    CONTINUITY = "continuity"
    TOPOLOGY = "topology"
    DEPLOYMENT = "deployment"
    ORCHESTRATION = "orchestration"
    VALIDATION = "validation"


class HistoricalIntegrityDimension(str, Enum):
    CHRONOLOGY = "chronology"
    PROVENANCE = "provenance"
    REPLAY = "replay"
    GOVERNANCE = "governance"
    CONTINUITY = "continuity"
    DEPLOYMENT = "deployment"


@dataclass
class TemporalAccountabilityState:
    run_id: str
    sessions_covered: int = 0
    chronology_intact: bool = True
    accountability_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.accountability_id:
            self.accountability_id = _deterministic_id(
                "tacct-", self.run_id, str(self.sessions_covered), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "accountability_id": self.accountability_id,
            "run_id": self.run_id,
            "sessions_covered": self.sessions_covered,
            "chronology_intact": self.chronology_intact,
            "created_at": self.created_at,
        }


@dataclass
class ConstitutionalChronologyState:
    domain: str
    entries: int = 0
    monotonic: bool = True
    no_orphans: bool = True
    chronology_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.chronology_id:
            self.chronology_id = _deterministic_id(
                "cchron-", self.domain, str(self.entries), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "chronology_id": self.chronology_id,
            "domain": self.domain,
            "entries": self.entries,
            "monotonic": self.monotonic,
            "no_orphans": self.no_orphans,
            "created_at": self.created_at,
        }


@dataclass
class GovernanceHistoryState:
    decision_count: int = 0
    approvals: int = 0
    denials: int = 0
    timeline_deterministic: bool = True
    history_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.history_id:
            self.history_id = _deterministic_id(
                "ghist-", str(self.decision_count), str(self.approvals), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "history_id": self.history_id,
            "decision_count": self.decision_count,
            "approvals": self.approvals,
            "denials": self.denials,
            "timeline_deterministic": self.timeline_deterministic,
            "created_at": self.created_at,
        }


@dataclass
class ReplayHistoryState:
    generations: int = 0
    restorations: int = 0
    consistency_preserved: bool = True
    history_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.history_id:
            self.history_id = _deterministic_id(
                "rhist-", str(self.generations), str(self.restorations), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "history_id": self.history_id,
            "generations": self.generations,
            "restorations": self.restorations,
            "consistency_preserved": self.consistency_preserved,
            "created_at": self.created_at,
        }


@dataclass
class ContinuityHistoryState:
    checkpoints: int = 0
    restorations: int = 0
    integrity_preserved: bool = True
    history_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.history_id:
            self.history_id = _deterministic_id(
                "chist-", str(self.checkpoints), str(self.restorations), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "history_id": self.history_id,
            "checkpoints": self.checkpoints,
            "restorations": self.restorations,
            "integrity_preserved": self.integrity_preserved,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentHistoryState:
    deployments: int = 0
    rollbacks: int = 0
    all_governed: bool = True
    history_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.history_id:
            self.history_id = _deterministic_id(
                "dhist-", str(self.deployments), str(self.rollbacks), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "history_id": self.history_id,
            "deployments": self.deployments,
            "rollbacks": self.rollbacks,
            "all_governed": self.all_governed,
            "created_at": self.created_at,
        }


@dataclass
class OperationalTimelineState:
    domain: str
    events: int = 0
    monotonic: bool = True
    timeline_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.timeline_id:
            self.timeline_id = _deterministic_id(
                "otl-", self.domain, str(self.events), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "timeline_id": self.timeline_id,
            "domain": self.domain,
            "events": self.events,
            "monotonic": self.monotonic,
            "created_at": self.created_at,
        }


@dataclass
class AccountabilityLineageState:
    source_id: str
    target_id: str
    lineage_type: str = "temporal"
    lineage_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.lineage_id:
            self.lineage_id = _deterministic_id(
                "alin-", self.source_id, self.target_id, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "lineage_id": self.lineage_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "lineage_type": self.lineage_type,
            "created_at": self.created_at,
        }


@dataclass
class AccountabilityReplayState:
    check_name: str
    input_hash: str = ""
    output_hash: str = ""
    deterministic: bool = True
    replay_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.replay_id:
            self.replay_id = _deterministic_id(
                "arplay-", self.check_name, self.input_hash,
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
class AccountabilityProvenanceState:
    graph_name: str
    nodes: int = 0
    edges: int = 0
    deterministic: bool = True
    provenance_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.provenance_id:
            self.provenance_id = _deterministic_id(
                "aprov-", self.graph_name, str(self.nodes), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance_id": self.provenance_id,
            "graph_name": self.graph_name,
            "nodes": self.nodes,
            "edges": self.edges,
            "deterministic": self.deterministic,
            "created_at": self.created_at,
        }


@dataclass
class AccountabilityBoundaryState:
    limit_name: str
    current_value: int = 0
    max_value: int = 0
    exceeded: bool = False
    boundary_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.boundary_id:
            self.boundary_id = _deterministic_id(
                "abnd-", self.limit_name, str(self.current_value), self.created_at,
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
class ConstitutionalAuditState:
    audit_domain: str
    findings: int = 0
    all_compliant: bool = True
    deterministic: bool = True
    audit_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.audit_id:
            self.audit_id = _deterministic_id(
                "caudit-", self.audit_domain, str(self.findings), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "audit_domain": self.audit_domain,
            "findings": self.findings,
            "all_compliant": self.all_compliant,
            "deterministic": self.deterministic,
            "created_at": self.created_at,
        }


@dataclass
class HistoricalIntegrityState:
    chronology_intact: bool = True
    provenance_intact: bool = True
    replay_intact: bool = True
    governance_intact: bool = True
    continuity_intact: bool = True
    deployment_intact: bool = True
    integrity_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.integrity_id:
            self.integrity_id = _deterministic_id(
                "hint-", str(self.chronology_intact),
                str(self.governance_intact), self.created_at,
            )

    @property
    def historical_integrity_score(self) -> float:
        checks = [
            self.chronology_intact, self.provenance_intact,
            self.replay_intact, self.governance_intact,
            self.continuity_intact, self.deployment_intact,
        ]
        return sum(1 for c in checks if c) / len(checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "integrity_id": self.integrity_id,
            "chronology_intact": self.chronology_intact,
            "provenance_intact": self.provenance_intact,
            "replay_intact": self.replay_intact,
            "governance_intact": self.governance_intact,
            "continuity_intact": self.continuity_intact,
            "deployment_intact": self.deployment_intact,
            "historical_integrity_score": self.historical_integrity_score,
            "created_at": self.created_at,
        }


@dataclass
class AccountabilityObservabilityState:
    events_emitted: int = 0
    all_persisted: bool = True
    observability_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.observability_id:
            self.observability_id = _deterministic_id(
                "aobs-", str(self.events_emitted),
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
class SovereignAccountabilityReceipt:
    run_id: str
    outcome: str = "accountable"
    audits_generated: int = 0
    receipt_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.receipt_id:
            self.receipt_id = _deterministic_id(
                "sarcpt-", self.run_id, self.outcome, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "run_id": self.run_id,
            "outcome": self.outcome,
            "audits_generated": self.audits_generated,
            "created_at": self.created_at,
        }
