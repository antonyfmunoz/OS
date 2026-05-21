"""Phase 81 correspondence validation — validate cross-domain structural mappings.

Correspondence is validated, not assumed. Analogy breaks are explicit.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.ontology.primitives import clamp_confidence


class CorrespondenceStatus(str, Enum):
    VALIDATED = "validated"
    PARTIAL = "partial"
    WEAK = "weak"
    INVALID = "invalid"
    UNKNOWN = "unknown"


def normalize_correspondence_status(value: str) -> CorrespondenceStatus:
    v = value.strip().lower()
    for m in CorrespondenceStatus:
        if m.value == v:
            return m
    return CorrespondenceStatus.UNKNOWN


@dataclass
class CorrespondenceMap:
    map_id: str
    source_domain: str = ""
    target_domain: str = ""
    source_layer: str = ""
    target_layer: str = ""
    source_pattern: str = ""
    target_pattern: str = ""
    shared_primitives: list[str] = field(default_factory=list)
    shared_laws: list[str] = field(default_factory=list)
    preserved_relationships: list[str] = field(default_factory=list)
    differing_constraints: list[str] = field(default_factory=list)
    analogy_breaks: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    status: CorrespondenceStatus = CorrespondenceStatus.UNKNOWN
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "map_id": self.map_id,
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "source_layer": self.source_layer,
            "target_layer": self.target_layer,
            "source_pattern": self.source_pattern,
            "target_pattern": self.target_pattern,
            "shared_primitives": self.shared_primitives,
            "shared_laws": self.shared_laws,
            "preserved_relationships": self.preserved_relationships,
            "differing_constraints": self.differing_constraints,
            "analogy_breaks": self.analogy_breaks,
            "evidence": self.evidence,
            "status": self.status.value,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class CorrespondenceCheck:
    check_id: str
    map_id: str = ""
    primitives_match: bool = False
    relationships_preserved: bool = False
    constraints_compatible: bool = False
    evidence_sufficient: bool = False
    breaks_identified: list[str] = field(default_factory=list)
    status: CorrespondenceStatus = CorrespondenceStatus.UNKNOWN
    confidence: float = 0.5
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "map_id": self.map_id,
            "primitives_match": self.primitives_match,
            "relationships_preserved": self.relationships_preserved,
            "constraints_compatible": self.constraints_compatible,
            "evidence_sufficient": self.evidence_sufficient,
            "breaks_identified": self.breaks_identified,
            "status": self.status.value,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def validate_correspondence_map(cmap: CorrespondenceMap) -> CorrespondenceCheck:
    check_id = f"chk_{uuid.uuid4().hex[:10]}"
    breaks = list(cmap.analogy_breaks)
    warnings: list[str] = []

    primitives_match = len(cmap.shared_primitives) > 0
    relationships_preserved = len(cmap.preserved_relationships) > 0
    constraints_compatible = len(cmap.differing_constraints) == 0
    evidence_sufficient = len(cmap.evidence) > 0

    if not primitives_match:
        warnings.append("No shared primitives identified")
    if not relationships_preserved:
        warnings.append("No preserved relationships identified")
    if not evidence_sufficient:
        warnings.append("No supporting evidence provided")

    if (
        primitives_match
        and relationships_preserved
        and constraints_compatible
        and evidence_sufficient
    ):
        status = CorrespondenceStatus.VALIDATED
        conf = 0.8
    elif primitives_match and relationships_preserved:
        status = CorrespondenceStatus.PARTIAL
        conf = 0.6
    elif primitives_match:
        status = CorrespondenceStatus.WEAK
        conf = 0.4
    else:
        status = CorrespondenceStatus.INVALID
        conf = 0.2

    if breaks:
        if status == CorrespondenceStatus.VALIDATED:
            status = CorrespondenceStatus.PARTIAL
            conf = 0.65
        conf = max(0.1, conf - 0.05 * len(breaks))

    return CorrespondenceCheck(
        check_id=check_id,
        map_id=cmap.map_id,
        primitives_match=primitives_match,
        relationships_preserved=relationships_preserved,
        constraints_compatible=constraints_compatible,
        evidence_sufficient=evidence_sufficient,
        breaks_identified=breaks,
        status=status,
        confidence=clamp_confidence(conf),
        warnings=warnings,
    )


def get_default_correspondence_maps() -> list[CorrespondenceMap]:
    return [
        CorrespondenceMap(
            map_id="corr_nervous_system_control_plane",
            source_domain="human",
            target_domain="umh_internal",
            source_pattern="nervous system (sensory input -> processing -> motor output)",
            target_pattern="control plane (input -> governance -> execution -> outcome)",
            shared_primitives=["signal", "feedback", "action", "constraint"],
            shared_laws=["feedback", "causality"],
            preserved_relationships=[
                "signal triggers processing",
                "processing selects action",
                "outcome feeds back",
            ],
            differing_constraints=[
                "Biological parallelism vs sequential execution",
                "Neuroplasticity vs code deployment",
            ],
            analogy_breaks=[
                "Nervous system is massively parallel; UMH control plane is largely sequential",
                "Biological adaptation is continuous; software adaptation requires explicit deployment",
                "Nervous system has no governance gate equivalent — reflexes bypass deliberation",
            ],
            evidence=[
                "Both use signal-processing-action loops",
                "Both have feedback-driven adaptation",
            ],
            status=CorrespondenceStatus.PARTIAL,
            confidence=0.55,
        ),
        CorrespondenceMap(
            map_id="corr_hands_adapters",
            source_domain="human",
            target_domain="umh_internal",
            source_pattern="hands/fingers (fine motor actuation of physical world)",
            target_pattern="adapters (CLI, filesystem, HTTP, browser — actuation of digital world)",
            shared_primitives=["action", "constraint", "environment"],
            shared_laws=["constraint_law", "causality"],
            preserved_relationships=[
                "Capability-specific actuation",
                "Environment constrains available actions",
            ],
            differing_constraints=[
                "Physical dexterity vs API contracts",
                "Tactile feedback vs status codes",
            ],
            analogy_breaks=[
                "Hands have continuous proprioceptive feedback; adapters get discrete status responses",
                "Hands can improvise novel grips; adapters are fixed to defined capabilities",
                "Physical manipulation is analog; adapter execution is digital/discrete",
            ],
            evidence=[
                "Both are capability-specific actuators",
                "Both operate within environmental constraints",
            ],
            status=CorrespondenceStatus.PARTIAL,
            confidence=0.5,
        ),
        CorrespondenceMap(
            map_id="corr_memory_systems",
            source_domain="human",
            target_domain="umh_internal",
            source_pattern="human memory (short-term, long-term, episodic, procedural)",
            target_pattern="UMH memory (TraceStore, MemoryCandidate, FeedbackRecord)",
            shared_primitives=["information", "state", "feedback"],
            shared_laws=["entropy", "feedback"],
            preserved_relationships=[
                "Experience stored for future retrieval",
                "Repeated patterns strengthen retention",
            ],
            differing_constraints=[
                "Human memory is associative and lossy; UMH storage is structured and exact"
            ],
            analogy_breaks=[
                "Human memory reconstructs; UMH memory retrieves exact records",
                "Human memory has emotional weighting; UMH has confidence scores",
                "Human forgetting is automatic; UMH requires explicit promotion/pruning",
            ],
            evidence=["Both store experience for future use", "Both degrade without maintenance"],
            status=CorrespondenceStatus.PARTIAL,
            confidence=0.5,
        ),
        CorrespondenceMap(
            map_id="corr_habit_workflow",
            source_domain="human",
            target_domain="umh_internal",
            source_pattern="habit loop (cue -> routine -> reward)",
            target_pattern="workflow/template loop (trigger -> execution -> outcome classification)",
            shared_primitives=["signal", "action", "feedback", "outcome"],
            shared_laws=["feedback", "compounding"],
            preserved_relationships=[
                "Trigger initiates behavior",
                "Outcome reinforces or extinguishes pattern",
            ],
            differing_constraints=["Habits are subconscious; workflows are explicitly defined"],
            analogy_breaks=[
                "Habits form through repetition without explicit programming; workflows are designed",
                "Habit reward is emotional/chemical; workflow reward is outcome classification",
                "Habits resist change; workflows can be redeployed instantly",
            ],
            evidence=["Both use trigger-action-feedback loops", "Both compound with repetition"],
            status=CorrespondenceStatus.PARTIAL,
            confidence=0.55,
        ),
        CorrespondenceMap(
            map_id="corr_homeostasis_observability",
            source_domain="human",
            target_domain="umh_internal",
            source_pattern="organism homeostasis (temperature, pH, blood sugar regulation)",
            target_pattern="system health (observability, governance, self-monitoring)",
            shared_primitives=["state", "feedback", "constraint", "signal"],
            shared_laws=["equilibrium", "feedback", "entropy"],
            preserved_relationships=[
                "Deviation detected -> corrective action -> return to baseline"
            ],
            differing_constraints=[
                "Biological regulation is autonomous; UMH requires operator intervention"
            ],
            analogy_breaks=[
                "Biological homeostasis is continuous and autonomous; UMH health checks are periodic and read-only",
                "Organisms self-heal; UMH requires explicit remediation",
                "Biological systems have billions of parallel sensors; UMH has limited observability points",
            ],
            evidence=[
                "Both maintain system health through feedback loops",
                "Both degrade without monitoring",
            ],
            status=CorrespondenceStatus.PARTIAL,
            confidence=0.5,
        ),
        CorrespondenceMap(
            map_id="corr_market_feedback_allocation",
            source_domain="business",
            target_domain="business",
            source_pattern="market feedback signals (sales, churn, engagement)",
            target_pattern="resource allocation decisions (budget, team, focus)",
            shared_primitives=["feedback", "resource", "signal", "outcome"],
            shared_laws=["feedback", "equilibrium", "leverage"],
            preserved_relationships=[
                "Market signals inform allocation",
                "Allocation affects outcomes",
            ],
            differing_constraints=["Market signals are noisy and delayed"],
            analogy_breaks=[
                "Market feedback is aggregate; individual decisions are specific",
                "Allocation changes are discrete; market response is continuous",
            ],
            evidence=["Standard business operations pattern"],
            status=CorrespondenceStatus.PARTIAL,
            confidence=0.6,
        ),
    ]


_DEFAULT_MAPS: list[CorrespondenceMap] | None = None


def get_correspondence_maps() -> list[CorrespondenceMap]:
    global _DEFAULT_MAPS
    if _DEFAULT_MAPS is None:
        _DEFAULT_MAPS = get_default_correspondence_maps()
    return list(_DEFAULT_MAPS)
