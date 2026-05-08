"""Canonical World Model v1 for the UMH substrate layer.

Stores governed truth — reality structures that have been promoted
through governance review from world-model candidates.

Canonical truth is not generated. Canonical truth is promoted
through governed transition.

UMH substrate subsystem. Phase 96.8Y.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


FORBIDDEN_CANONICAL_ACTIONS = frozenset(
    {
        "self_mutate",
        "recursive_rewrite",
        "auto_promote_new_truths",
        "trigger_execution",
        "reinterpret_observations",
        "bypass_governance",
        "circular_truth_reference",
        "ungrounded_entity_generation",
        "silent_ontology_mutation",
        "self_reinforcing_promotion",
    }
)


@dataclass
class CanonicalLineageReference:
    """Full lineage chain for a canonical truth record."""

    extraction_state_id: str = ""
    normalization_state_id: str = ""
    interpretation_state_id: str = ""
    candidate_state_id: str = ""
    governance_state_id: str = ""
    trace_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "extraction_state_id": self.extraction_state_id,
            "normalization_state_id": self.normalization_state_id,
            "interpretation_state_id": self.interpretation_state_id,
            "candidate_state_id": self.candidate_state_id,
            "governance_state_id": self.governance_state_id,
            "trace_id": self.trace_id,
        }


@dataclass
class CanonicalGovernanceReceipt:
    """Proof that governance approved this canonical truth."""

    receipt_id: str
    governance_reference: str
    approved_by: str
    approval_timestamp: str = ""
    candidate_hash: str = ""
    decision: str = "approved"
    review_notes: str = ""

    def __post_init__(self) -> None:
        if not self.approval_timestamp:
            self.approval_timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "governance_reference": self.governance_reference,
            "approved_by": self.approved_by,
            "approval_timestamp": self.approval_timestamp,
            "candidate_hash": self.candidate_hash,
            "decision": self.decision,
            "review_notes": self.review_notes,
        }


@dataclass
class CanonicalEntity:
    """A canonical entity — governed truth."""

    entity_id: str
    entity_type: str
    label: str
    confidence: float
    source_candidate_entity_id: str = ""
    source_observation_ids: list[str] = field(default_factory=list)
    governance_receipt_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "label": self.label,
            "confidence": self.confidence,
            "source_candidate_entity_id": self.source_candidate_entity_id,
            "source_observation_ids": self.source_observation_ids,
            "governance_receipt_id": self.governance_receipt_id,
        }


@dataclass
class CanonicalRelationship:
    """A canonical relationship — governed truth."""

    relationship_id: str
    from_entity_id: str
    to_entity_id: str
    relationship_type: str
    confidence: float
    source_candidate_relationship_id: str = ""
    governance_receipt_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "from_entity_id": self.from_entity_id,
            "to_entity_id": self.to_entity_id,
            "relationship_type": self.relationship_type,
            "confidence": self.confidence,
            "source_candidate_relationship_id": self.source_candidate_relationship_id,
            "governance_receipt_id": self.governance_receipt_id,
        }


@dataclass
class CanonicalConstraint:
    """A canonical constraint — governed truth."""

    constraint_id: str
    constraint_type: str
    description: str
    applies_to_entity_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    governance_receipt_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "constraint_type": self.constraint_type,
            "description": self.description,
            "applies_to_entity_ids": self.applies_to_entity_ids,
            "confidence": self.confidence,
            "governance_receipt_id": self.governance_receipt_id,
        }


@dataclass
class CanonicalCausalGraph:
    """A canonical causal graph — governed truth."""

    graph_id: str
    causal_links: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    governance_receipt_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "causal_links": self.causal_links,
            "confidence": self.confidence,
            "governance_receipt_id": self.governance_receipt_id,
        }


@dataclass
class CanonicalTruthRecord:
    """A record of a single canonical truth — immutable once written."""

    truth_id: str
    source_candidate_id: str
    source_candidate_hash: str
    canonical_hash: str = ""
    originating_observation_ids: list[str] = field(default_factory=list)
    originating_interpretation_id: str = ""
    originating_trace_id: str = ""
    governance_receipt: CanonicalGovernanceReceipt | None = None
    lineage: CanonicalLineageReference = field(default_factory=CanonicalLineageReference)
    confidence: float = 0.0
    uncertainty_score: float = 0.0
    rollback_reference: str = ""
    allowed_next_actions: list[str] = field(default_factory=list)
    blocked_next_actions: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def compute_canonical_hash(self) -> str:
        serializable = {
            "truth_id": self.truth_id,
            "source_candidate_id": self.source_candidate_id,
            "source_candidate_hash": self.source_candidate_hash,
            "originating_observation_ids": self.originating_observation_ids,
            "originating_interpretation_id": self.originating_interpretation_id,
            "originating_trace_id": self.originating_trace_id,
            "confidence": self.confidence,
        }
        content = json.dumps(serializable, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "truth_id": self.truth_id,
            "source_candidate_id": self.source_candidate_id,
            "source_candidate_hash": self.source_candidate_hash,
            "canonical_hash": self.canonical_hash,
            "originating_observation_ids": self.originating_observation_ids,
            "originating_interpretation_id": self.originating_interpretation_id,
            "originating_trace_id": self.originating_trace_id,
            "governance_receipt": self.governance_receipt.to_dict()
            if self.governance_receipt
            else None,
            "lineage": self.lineage.to_dict(),
            "confidence": self.confidence,
            "uncertainty_score": self.uncertainty_score,
            "rollback_reference": self.rollback_reference,
            "allowed_next_actions": self.allowed_next_actions,
            "blocked_next_actions": self.blocked_next_actions,
            "timestamp": self.timestamp,
        }


@dataclass
class CanonicalBoundary:
    """Structural enforcement of what canonical world models may do."""

    may_store_governed_truth: bool = True
    may_expose_retrieval: bool = True
    may_support_replay: bool = True
    may_support_rollback: bool = True
    may_support_lineage_traversal: bool = True
    may_support_governance_audit: bool = True
    may_self_mutate: bool = False
    may_recursive_rewrite: bool = False
    may_auto_promote: bool = False
    may_trigger_execution: bool = False
    may_reinterpret_observations: bool = False
    may_bypass_governance: bool = False

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.may_self_mutate:
            errors.append("canonical world model may not self-mutate")
        if self.may_recursive_rewrite:
            errors.append("canonical world model may not recursively rewrite")
        if self.may_auto_promote:
            errors.append("canonical world model may not auto-promote new truths")
        if self.may_trigger_execution:
            errors.append("canonical world model may not trigger execution")
        if self.may_reinterpret_observations:
            errors.append("canonical world model may not reinterpret observations")
        if self.may_bypass_governance:
            errors.append("canonical world model may not bypass governance")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "may_store_governed_truth": self.may_store_governed_truth,
            "may_expose_retrieval": self.may_expose_retrieval,
            "may_support_replay": self.may_support_replay,
            "may_support_rollback": self.may_support_rollback,
            "may_support_lineage_traversal": self.may_support_lineage_traversal,
            "may_support_governance_audit": self.may_support_governance_audit,
            "may_self_mutate": self.may_self_mutate,
            "may_recursive_rewrite": self.may_recursive_rewrite,
            "may_auto_promote": self.may_auto_promote,
            "may_trigger_execution": self.may_trigger_execution,
            "may_reinterpret_observations": self.may_reinterpret_observations,
            "may_bypass_governance": self.may_bypass_governance,
        }


@dataclass
class CanonicalWorldModel:
    """The substrate's canonical world model — governed truth store."""

    model_id: str
    entities: list[CanonicalEntity] = field(default_factory=list)
    relationships: list[CanonicalRelationship] = field(default_factory=list)
    constraints: list[CanonicalConstraint] = field(default_factory=list)
    causal_graph: CanonicalCausalGraph | None = None
    truth_records: list[CanonicalTruthRecord] = field(default_factory=list)
    boundary: CanonicalBoundary = field(default_factory=CanonicalBoundary)
    output_hash: str = ""
    governance_receipts: list[CanonicalGovernanceReceipt] = field(default_factory=list)
    rollback_chain: list[str] = field(default_factory=list)
    blocked_actions: list[str] = field(default_factory=list)
    allowed_actions: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def compute_output_hash(self) -> str:
        serializable = {
            "model_id": self.model_id,
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
            "constraints": [c.to_dict() for c in self.constraints],
            "causal_graph": self.causal_graph.to_dict() if self.causal_graph else None,
            "truth_records": [
                {
                    "truth_id": t.truth_id,
                    "source_candidate_id": t.source_candidate_id,
                    "source_candidate_hash": t.source_candidate_hash,
                    "canonical_hash": t.canonical_hash,
                    "originating_observation_ids": t.originating_observation_ids,
                    "originating_interpretation_id": t.originating_interpretation_id,
                    "confidence": t.confidence,
                }
                for t in self.truth_records
            ],
        }
        content = json.dumps(serializable, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def validate(self) -> list[str]:
        errors = self.boundary.validate()
        if not self.model_id:
            errors.append("model_id required")
        if not self.truth_records:
            errors.append("at least one truth_record required")
        if not self.governance_receipts:
            errors.append("at least one governance_receipt required")
        if not self.blocked_actions:
            errors.append("blocked_actions must be populated")
        for tr in self.truth_records:
            if not tr.governance_receipt:
                errors.append(f"truth_record {tr.truth_id} missing governance_receipt")
            if not tr.canonical_hash:
                errors.append(f"truth_record {tr.truth_id} missing canonical_hash")
        return errors

    def get_entity(self, entity_id: str) -> CanonicalEntity | None:
        for e in self.entities:
            return e if e.entity_id == entity_id else None
        return None

    def get_truth_record(self, truth_id: str) -> CanonicalTruthRecord | None:
        for tr in self.truth_records:
            if tr.truth_id == truth_id:
                return tr
        return None

    def get_governance_audit(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self.governance_receipts]

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
            "constraints": [c.to_dict() for c in self.constraints],
            "causal_graph": self.causal_graph.to_dict() if self.causal_graph else None,
            "truth_records": [t.to_dict() for t in self.truth_records],
            "boundary": self.boundary.to_dict(),
            "output_hash": self.output_hash,
            "governance_receipts": [r.to_dict() for r in self.governance_receipts],
            "rollback_chain": self.rollback_chain,
            "blocked_actions": self.blocked_actions,
            "allowed_actions": self.allowed_actions,
            "timestamp": self.timestamp,
        }
