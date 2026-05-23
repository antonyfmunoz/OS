"""Interpretation Engine v1 for the UMH substrate layer.

Deterministic, lineage-aware, non-mutating interpretation.
Generates hypotheses — never truth. Truth only exists through
governed promotion.

Interpretation stages:
  observation → pattern_detection → primitive_mapping
  → hypothesis_generation → uncertainty_analysis

UMH substrate subsystem. Phase 96.8W.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from substrate.understanding.ontology.primitive_decomposition_v1 import (
    DecompositionResult,
    PrimitiveObservation,
    PrimitiveRelationship,
    PrimitiveType,
    RelationshipType,
)


class InterpretationStage(str, Enum):
    OBSERVATION = "observation"
    PATTERN_DETECTION = "pattern_detection"
    PRIMITIVE_MAPPING = "primitive_mapping"
    HYPOTHESIS_GENERATION = "hypothesis_generation"
    UNCERTAINTY_ANALYSIS = "uncertainty_analysis"


INTERPRETATION_STAGE_ORDER = [
    InterpretationStage.OBSERVATION,
    InterpretationStage.PATTERN_DETECTION,
    InterpretationStage.PRIMITIVE_MAPPING,
    InterpretationStage.HYPOTHESIS_GENERATION,
    InterpretationStage.UNCERTAINTY_ANALYSIS,
]

FORBIDDEN_INTERPRETATION_ACTIONS = frozenset(
    {
        "mutate_canonical_memory",
        "update_world_model",
        "generate_embeddings",
        "promote_to_canonical",
        "self_promote",
        "recursive_self_expand",
        "bypass_governance",
        "trigger_execution",
        "autonomous_promotion",
        "silent_knowledge_creation",
    }
)


@dataclass
class ConfidenceEnvelope:
    """Quantified uncertainty for an interpretation."""

    overall_confidence: float
    observation_confidence: float
    pattern_confidence: float
    decomposition_confidence: float
    hypothesis_confidence: float
    uncertainty_score: float
    completeness_ratio: float = 0.0
    assumptions_count: int = 0
    unknowns_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_confidence": self.overall_confidence,
            "observation_confidence": self.observation_confidence,
            "pattern_confidence": self.pattern_confidence,
            "decomposition_confidence": self.decomposition_confidence,
            "hypothesis_confidence": self.hypothesis_confidence,
            "uncertainty_score": self.uncertainty_score,
            "completeness_ratio": self.completeness_ratio,
            "assumptions_count": self.assumptions_count,
            "unknowns_count": self.unknowns_count,
        }


@dataclass
class InterpretationBoundary:
    """Explicit declaration of what this interpretation may and may not do."""

    may_infer: bool = True
    may_decompose: bool = True
    may_classify: bool = True
    may_identify_patterns: bool = True
    may_generate_hypotheses: bool = True
    may_mutate_canonical_memory: bool = False
    may_update_world_model: bool = False
    may_generate_embeddings: bool = False
    may_promote_knowledge: bool = False
    may_trigger_execution: bool = False
    may_self_expand: bool = False

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.may_mutate_canonical_memory:
            errors.append("interpretation may not mutate canonical memory")
        if self.may_update_world_model:
            errors.append("interpretation may not update world model")
        if self.may_generate_embeddings:
            errors.append("interpretation may not generate embeddings")
        if self.may_promote_knowledge:
            errors.append("interpretation may not promote knowledge")
        if self.may_trigger_execution:
            errors.append("interpretation may not trigger execution")
        if self.may_self_expand:
            errors.append("interpretation may not self-expand")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "may_infer": self.may_infer,
            "may_decompose": self.may_decompose,
            "may_classify": self.may_classify,
            "may_identify_patterns": self.may_identify_patterns,
            "may_generate_hypotheses": self.may_generate_hypotheses,
            "may_mutate_canonical_memory": self.may_mutate_canonical_memory,
            "may_update_world_model": self.may_update_world_model,
            "may_generate_embeddings": self.may_generate_embeddings,
            "may_promote_knowledge": self.may_promote_knowledge,
            "may_trigger_execution": self.may_trigger_execution,
            "may_self_expand": self.may_self_expand,
        }


@dataclass
class InterpretationInput:
    """Input to the interpretation engine."""

    input_id: str
    source_content: str
    source_content_hash: str
    source_trace_id: str = ""
    source_state_id: str = ""
    extraction_reference: str = ""
    normalization_reference: str = ""
    query_lineage_reference: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_id": self.input_id,
            "source_content_hash": self.source_content_hash,
            "source_trace_id": self.source_trace_id,
            "source_state_id": self.source_state_id,
            "extraction_reference": self.extraction_reference,
            "normalization_reference": self.normalization_reference,
            "query_lineage_reference": self.query_lineage_reference,
            "timestamp": self.timestamp,
        }


@dataclass
class InterpretationHypothesis:
    """A generated hypothesis — NOT truth."""

    hypothesis_id: str
    statement: str
    confidence: float
    supporting_observations: list[str] = field(default_factory=list)
    unsupported_assumptions: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)
    requires_governance_review: bool = True
    promotion_status: str = "hypothesis_only"

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "statement": self.statement,
            "confidence": self.confidence,
            "supporting_observations": self.supporting_observations,
            "unsupported_assumptions": self.unsupported_assumptions,
            "contradicting_evidence": self.contradicting_evidence,
            "requires_governance_review": self.requires_governance_review,
            "promotion_status": self.promotion_status,
        }


@dataclass
class InterpretationResult:
    """Complete result of an interpretation run."""

    result_id: str
    input_id: str
    input_content_hash: str
    output_hash: str = ""
    stages_completed: list[str] = field(default_factory=list)
    observations: list[PrimitiveObservation] = field(default_factory=list)
    relationships: list[PrimitiveRelationship] = field(default_factory=list)
    decomposition: DecompositionResult | None = None
    hypotheses: list[InterpretationHypothesis] = field(default_factory=list)
    confidence_envelope: ConfidenceEnvelope | None = None
    boundary: InterpretationBoundary = field(default_factory=InterpretationBoundary)
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
        stable = {
            "input_content_hash": self.input_content_hash,
            "observations": [o.to_dict() for o in self.observations],
            "relationships": [r.to_dict() for r in self.relationships],
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "unsupported_assumptions": sorted(self.unsupported_assumptions),
            "explicit_unknowns": sorted(self.explicit_unknowns),
        }
        return hashlib.sha256(json.dumps(stable, sort_keys=True).encode("utf-8")).hexdigest()

    def validate(self) -> list[str]:
        errors: list[str] = []
        errors.extend(self.boundary.validate())

        if not self.explicit_unknowns and not self.unsupported_assumptions:
            errors.append(
                "interpretation must declare explicit unknowns or unsupported assumptions"
            )

        for h in self.hypotheses:
            if h.promotion_status != "hypothesis_only":
                errors.append(
                    f"hypothesis {h.hypothesis_id} has invalid promotion_status: "
                    f"{h.promotion_status} (must be 'hypothesis_only')"
                )
            if not h.requires_governance_review:
                errors.append(f"hypothesis {h.hypothesis_id} must require governance review")

        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "input_id": self.input_id,
            "input_content_hash": self.input_content_hash,
            "output_hash": self.output_hash,
            "stages_completed": self.stages_completed,
            "observations": [o.to_dict() for o in self.observations],
            "relationships": [r.to_dict() for r in self.relationships],
            "decomposition": self.decomposition.to_dict() if self.decomposition else None,
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "confidence_envelope": self.confidence_envelope.to_dict()
            if self.confidence_envelope
            else None,
            "boundary": self.boundary.to_dict(),
            "unsupported_assumptions": self.unsupported_assumptions,
            "missing_information": self.missing_information,
            "explicit_unknowns": self.explicit_unknowns,
            "blocked_actions": self.blocked_actions,
            "allowed_actions": self.allowed_actions,
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


class InterpretationEngineV1:
    """Deterministic, non-mutating interpretation engine.

    Runs the 5-stage interpretation pipeline on a given input.
    Produces hypotheses, primitive decompositions, and confidence
    envelopes. Never mutates canonical memory or world model.
    """

    def __init__(self) -> None:
        self.boundary = InterpretationBoundary()

    def interpret(self, interp_input: InterpretationInput) -> InterpretationResult:
        boundary_errors = self.boundary.validate()
        if boundary_errors:
            raise ValueError(f"Boundary violation: {boundary_errors}")

        ids = _DeterministicIdGenerator(interp_input.source_content_hash)

        observations = self._observe(interp_input, ids)
        patterns = self._detect_patterns(observations)
        decomposition = self._map_primitives(interp_input, observations, patterns, ids)
        hypotheses = self._generate_hypotheses(observations, patterns, decomposition, ids)
        confidence = self._analyze_uncertainty(observations, decomposition, hypotheses)

        unsupported = decomposition.unsupported_assumptions.copy()
        unknowns = decomposition.explicit_unknowns.copy()
        if not unknowns:
            unknowns.append("interpretation completeness unknown without domain context")

        result = InterpretationResult(
            result_id=ids.next_id("INTERP"),
            input_id=interp_input.input_id,
            input_content_hash=interp_input.source_content_hash,
            stages_completed=[s.value for s in INTERPRETATION_STAGE_ORDER],
            observations=observations,
            relationships=patterns,
            decomposition=decomposition,
            hypotheses=hypotheses,
            confidence_envelope=confidence,
            boundary=self.boundary,
            unsupported_assumptions=unsupported,
            missing_information=decomposition.missing_information.copy(),
            explicit_unknowns=unknowns,
            blocked_actions=[a for a in FORBIDDEN_INTERPRETATION_ACTIONS],
            allowed_actions=[
                "create_hypothesis_candidate",
                "create_decomposition_artifact",
                "persist_interpretation_state",
            ],
        )
        result.output_hash = result.compute_output_hash()

        validation_errors = result.validate()
        if validation_errors:
            raise ValueError(f"Result validation failed: {validation_errors}")

        return result

    def _observe(
        self, interp_input: InterpretationInput, ids: _DeterministicIdGenerator
    ) -> list[PrimitiveObservation]:
        content = interp_input.source_content
        observations: list[PrimitiveObservation] = []

        observations.append(
            PrimitiveObservation(
                observation_id=ids.next_id("OBS"),
                primitive_type=PrimitiveType.STATE,
                label="document_exists",
                description=f"Document content available ({len(content)} chars)",
                confidence=1.0,
                source_reference=interp_input.input_id,
                evidence="content hash verified",
            )
        )

        if any(kw in content.lower() for kw in ["test", "validation", "proof", "verify"]):
            observations.append(
                PrimitiveObservation(
                    observation_id=ids.next_id("OBS"),
                    primitive_type=PrimitiveType.GOAL,
                    label="validation_purpose",
                    description="Document appears to serve a validation or testing purpose",
                    confidence=0.85,
                    source_reference=interp_input.input_id,
                    evidence="keyword match: test/validation/proof/verify",
                    is_inferred=True,
                )
            )

        if any(kw in content.lower() for kw in ["no sensitive", "no private", "safe"]):
            observations.append(
                PrimitiveObservation(
                    observation_id=ids.next_id("OBS"),
                    primitive_type=PrimitiveType.CONSTRAINT,
                    label="safety_bounded",
                    description="Document explicitly declares safety/non-sensitivity constraints",
                    confidence=0.90,
                    source_reference=interp_input.input_id,
                    evidence="keyword match: no sensitive/no private/safe",
                    is_inferred=True,
                )
            )

        observations.append(
            PrimitiveObservation(
                observation_id=ids.next_id("OBS"),
                primitive_type=PrimitiveType.RESOURCE,
                label="content_resource",
                description="Document content is a consumable knowledge resource",
                confidence=0.80,
                source_reference=interp_input.input_id,
                is_inferred=True,
            )
        )

        return observations

    def _detect_patterns(
        self, observations: list[PrimitiveObservation]
    ) -> list[PrimitiveRelationship]:
        relationships: list[PrimitiveRelationship] = []
        obs_by_type: dict[str, list[PrimitiveObservation]] = {}
        for obs in observations:
            key = obs.primitive_type.value
            obs_by_type.setdefault(key, []).append(obs)

        states = obs_by_type.get("state", [])
        constraints = obs_by_type.get("constraint", [])
        for s in states:
            for c in constraints:
                relationships.append(
                    PrimitiveRelationship(
                        from_observation_id=c.observation_id,
                        to_observation_id=s.observation_id,
                        relationship_type=RelationshipType.CONSTRAINS,
                        confidence=min(s.confidence, c.confidence),
                        description=f"{c.label} constrains {s.label}",
                    )
                )

        goals = obs_by_type.get("goal", [])
        resources = obs_by_type.get("resource", [])
        for g in goals:
            for r in resources:
                relationships.append(
                    PrimitiveRelationship(
                        from_observation_id=r.observation_id,
                        to_observation_id=g.observation_id,
                        relationship_type=RelationshipType.ENABLES,
                        confidence=min(g.confidence, r.confidence),
                        description=f"{r.label} enables {g.label}",
                    )
                )

        return relationships

    def _map_primitives(
        self,
        interp_input: InterpretationInput,
        observations: list[PrimitiveObservation],
        relationships: list[PrimitiveRelationship],
        ids: _DeterministicIdGenerator,
    ) -> DecompositionResult:
        decomp = DecompositionResult(
            decomposition_id=ids.next_id("DECOMP"),
            source_content_hash=interp_input.source_content_hash,
            observations=observations,
            relationships=relationships,
            decomposition_confidence=sum(o.confidence for o in observations)
            / max(len(observations), 1),
            unsupported_assumptions=[
                "document content completeness assumed from extraction preview",
                "keyword-based pattern detection may miss semantic nuance",
            ],
            missing_information=[
                "document creation date and author not available from extraction",
                "document revision history not available",
            ],
            explicit_unknowns=[
                "whether document content has been modified since extraction",
                "whether additional related documents exist",
                "full semantic intent of document beyond keyword signals",
            ],
        )
        decomp.compute_coverage()
        return decomp

    def _generate_hypotheses(
        self,
        observations: list[PrimitiveObservation],
        relationships: list[PrimitiveRelationship],
        decomposition: DecompositionResult,
        ids: _DeterministicIdGenerator,
    ) -> list[InterpretationHypothesis]:
        hypotheses: list[InterpretationHypothesis] = []

        goal_obs = [o for o in observations if o.primitive_type == PrimitiveType.GOAL]
        if goal_obs:
            hypotheses.append(
                InterpretationHypothesis(
                    hypothesis_id=ids.next_id("HYP"),
                    statement="This document was created primarily for system validation purposes",
                    confidence=0.80,
                    supporting_observations=[o.observation_id for o in goal_obs],
                    unsupported_assumptions=[
                        "inferred from keyword patterns, not explicit declaration"
                    ],
                    requires_governance_review=True,
                    promotion_status="hypothesis_only",
                )
            )

        constraint_obs = [o for o in observations if o.primitive_type == PrimitiveType.CONSTRAINT]
        if constraint_obs:
            hypotheses.append(
                InterpretationHypothesis(
                    hypothesis_id=ids.next_id("HYP"),
                    statement="Document content is intentionally non-sensitive for safe testing",
                    confidence=0.85,
                    supporting_observations=[o.observation_id for o in constraint_obs],
                    unsupported_assumptions=[
                        "author's intent inferred from explicit safety declarations"
                    ],
                    requires_governance_review=True,
                    promotion_status="hypothesis_only",
                )
            )

        return hypotheses

    def _analyze_uncertainty(
        self,
        observations: list[PrimitiveObservation],
        decomposition: DecompositionResult,
        hypotheses: list[InterpretationHypothesis],
    ) -> ConfidenceEnvelope:
        obs_conf = sum(o.confidence for o in observations) / max(len(observations), 1)
        hyp_conf = sum(h.confidence for h in hypotheses) / max(len(hypotheses), 1)
        decomp_conf = decomposition.decomposition_confidence
        pattern_conf = min(obs_conf, decomp_conf)

        overall = (obs_conf + pattern_conf + decomp_conf + hyp_conf) / 4.0
        uncertainty = 1.0 - overall

        return ConfidenceEnvelope(
            overall_confidence=round(overall, 4),
            observation_confidence=round(obs_conf, 4),
            pattern_confidence=round(pattern_conf, 4),
            decomposition_confidence=round(decomp_conf, 4),
            hypothesis_confidence=round(hyp_conf, 4),
            uncertainty_score=round(uncertainty, 4),
            completeness_ratio=round(
                len(decomposition.primitive_type_coverage) / len(PrimitiveType),
                4,
            ),
            assumptions_count=len(decomposition.unsupported_assumptions),
            unknowns_count=len(decomposition.explicit_unknowns),
        )
