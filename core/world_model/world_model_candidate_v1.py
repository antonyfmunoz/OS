"""World Model Candidate v1 for the UMH substrate layer.

Accumulates structured interpretations into candidate reality
structures WITHOUT mutating canonical world models.

Interpretation generates hypotheses.
World-model candidates organize hypotheses.
Only governance may promote reality structure into canonical
world models.

UMH substrate subsystem. Phase 96.8X.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from core.world_model.entity_resolution_v1 import (
    CandidateEntity,
    CandidateRelationship,
    EntityReference,
    RelationshipReference,
    ResolutionConfidence,
)


class CandidateStatus(str, Enum):
    DRAFT = "draft"
    ASSEMBLED = "assembled"
    AWAITING_GOVERNANCE = "awaiting_governance"
    GOVERNANCE_APPROVED = "governance_approved"
    GOVERNANCE_REJECTED = "governance_rejected"


FORBIDDEN_CANDIDATE_ACTIONS = frozenset(
    {
        "mutate_canonical_world_model",
        "create_canonical_truth",
        "auto_promote",
        "bypass_governance",
        "trigger_execution",
        "recursive_self_rewrite",
        "autonomous_memory_promotion",
        "silent_entity_creation",
        "expand_ontology_without_governance",
        "self_promote_to_canonical",
    }
)


@dataclass
class CandidateObservation:
    """An observation contributing to a world-model candidate."""

    observation_id: str
    primitive_type: str
    label: str
    confidence: float
    source_interpretation_id: str = ""
    source_trace_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "primitive_type": self.primitive_type,
            "label": self.label,
            "confidence": self.confidence,
            "source_interpretation_id": self.source_interpretation_id,
            "source_trace_id": self.source_trace_id,
        }


@dataclass
class CandidateCausalLink:
    """A candidate causal relationship between entities."""

    link_id: str
    cause_entity_id: str
    effect_entity_id: str
    causal_type: str
    confidence: float
    evidence_observation_ids: list[str] = field(default_factory=list)
    unsupported_assumptions: list[str] = field(default_factory=list)
    temporal_ordering: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_id": self.link_id,
            "cause_entity_id": self.cause_entity_id,
            "effect_entity_id": self.effect_entity_id,
            "causal_type": self.causal_type,
            "confidence": self.confidence,
            "evidence_observation_ids": self.evidence_observation_ids,
            "unsupported_assumptions": self.unsupported_assumptions,
            "temporal_ordering": self.temporal_ordering,
        }


@dataclass
class CandidateConstraint:
    """A constraint on a world-model candidate."""

    constraint_id: str
    constraint_type: str
    description: str
    applies_to_entity_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    source_observation_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "constraint_type": self.constraint_type,
            "description": self.description,
            "applies_to_entity_ids": self.applies_to_entity_ids,
            "confidence": self.confidence,
            "source_observation_id": self.source_observation_id,
        }


@dataclass
class CandidateConfidenceEnvelope:
    """Quantified uncertainty for a world-model candidate."""

    overall_confidence: float
    entity_confidence: float
    relationship_confidence: float
    causal_confidence: float
    evidence_coverage: float
    uncertainty_score: float
    assumptions_count: int = 0
    unknowns_count: int = 0
    interpretation_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_confidence": self.overall_confidence,
            "entity_confidence": self.entity_confidence,
            "relationship_confidence": self.relationship_confidence,
            "causal_confidence": self.causal_confidence,
            "evidence_coverage": self.evidence_coverage,
            "uncertainty_score": self.uncertainty_score,
            "assumptions_count": self.assumptions_count,
            "unknowns_count": self.unknowns_count,
            "interpretation_count": self.interpretation_count,
        }


@dataclass
class CandidateBoundary:
    """Structural enforcement of what a world-model candidate may do."""

    may_aggregate_interpretations: bool = True
    may_connect_entities: bool = True
    may_establish_relationships: bool = True
    may_accumulate_evidence: bool = True
    may_track_uncertainty: bool = True
    may_form_causal_structures: bool = True
    may_mutate_canonical_world_model: bool = False
    may_create_canonical_truth: bool = False
    may_auto_promote: bool = False
    may_bypass_governance: bool = False
    may_trigger_execution: bool = False
    may_recursive_rewrite: bool = False

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.may_mutate_canonical_world_model:
            errors.append("candidate may not mutate canonical world model")
        if self.may_create_canonical_truth:
            errors.append("candidate may not create canonical truth")
        if self.may_auto_promote:
            errors.append("candidate may not auto-promote")
        if self.may_bypass_governance:
            errors.append("candidate may not bypass governance")
        if self.may_trigger_execution:
            errors.append("candidate may not trigger execution")
        if self.may_recursive_rewrite:
            errors.append("candidate may not recursively rewrite itself")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "may_aggregate_interpretations": self.may_aggregate_interpretations,
            "may_connect_entities": self.may_connect_entities,
            "may_establish_relationships": self.may_establish_relationships,
            "may_accumulate_evidence": self.may_accumulate_evidence,
            "may_track_uncertainty": self.may_track_uncertainty,
            "may_form_causal_structures": self.may_form_causal_structures,
            "may_mutate_canonical_world_model": self.may_mutate_canonical_world_model,
            "may_create_canonical_truth": self.may_create_canonical_truth,
            "may_auto_promote": self.may_auto_promote,
            "may_bypass_governance": self.may_bypass_governance,
            "may_trigger_execution": self.may_trigger_execution,
            "may_recursive_rewrite": self.may_recursive_rewrite,
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


@dataclass
class WorldModelCandidate:
    """A candidate world-model structure — NOT canonical truth."""

    candidate_id: str
    source_interpretation_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    entities: list[CandidateEntity] = field(default_factory=list)
    relationships: list[CandidateRelationship] = field(default_factory=list)
    causal_links: list[CandidateCausalLink] = field(default_factory=list)
    constraints: list[CandidateConstraint] = field(default_factory=list)
    observations: list[CandidateObservation] = field(default_factory=list)
    confidence_envelope: CandidateConfidenceEnvelope | None = None
    boundary: CandidateBoundary = field(default_factory=CandidateBoundary)
    status: CandidateStatus = CandidateStatus.DRAFT
    input_content_hash: str = ""
    output_hash: str = ""
    extraction_lineage: str = ""
    normalization_lineage: str = ""
    interpretation_lineage: str = ""
    governance_status: str = "not_submitted"
    rollback_reference: str = ""
    unsupported_assumptions: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    explicit_unknowns: list[str] = field(default_factory=list)
    blocked_actions: list[str] = field(default_factory=list)
    allowed_actions: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def compute_output_hash(self) -> str:
        serializable = {
            "candidate_id": self.candidate_id,
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
            "causal_links": [c.to_dict() for c in self.causal_links],
            "constraints": [c.to_dict() for c in self.constraints],
            "observations": [o.to_dict() for o in self.observations],
            "unsupported_assumptions": self.unsupported_assumptions,
            "explicit_unknowns": self.explicit_unknowns,
            "source_interpretation_ids": self.source_interpretation_ids,
        }
        content = json.dumps(serializable, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def validate(self) -> list[str]:
        errors = self.boundary.validate()
        if not self.candidate_id:
            errors.append("candidate_id required")
        if not self.entities and not self.observations:
            errors.append("at least one entity or observation required")
        if not self.blocked_actions:
            errors.append("blocked_actions must be populated")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source_interpretation_ids": self.source_interpretation_ids,
            "source_trace_ids": self.source_trace_ids,
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
            "causal_links": [c.to_dict() for c in self.causal_links],
            "constraints": [c.to_dict() for c in self.constraints],
            "observations": [o.to_dict() for o in self.observations],
            "confidence_envelope": self.confidence_envelope.to_dict()
            if self.confidence_envelope
            else None,
            "boundary": self.boundary.to_dict(),
            "status": self.status.value,
            "input_content_hash": self.input_content_hash,
            "output_hash": self.output_hash,
            "extraction_lineage": self.extraction_lineage,
            "normalization_lineage": self.normalization_lineage,
            "interpretation_lineage": self.interpretation_lineage,
            "governance_status": self.governance_status,
            "rollback_reference": self.rollback_reference,
            "unsupported_assumptions": self.unsupported_assumptions,
            "missing_information": self.missing_information,
            "explicit_unknowns": self.explicit_unknowns,
            "blocked_actions": self.blocked_actions,
            "allowed_actions": self.allowed_actions,
            "timestamp": self.timestamp,
        }


class WorldModelCandidateAssembler:
    """Assembles world-model candidates from interpretation results.

    Takes interpretation output (observations, hypotheses, decompositions)
    and organizes them into candidate entity graphs with causal links.
    Deterministic: same interpretation chain → same candidate hash.
    """

    def __init__(self) -> None:
        self.boundary = CandidateBoundary()

    def assemble(
        self,
        interpretation_result_id: str,
        interpretation_output_hash: str,
        observations: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
        hypotheses: list[dict[str, Any]],
        trace_id: str = "",
        extraction_lineage: str = "",
        normalization_lineage: str = "",
    ) -> WorldModelCandidate:
        boundary_errors = self.boundary.validate()
        if boundary_errors:
            raise ValueError(f"Boundary violation: {boundary_errors}")

        ids = _DeterministicIdGenerator(interpretation_output_hash)

        candidate_entities = self._extract_entities(observations, ids, trace_id)
        candidate_relationships = self._extract_relationships(
            relationships, candidate_entities, ids
        )
        candidate_causal_links = self._extract_causal_links(hypotheses, candidate_entities, ids)
        candidate_observations = self._extract_observations(
            observations, ids, interpretation_result_id, trace_id
        )
        candidate_constraints = self._extract_constraints(observations, ids)
        confidence = self._compute_confidence(
            candidate_entities,
            candidate_relationships,
            candidate_causal_links,
            candidate_observations,
        )

        unsupported = []
        for h in hypotheses:
            unsupported.extend(h.get("unsupported_assumptions", []))
        if not unsupported:
            unsupported.append("world-model candidate assembled from limited interpretation chain")

        unknowns = [
            "whether additional interpretations would change candidate structure",
            "whether entity resolution is complete across all sources",
            "candidate causal links may lack temporal validation",
        ]

        candidate = WorldModelCandidate(
            candidate_id=ids.next_id("WMC"),
            source_interpretation_ids=[interpretation_result_id],
            source_trace_ids=[trace_id] if trace_id else [],
            entities=candidate_entities,
            relationships=candidate_relationships,
            causal_links=candidate_causal_links,
            constraints=candidate_constraints,
            observations=candidate_observations,
            confidence_envelope=confidence,
            boundary=self.boundary,
            status=CandidateStatus.ASSEMBLED,
            input_content_hash=interpretation_output_hash,
            extraction_lineage=extraction_lineage,
            normalization_lineage=normalization_lineage,
            interpretation_lineage=interpretation_result_id,
            governance_status="not_submitted",
            rollback_reference="",
            unsupported_assumptions=unsupported,
            missing_information=[
                "cross-interpretation entity resolution not yet performed",
                "temporal ordering of causal links not validated externally",
            ],
            explicit_unknowns=unknowns,
            blocked_actions=list(FORBIDDEN_CANDIDATE_ACTIONS),
            allowed_actions=[
                "persist_candidate_artifact",
                "submit_for_governance_review",
                "merge_with_other_candidate",
            ],
        )
        candidate.output_hash = candidate.compute_output_hash()

        validation_errors = candidate.validate()
        if validation_errors:
            raise ValueError(f"Candidate validation failed: {validation_errors}")

        return candidate

    def _extract_entities(
        self,
        observations: list[dict[str, Any]],
        ids: _DeterministicIdGenerator,
        trace_id: str,
    ) -> list[CandidateEntity]:
        entities: list[CandidateEntity] = []
        seen_labels: set[str] = set()

        for obs in observations:
            label = obs.get("label", "")
            if not label or label in seen_labels:
                continue
            seen_labels.add(label)

            entities.append(
                CandidateEntity(
                    entity_id=ids.next_id("ENT"),
                    entity_type=obs.get("primitive_type", "unknown"),
                    label=label,
                    confidence=obs.get("confidence", 0.0),
                    source_observation_ids=[obs.get("observation_id", "")],
                    source_interpretation_ids=[],
                    source_trace_ids=[trace_id] if trace_id else [],
                    uncertainty_notes=[],
                )
            )
        return entities

    def _extract_relationships(
        self,
        relationships: list[dict[str, Any]],
        entities: list[CandidateEntity],
        ids: _DeterministicIdGenerator,
    ) -> list[CandidateRelationship]:
        obs_to_entity: dict[str, str] = {}
        for ent in entities:
            for obs_id in ent.source_observation_ids:
                obs_to_entity[obs_id] = ent.entity_id

        result: list[CandidateRelationship] = []
        for rel in relationships:
            from_obs = rel.get("from_observation_id", "")
            to_obs = rel.get("to_observation_id", "")
            from_ent = obs_to_entity.get(from_obs, "")
            to_ent = obs_to_entity.get(to_obs, "")
            if from_ent and to_ent:
                result.append(
                    CandidateRelationship(
                        relationship_id=ids.next_id("REL"),
                        from_entity_id=from_ent,
                        to_entity_id=to_ent,
                        relationship_type=rel.get("relationship_type", "unknown"),
                        confidence=rel.get("confidence", 0.0),
                        evidence_observation_ids=[from_obs, to_obs],
                        is_causal="cause" in rel.get("relationship_type", "").lower(),
                        is_temporal="preced" in rel.get("relationship_type", "").lower()
                        or "follow" in rel.get("relationship_type", "").lower(),
                        is_constraint="constrain" in rel.get("relationship_type", "").lower(),
                    )
                )
        return result

    def _extract_causal_links(
        self,
        hypotheses: list[dict[str, Any]],
        entities: list[CandidateEntity],
        ids: _DeterministicIdGenerator,
    ) -> list[CandidateCausalLink]:
        links: list[CandidateCausalLink] = []
        if len(entities) < 2 or not hypotheses:
            return links

        for hyp in hypotheses:
            supporting = hyp.get("supporting_observations", [])
            if not supporting:
                continue
            links.append(
                CandidateCausalLink(
                    link_id=ids.next_id("CAUSAL"),
                    cause_entity_id=entities[0].entity_id,
                    effect_entity_id=entities[-1].entity_id,
                    causal_type="hypothesis_derived",
                    confidence=hyp.get("confidence", 0.0),
                    evidence_observation_ids=supporting,
                    unsupported_assumptions=hyp.get("unsupported_assumptions", []),
                    temporal_ordering="inferred",
                )
            )
        return links

    def _extract_observations(
        self,
        observations: list[dict[str, Any]],
        ids: _DeterministicIdGenerator,
        interpretation_result_id: str,
        trace_id: str,
    ) -> list[CandidateObservation]:
        return [
            CandidateObservation(
                observation_id=ids.next_id("COBS"),
                primitive_type=obs.get("primitive_type", "unknown"),
                label=obs.get("label", ""),
                confidence=obs.get("confidence", 0.0),
                source_interpretation_id=interpretation_result_id,
                source_trace_id=trace_id,
            )
            for obs in observations
        ]

    def _extract_constraints(
        self,
        observations: list[dict[str, Any]],
        ids: _DeterministicIdGenerator,
    ) -> list[CandidateConstraint]:
        constraints: list[CandidateConstraint] = []
        for obs in observations:
            if obs.get("primitive_type") == "constraint":
                constraints.append(
                    CandidateConstraint(
                        constraint_id=ids.next_id("CSTR"),
                        constraint_type="observed",
                        description=obs.get("description", obs.get("label", "")),
                        confidence=obs.get("confidence", 0.0),
                        source_observation_id=obs.get("observation_id", ""),
                    )
                )
        return constraints

    def _compute_confidence(
        self,
        entities: list[CandidateEntity],
        relationships: list[CandidateRelationship],
        causal_links: list[CandidateCausalLink],
        observations: list[CandidateObservation],
    ) -> CandidateConfidenceEnvelope:
        ent_conf = sum(e.confidence for e in entities) / max(len(entities), 1)
        rel_conf = sum(r.confidence for r in relationships) / max(len(relationships), 1)
        causal_conf = sum(c.confidence for c in causal_links) / max(len(causal_links), 1)
        evidence = len(observations) / max(len(entities) + len(relationships), 1)
        evidence_cov = min(evidence, 1.0)

        overall = (ent_conf + rel_conf + causal_conf + evidence_cov) / 4.0
        uncertainty = 1.0 - overall

        return CandidateConfidenceEnvelope(
            overall_confidence=round(overall, 4),
            entity_confidence=round(ent_conf, 4),
            relationship_confidence=round(rel_conf, 4),
            causal_confidence=round(causal_conf, 4),
            evidence_coverage=round(evidence_cov, 4),
            uncertainty_score=round(uncertainty, 4),
            interpretation_count=1,
        )
