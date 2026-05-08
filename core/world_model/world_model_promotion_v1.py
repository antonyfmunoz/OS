"""World Model Promotion v1 for the UMH substrate layer.

Governance-bound promotion pipeline that converts world-model
candidates into canonical world-model truth. Every promotion
requires governance approval, deterministic candidate hash
verification, lineage completeness, and rollback reference.

Canonical truth is not generated.
Canonical truth is promoted through governed transition.

UMH substrate subsystem. Phase 96.8Y.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from core.world_model.canonical_world_model_v1 import (
    FORBIDDEN_CANONICAL_ACTIONS,
    CanonicalBoundary,
    CanonicalCausalGraph,
    CanonicalConstraint,
    CanonicalEntity,
    CanonicalGovernanceReceipt,
    CanonicalLineageReference,
    CanonicalRelationship,
    CanonicalTruthRecord,
    CanonicalWorldModel,
)
from core.world_model.world_model_candidate_v1 import WorldModelCandidate


class PromotionDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


@dataclass
class PromotionRequest:
    """Request to promote a world-model candidate to canonical."""

    request_id: str
    candidate_id: str
    candidate_hash: str
    requestor: str = "system"
    lineage_complete: bool = False
    replay_validated: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "candidate_id": self.candidate_id,
            "candidate_hash": self.candidate_hash,
            "requestor": self.requestor,
            "lineage_complete": self.lineage_complete,
            "replay_validated": self.replay_validated,
            "timestamp": self.timestamp,
        }


@dataclass
class PromotionReview:
    """Governance review of a promotion request."""

    review_id: str
    request_id: str
    reviewer: str
    decision: PromotionDecision
    review_notes: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "request_id": self.request_id,
            "reviewer": self.reviewer,
            "decision": self.decision.value,
            "review_notes": self.review_notes,
            "timestamp": self.timestamp,
        }


@dataclass
class GovernanceApproval:
    """Approved governance decision for promotion."""

    approval_id: str
    review_id: str
    request_id: str
    candidate_id: str
    candidate_hash: str
    approved_by: str
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "review_id": self.review_id,
            "request_id": self.request_id,
            "candidate_id": self.candidate_id,
            "candidate_hash": self.candidate_hash,
            "approved_by": self.approved_by,
            "timestamp": self.timestamp,
        }


@dataclass
class PromotionReceipt:
    """Receipt proving a candidate was promoted to canonical."""

    receipt_id: str
    candidate_id: str
    candidate_hash: str
    canonical_model_id: str
    canonical_hash: str
    governance_approval_id: str
    truth_record_ids: list[str] = field(default_factory=list)
    rollback_reference: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "candidate_id": self.candidate_id,
            "candidate_hash": self.candidate_hash,
            "canonical_model_id": self.canonical_model_id,
            "canonical_hash": self.canonical_hash,
            "governance_approval_id": self.governance_approval_id,
            "truth_record_ids": self.truth_record_ids,
            "rollback_reference": self.rollback_reference,
            "timestamp": self.timestamp,
        }


@dataclass
class RollbackReceipt:
    """Receipt proving a canonical truth was rolled back."""

    receipt_id: str
    canonical_model_id: str
    rolled_back_truth_ids: list[str] = field(default_factory=list)
    prior_canonical_hash: str = ""
    new_canonical_hash: str = ""
    rollback_reason: str = ""
    governance_reference: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "canonical_model_id": self.canonical_model_id,
            "rolled_back_truth_ids": self.rolled_back_truth_ids,
            "prior_canonical_hash": self.prior_canonical_hash,
            "new_canonical_hash": self.new_canonical_hash,
            "rollback_reason": self.rollback_reason,
            "governance_reference": self.governance_reference,
            "timestamp": self.timestamp,
        }


class _DeterministicIdGenerator:
    """Generates reproducible IDs from a seed hash + counter."""

    def __init__(self, seed: str) -> None:
        self._seed = seed
        self._counter = 0

    def next_id(self, prefix: str) -> str:
        self._counter += 1
        raw = hashlib.sha256(f"{self._seed}:{prefix}:{self._counter}".encode("utf-8")).hexdigest()[
            :8
        ]
        return f"{prefix}-{raw}"


class WorldModelPromoter:
    """Promotes governance-approved candidates to canonical world models.

    Requires governance approval before any promotion. Produces
    deterministic canonical hashes. Generates rollback references.
    """

    def __init__(self) -> None:
        self.boundary = CanonicalBoundary()

    def promote(
        self,
        candidate: WorldModelCandidate,
        approval: GovernanceApproval,
        extraction_lineage: str = "",
        normalization_lineage: str = "",
        interpretation_lineage: str = "",
    ) -> tuple[CanonicalWorldModel, PromotionReceipt]:
        boundary_errors = self.boundary.validate()
        if boundary_errors:
            raise ValueError(f"Boundary violation: {boundary_errors}")

        self._validate_promotion_preconditions(candidate, approval)

        ids = _DeterministicIdGenerator(candidate.output_hash)

        governance_receipt = CanonicalGovernanceReceipt(
            receipt_id=ids.next_id("GRCPT"),
            governance_reference=approval.approval_id,
            approved_by=approval.approved_by,
            candidate_hash=candidate.output_hash,
            decision="approved",
        )

        lineage = CanonicalLineageReference(
            extraction_state_id=extraction_lineage or candidate.extraction_lineage,
            normalization_state_id=normalization_lineage or candidate.normalization_lineage,
            interpretation_state_id=interpretation_lineage or candidate.interpretation_lineage,
            candidate_state_id=candidate.candidate_id,
            governance_state_id=approval.approval_id,
            trace_id=candidate.source_trace_ids[0] if candidate.source_trace_ids else "",
        )

        canonical_entities = [
            CanonicalEntity(
                entity_id=ids.next_id("CENT"),
                entity_type=e.entity_type,
                label=e.label,
                confidence=e.confidence,
                source_candidate_entity_id=e.entity_id,
                source_observation_ids=e.source_observation_ids,
                governance_receipt_id=governance_receipt.receipt_id,
            )
            for e in candidate.entities
        ]

        ent_id_map: dict[str, str] = {}
        for orig, canon in zip(candidate.entities, canonical_entities):
            ent_id_map[orig.entity_id] = canon.entity_id

        canonical_relationships = [
            CanonicalRelationship(
                relationship_id=ids.next_id("CREL"),
                from_entity_id=ent_id_map.get(r.from_entity_id, r.from_entity_id),
                to_entity_id=ent_id_map.get(r.to_entity_id, r.to_entity_id),
                relationship_type=r.relationship_type,
                confidence=r.confidence,
                source_candidate_relationship_id=r.relationship_id,
                governance_receipt_id=governance_receipt.receipt_id,
            )
            for r in candidate.relationships
        ]

        canonical_constraints = [
            CanonicalConstraint(
                constraint_id=ids.next_id("CCSTR"),
                constraint_type=c.constraint_type,
                description=c.description,
                applies_to_entity_ids=[ent_id_map.get(eid, eid) for eid in c.applies_to_entity_ids],
                confidence=c.confidence,
                governance_receipt_id=governance_receipt.receipt_id,
            )
            for c in candidate.constraints
        ]

        canonical_causal = None
        if candidate.causal_links:
            canonical_causal = CanonicalCausalGraph(
                graph_id=ids.next_id("CCAUSAL"),
                causal_links=[
                    {
                        "cause_entity_id": ent_id_map.get(cl.cause_entity_id, cl.cause_entity_id),
                        "effect_entity_id": ent_id_map.get(
                            cl.effect_entity_id, cl.effect_entity_id
                        ),
                        "causal_type": cl.causal_type,
                        "confidence": cl.confidence,
                    }
                    for cl in candidate.causal_links
                ],
                confidence=sum(cl.confidence for cl in candidate.causal_links)
                / max(len(candidate.causal_links), 1),
                governance_receipt_id=governance_receipt.receipt_id,
            )

        all_obs_ids = [obs_id for e in candidate.entities for obs_id in e.source_observation_ids]

        truth_record = CanonicalTruthRecord(
            truth_id=ids.next_id("TRUTH"),
            source_candidate_id=candidate.candidate_id,
            source_candidate_hash=candidate.output_hash,
            originating_observation_ids=all_obs_ids,
            originating_interpretation_id=candidate.interpretation_lineage,
            originating_trace_id=lineage.trace_id,
            governance_receipt=governance_receipt,
            lineage=lineage,
            confidence=candidate.confidence_envelope.overall_confidence
            if candidate.confidence_envelope
            else 0.0,
            uncertainty_score=candidate.confidence_envelope.uncertainty_score
            if candidate.confidence_envelope
            else 1.0,
            rollback_reference=ids.next_id("ROLLBACK"),
            allowed_next_actions=[
                "retrieve_canonical_truth",
                "traverse_lineage",
                "audit_governance",
                "initiate_rollback_review",
            ],
            blocked_next_actions=list(FORBIDDEN_CANONICAL_ACTIONS),
        )
        truth_record.canonical_hash = truth_record.compute_canonical_hash()

        model = CanonicalWorldModel(
            model_id=ids.next_id("CWM"),
            entities=canonical_entities,
            relationships=canonical_relationships,
            constraints=canonical_constraints,
            causal_graph=canonical_causal,
            truth_records=[truth_record],
            boundary=self.boundary,
            governance_receipts=[governance_receipt],
            rollback_chain=[truth_record.rollback_reference],
            blocked_actions=list(FORBIDDEN_CANONICAL_ACTIONS),
            allowed_actions=[
                "retrieve_canonical_truth",
                "traverse_lineage",
                "audit_governance",
                "initiate_rollback_review",
            ],
        )
        model.output_hash = model.compute_output_hash()

        validation_errors = model.validate()
        if validation_errors:
            raise ValueError(f"Canonical model validation failed: {validation_errors}")

        promotion_receipt = PromotionReceipt(
            receipt_id=ids.next_id("PROMO"),
            candidate_id=candidate.candidate_id,
            candidate_hash=candidate.output_hash,
            canonical_model_id=model.model_id,
            canonical_hash=model.output_hash,
            governance_approval_id=approval.approval_id,
            truth_record_ids=[truth_record.truth_id],
            rollback_reference=truth_record.rollback_reference,
        )

        return model, promotion_receipt

    def create_rollback_receipt(
        self,
        model: CanonicalWorldModel,
        truth_ids_to_rollback: list[str],
        rollback_reason: str,
        governance_reference: str,
    ) -> RollbackReceipt:
        prior_hash = model.output_hash
        return RollbackReceipt(
            receipt_id=f"RBRECEIPT-{hashlib.sha256(prior_hash.encode()).hexdigest()[:8]}",
            canonical_model_id=model.model_id,
            rolled_back_truth_ids=truth_ids_to_rollback,
            prior_canonical_hash=prior_hash,
            new_canonical_hash="",
            rollback_reason=rollback_reason,
            governance_reference=governance_reference,
        )

    def _validate_promotion_preconditions(
        self,
        candidate: WorldModelCandidate,
        approval: GovernanceApproval,
    ) -> None:
        if not approval.approval_id:
            raise ValueError("Governance approval_id required for promotion")
        if not approval.approved_by:
            raise ValueError("Governance approved_by required for promotion")
        if approval.candidate_id != candidate.candidate_id:
            raise ValueError(
                f"Approval candidate_id mismatch: "
                f"{approval.candidate_id} != {candidate.candidate_id}"
            )
        if approval.candidate_hash != candidate.output_hash:
            raise ValueError(
                f"Approval candidate_hash mismatch: "
                f"{approval.candidate_hash} != {candidate.output_hash}"
            )
        if not candidate.entities and not candidate.observations:
            raise ValueError("Cannot promote empty candidate")
