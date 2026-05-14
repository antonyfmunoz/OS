"""Constitutional Explainability Contracts v1.

15 contracts, 4 enums for deterministic constitutional explainability.

Every governed runtime outcome must be reconstructable into a
deterministic constitutional explanation with full lineage,
causal traceability, governance reasoning, replay justification,
and operational accountability.

UMH substrate subsystem. Phase 96.8CK.
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


class ExplainabilityPhase(str, Enum):
    DEFINED = "defined"
    RECONSTRUCTING = "reconstructing"
    VALIDATING = "validating"
    EXPLAINED = "explained"
    ARCHIVED = "archived"


class ExplainabilityEventType(str, Enum):
    EXPLANATION_REQUESTED = "explanation_requested"
    LINEAGE_RECONSTRUCTED = "lineage_reconstructed"
    GOVERNANCE_REASONING_RECONSTRUCTED = "governance_reasoning_reconstructed"
    REPLAY_EXPLANATION_GENERATED = "replay_explanation_generated"
    CONTINUITY_EXPLANATION_GENERATED = "continuity_explanation_generated"
    PROVENANCE_GRAPH_GENERATED = "provenance_graph_generated"
    CONSTITUTIONAL_REASONING_GENERATED = "constitutional_reasoning_generated"
    EXPLANATION_COMPLETED = "explanation_completed"


class ExplainabilityDomain(str, Enum):
    GOVERNANCE = "governance"
    REPLAY = "replay"
    CONTINUITY = "continuity"
    TOPOLOGY = "topology"
    DEPLOYMENT = "deployment"
    VALIDATION = "validation"
    ORCHESTRATION = "orchestration"
    CERTIFICATION = "certification"


class ReasoningType(str, Enum):
    RULE_REFERENCE = "rule_reference"
    LINEAGE_REFERENCE = "lineage_reference"
    TOPOLOGY_REFERENCE = "topology_reference"
    REPLAY_REFERENCE = "replay_reference"
    POLICY_REFERENCE = "policy_reference"
    RECEIPT_REFERENCE = "receipt_reference"


@dataclass
class ConstitutionalExplanationState:
    domain: str
    decision_id: str
    explanation: str = ""
    explanation_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.explanation_id:
            self.explanation_id = _deterministic_id(
                "cexp-", self.domain, self.decision_id, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "explanation_id": self.explanation_id,
            "domain": self.domain,
            "decision_id": self.decision_id,
            "explanation": self.explanation,
            "created_at": self.created_at,
        }


@dataclass
class RuntimeLineageState:
    source_id: str
    target_id: str
    lineage_type: str = "causal"
    lineage_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.lineage_id:
            self.lineage_id = _deterministic_id(
                "rlin-", self.source_id, self.target_id, self.created_at,
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
class GovernanceReasoningState:
    decision_id: str
    rule_applied: str
    outcome: str = "allowed"
    reasoning_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.reasoning_id:
            self.reasoning_id = _deterministic_id(
                "greas-", self.decision_id, self.rule_applied, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "reasoning_id": self.reasoning_id,
            "decision_id": self.decision_id,
            "rule_applied": self.rule_applied,
            "outcome": self.outcome,
            "created_at": self.created_at,
        }


@dataclass
class ReplayExplanationState:
    replay_id: str
    deterministic: bool = True
    explanation: str = ""
    replay_explanation_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.replay_explanation_id:
            self.replay_explanation_id = _deterministic_id(
                "rexp-", self.replay_id, str(self.deterministic), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_explanation_id": self.replay_explanation_id,
            "replay_id": self.replay_id,
            "deterministic": self.deterministic,
            "explanation": self.explanation,
            "created_at": self.created_at,
        }


@dataclass
class ContinuityExplanationState:
    checkpoint_id: str
    restoration_valid: bool = True
    explanation: str = ""
    continuity_explanation_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.continuity_explanation_id:
            self.continuity_explanation_id = _deterministic_id(
                "ctexp-", self.checkpoint_id, str(self.restoration_valid),
                self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "continuity_explanation_id": self.continuity_explanation_id,
            "checkpoint_id": self.checkpoint_id,
            "restoration_valid": self.restoration_valid,
            "explanation": self.explanation,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentExplanationState:
    deployment_id: str
    governed: bool = True
    explanation: str = ""
    deployment_explanation_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.deployment_explanation_id:
            self.deployment_explanation_id = _deterministic_id(
                "dexp-", self.deployment_id, str(self.governed), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "deployment_explanation_id": self.deployment_explanation_id,
            "deployment_id": self.deployment_id,
            "governed": self.governed,
            "explanation": self.explanation,
            "created_at": self.created_at,
        }


@dataclass
class ValidationExplanationState:
    validation_id: str
    outcome: str = "sovereign"
    explanation: str = ""
    validation_explanation_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.validation_explanation_id:
            self.validation_explanation_id = _deterministic_id(
                "vexp-", self.validation_id, self.outcome, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "validation_explanation_id": self.validation_explanation_id,
            "validation_id": self.validation_id,
            "outcome": self.outcome,
            "explanation": self.explanation,
            "created_at": self.created_at,
        }


@dataclass
class CausalTraceState:
    trace_name: str
    steps: int = 0
    deterministic: bool = True
    trace_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.trace_id:
            self.trace_id = _deterministic_id(
                "ctrace-", self.trace_name, str(self.steps), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "trace_name": self.trace_name,
            "steps": self.steps,
            "deterministic": self.deterministic,
            "created_at": self.created_at,
        }


@dataclass
class OperationalJustificationState:
    operation_id: str
    justification: str = ""
    evidence_count: int = 0
    justified: bool = True
    justification_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.justification_id:
            self.justification_id = _deterministic_id(
                "ojust-", self.operation_id, str(self.evidence_count),
                self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "justification_id": self.justification_id,
            "operation_id": self.operation_id,
            "justification": self.justification,
            "evidence_count": self.evidence_count,
            "justified": self.justified,
            "created_at": self.created_at,
        }


@dataclass
class ConstitutionalAccountabilityState:
    domain: str
    decisions_explained: int = 0
    all_accountable: bool = True
    accountability_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.accountability_id:
            self.accountability_id = _deterministic_id(
                "cacct-", self.domain, str(self.decisions_explained),
                self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "accountability_id": self.accountability_id,
            "domain": self.domain,
            "decisions_explained": self.decisions_explained,
            "all_accountable": self.all_accountable,
            "created_at": self.created_at,
        }


@dataclass
class ProvenanceGraphState:
    graph_name: str
    nodes: int = 0
    edges: int = 0
    deterministic: bool = True
    provenance_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.provenance_id:
            self.provenance_id = _deterministic_id(
                "prov-", self.graph_name, str(self.nodes), self.created_at,
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
class RuntimeNarrativeState:
    narrative_type: str
    source_count: int = 0
    fabricated: bool = False
    narrative_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.narrative_id:
            self.narrative_id = _deterministic_id(
                "rnarr-", self.narrative_type, str(self.source_count),
                self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "narrative_id": self.narrative_id,
            "narrative_type": self.narrative_type,
            "source_count": self.source_count,
            "fabricated": self.fabricated,
            "created_at": self.created_at,
        }


@dataclass
class ExplanationReplayState:
    check_name: str
    input_hash: str = ""
    output_hash: str = ""
    deterministic: bool = True
    replay_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.replay_id:
            self.replay_id = _deterministic_id(
                "exrplay-", self.check_name, self.input_hash,
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
class ExplainabilityObservabilityState:
    events_emitted: int = 0
    all_persisted: bool = True
    observability_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.observability_id:
            self.observability_id = _deterministic_id(
                "exobs-", str(self.events_emitted),
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
class ConstitutionalExplanationReceipt:
    run_id: str
    outcome: str = "explained"
    explanations_generated: int = 0
    receipt_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.receipt_id:
            self.receipt_id = _deterministic_id(
                "exrcpt-", self.run_id, self.outcome, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "run_id": self.run_id,
            "outcome": self.outcome,
            "explanations_generated": self.explanations_generated,
            "created_at": self.created_at,
        }
