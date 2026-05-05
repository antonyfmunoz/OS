"""Phase 81 universal law contracts.

Each law declares scope, evidence basis, governed primitives,
state-transition effects, constraints created, and failure conditions.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LawType(str, Enum):
    PHYSICAL = "physical"
    FORMAL = "formal"
    INFORMATIONAL = "informational"
    SYSTEMS = "systems"
    CYBERNETIC = "cybernetic"
    BIOLOGICAL = "biological"
    COGNITIVE = "cognitive"
    ECONOMIC = "economic"
    SOFTWARE = "software"
    DOMAIN_SPECIFIC = "domain_specific"
    HEURISTIC = "heuristic"
    POLICY = "policy"
    UNKNOWN = "unknown"


def normalize_law_type(value: str) -> LawType:
    v = value.strip().lower()
    for m in LawType:
        if m.value == v:
            return m
    return LawType.UNKNOWN


class LawScope(str, Enum):
    UNIVERSAL = "universal"
    DOMAIN_PROJECTION = "domain_projection"
    LOCAL_RULE = "local_rule"
    HEURISTIC = "heuristic"
    POLICY = "policy"
    UNKNOWN = "unknown"


def normalize_law_scope(value: str) -> LawScope:
    v = value.strip().lower()
    for m in LawScope:
        if m.value == v:
            return m
    return LawScope.UNKNOWN


class UniversalLawName(str, Enum):
    CAUSALITY = "causality"
    CORRESPONDENCE = "correspondence"
    POLARITY = "polarity"
    FEEDBACK = "feedback"
    COMPOUNDING = "compounding"
    ENTROPY = "entropy"
    EMERGENCE = "emergence"
    CONSTRAINT = "constraint"
    EQUILIBRIUM = "equilibrium"
    TEMPORAL_DEPENDENCY = "temporal_dependency"
    CONSERVATION = "conservation"
    RESOURCE_LIMITATION = "resource_limitation"
    LEVERAGE = "leverage"
    SIGNAL_NOISE = "signal_noise"
    UNCERTAINTY = "uncertainty"
    UNITY_ONENESS = "unity_oneness"
    UNKNOWN = "unknown"


_UNITY_ALIASES: frozenset[str] = frozenset(
    {
        "unity",
        "oneness",
        "unity_oneness",
        "unity / oneness",
        "law of unity",
        "law of oneness",
    }
)


def normalize_universal_law_name(value: str) -> UniversalLawName:
    v = value.strip().lower()
    if v in _UNITY_ALIASES:
        return UniversalLawName.UNITY_ONENESS
    for m in UniversalLawName:
        if m.value == v:
            return m
    return UniversalLawName.UNKNOWN


def clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, value))


def _law_id() -> str:
    return f"law_{uuid.uuid4().hex[:10]}"


@dataclass
class UniversalLaw:
    law_id: str
    name: str = ""
    law_name: UniversalLawName = UniversalLawName.UNKNOWN
    law_type: LawType = LawType.UNKNOWN
    scope: LawScope = LawScope.UNIVERSAL
    definition: str = ""
    governs: list[str] = field(default_factory=list)
    applies_to_primitives: list[str] = field(default_factory=list)
    state_transition_effect: str = ""
    constraints_created: list[str] = field(default_factory=list)
    abstraction_scope: str = "universal"
    evidence_basis: str = ""
    failure_conditions: list[str] = field(default_factory=list)
    confidence: float = 0.8
    examples: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "law_id": self.law_id,
            "name": self.name,
            "law_name": self.law_name.value,
            "law_type": self.law_type.value,
            "scope": self.scope.value,
            "definition": self.definition,
            "governs": self.governs,
            "applies_to_primitives": self.applies_to_primitives,
            "state_transition_effect": self.state_transition_effect,
            "constraints_created": self.constraints_created,
            "abstraction_scope": self.abstraction_scope,
            "evidence_basis": self.evidence_basis,
            "failure_conditions": self.failure_conditions,
            "confidence": self.confidence,
            "examples": self.examples,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UniversalLaw:
        return cls(
            law_id=data.get("law_id", _law_id()),
            name=data.get("name", ""),
            law_name=normalize_universal_law_name(data.get("law_name", "unknown")),
            law_type=normalize_law_type(data.get("law_type", "unknown")),
            scope=normalize_law_scope(data.get("scope", "universal")),
            definition=data.get("definition", ""),
            governs=data.get("governs", []),
            applies_to_primitives=data.get("applies_to_primitives", []),
            state_transition_effect=data.get("state_transition_effect", ""),
            constraints_created=data.get("constraints_created", []),
            abstraction_scope=data.get("abstraction_scope", "universal"),
            evidence_basis=data.get("evidence_basis", ""),
            failure_conditions=data.get("failure_conditions", []),
            confidence=clamp_confidence(data.get("confidence", 0.8)),
            examples=data.get("examples", []),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DomainLawProjection:
    projection_id: str
    universal_law_id: str = ""
    domain: str = ""
    local_name: str = ""
    local_expression: str = ""
    applies_when: list[str] = field(default_factory=list)
    does_not_apply_when: list[str] = field(default_factory=list)
    domain_constraints: list[str] = field(default_factory=list)
    evidence_basis: str = ""
    confidence: float = 0.7
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_id": self.projection_id,
            "universal_law_id": self.universal_law_id,
            "domain": self.domain,
            "local_name": self.local_name,
            "local_expression": self.local_expression,
            "applies_when": self.applies_when,
            "does_not_apply_when": self.does_not_apply_when,
            "domain_constraints": self.domain_constraints,
            "evidence_basis": self.evidence_basis,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DomainLawProjection:
        return cls(
            projection_id=data.get("projection_id", f"lproj_{uuid.uuid4().hex[:10]}"),
            universal_law_id=data.get("universal_law_id", ""),
            domain=data.get("domain", ""),
            local_name=data.get("local_name", ""),
            local_expression=data.get("local_expression", ""),
            applies_when=data.get("applies_when", []),
            does_not_apply_when=data.get("does_not_apply_when", []),
            domain_constraints=data.get("domain_constraints", []),
            evidence_basis=data.get("evidence_basis", ""),
            confidence=clamp_confidence(data.get("confidence", 0.7)),
            metadata=data.get("metadata", {}),
        )


@dataclass
class LawClassification:
    item_id: str
    label: str = ""
    law_type: LawType = LawType.UNKNOWN
    scope: LawScope = LawScope.UNKNOWN
    is_universal: bool = False
    reason: str = ""
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "label": self.label,
            "law_type": self.law_type.value,
            "scope": self.scope.value,
            "is_universal": self.is_universal,
            "reason": self.reason,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


def classify_law_scope(
    label: str,
    law_type: str = "",
    is_domain_specific: bool = False,
    is_heuristic: bool = False,
    is_policy: bool = False,
) -> LawClassification:
    lt = normalize_law_type(law_type)
    if is_policy:
        return LawClassification(
            item_id=f"cls_{label}",
            label=label,
            law_type=lt,
            scope=LawScope.POLICY,
            is_universal=False,
            reason="Classified as policy",
            confidence=0.9,
        )
    if is_heuristic:
        return LawClassification(
            item_id=f"cls_{label}",
            label=label,
            law_type=lt,
            scope=LawScope.HEURISTIC,
            is_universal=False,
            reason="Classified as heuristic",
            confidence=0.8,
        )
    if is_domain_specific or lt == LawType.DOMAIN_SPECIFIC:
        return LawClassification(
            item_id=f"cls_{label}",
            label=label,
            law_type=lt,
            scope=LawScope.DOMAIN_PROJECTION,
            is_universal=False,
            reason="Domain-specific rule, not universal",
            confidence=0.8,
        )
    return LawClassification(
        item_id=f"cls_{label}",
        label=label,
        law_type=lt,
        scope=LawScope.UNIVERSAL,
        is_universal=True,
        reason="Cross-domain law",
        confidence=0.7,
    )


def _make_law(
    name: str,
    law_name: str,
    law_type: str,
    definition: str,
    governs: list[str],
    primitives: list[str],
    transition: str,
    constraints: list[str],
    failures: list[str],
    evidence: str,
    examples: list[str],
) -> UniversalLaw:
    return UniversalLaw(
        law_id=f"law_{name}",
        name=name,
        law_name=normalize_universal_law_name(law_name),
        law_type=normalize_law_type(law_type),
        scope=LawScope.UNIVERSAL,
        definition=definition,
        governs=governs,
        applies_to_primitives=primitives,
        state_transition_effect=transition,
        constraints_created=constraints,
        evidence_basis=evidence,
        failure_conditions=failures,
        confidence=0.85,
        examples=examples,
        tags=["universal", "kernel"],
    )


def get_default_universal_laws() -> list[UniversalLaw]:
    return [
        _make_law(
            "causality",
            "causality",
            "systems",
            "Actions may produce effects through mechanisms over time; effects have causes.",
            governs=["action-outcome relationships", "temporal ordering of effects"],
            primitives=["action", "change", "outcome", "time"],
            transition="Actions may produce state changes through causal mechanisms",
            constraints=["Cannot attribute effect without mechanism or evidence"],
            failures=[
                "Insufficient evidence",
                "Confounding variables",
                "Correlation-only observations",
                "Delayed or indirect effects",
            ],
            evidence="Physical reality / systems theory / scientific method",
            examples=[
                "Code change causes test failure",
                "Ad spend causes lead generation",
                "Exercise causes fitness improvement",
            ],
        ),
        _make_law(
            "correspondence",
            "correspondence",
            "formal",
            "Patterns can map across abstraction layers only when primitive relationships are preserved.",
            governs=["abstraction-layer mapping", "analogy validity"],
            primitives=["relationship", "entity", "information"],
            transition="Structural patterns transfer across domains when primitive topology matches",
            constraints=[
                "Mapping requires relationship preservation",
                "Domain constraints may invalidate mapping",
            ],
            failures=[
                "Primitive relations differ",
                "Domain constraints diverge",
                "Surface similarity without structural match",
            ],
            evidence="Category theory / formal modeling / isomorphism",
            examples=[
                "Nervous system maps to control plane only if feedback loops match",
                "Market supply-demand maps to resource allocation",
            ],
        ),
        _make_law(
            "polarity",
            "polarity",
            "systems",
            "Every system contains tensions between opposing forces; resolution drives dynamics.",
            governs=["tradeoff identification", "tension dynamics"],
            primitives=["constraint", "goal_attractor", "resource", "action"],
            transition="Resolving one tension may create or shift another",
            constraints=[
                "Cannot eliminate all tension simultaneously",
                "Optimization along one axis degrades another",
            ],
            failures=[
                "False dichotomy",
                "Missing third option",
                "Over-simplification of multi-axis tradeoffs",
            ],
            evidence="Dialectics / optimization theory / systems dynamics",
            examples=["Speed vs quality", "Exploration vs exploitation", "Growth vs profitability"],
        ),
        _make_law(
            "feedback",
            "feedback",
            "cybernetic",
            "Systems adjust behavior based on information about prior outcomes.",
            governs=["learning loops", "self-correction", "reinforcement"],
            primitives=["feedback", "action", "outcome", "signal", "goal_attractor"],
            transition="Outcome information feeds back to modify future action selection",
            constraints=[
                "Requires timely signal delivery",
                "Feedback must be attributable to action",
            ],
            failures=[
                "Delayed feedback",
                "Noisy signal",
                "Wrong attribution",
                "Feedback ignored or suppressed",
            ],
            evidence="Cybernetics / control theory / behavioral science",
            examples=[
                "A/B test results adjust marketing",
                "Code review improves quality",
                "Customer churn signals product issues",
            ],
        ),
        _make_law(
            "compounding",
            "compounding",
            "systems",
            "Repeated application of small gains or losses accumulates nonlinearly over time.",
            governs=["growth dynamics", "decay dynamics", "accumulation"],
            primitives=["time", "change", "resource", "outcome"],
            transition="Small consistent changes compound into large state differences over time",
            constraints=[
                "Requires sustained consistent input",
                "Subject to rate limits and saturation",
            ],
            failures=[
                "Interruption breaks compound chain",
                "Diminishing returns at scale",
                "Negative compounding from consistent errors",
            ],
            evidence="Mathematics / finance / skill acquisition / evolutionary biology",
            examples=[
                "Compound interest",
                "Skill practice",
                "Technical debt accumulation",
                "Content library growth",
            ],
        ),
        _make_law(
            "entropy",
            "entropy",
            "physical",
            "Systems tend toward disorder, drift, decay, or uncertainty without maintenance.",
            governs=["degradation", "maintenance requirements", "information loss"],
            primitives=["state", "change", "time", "resource", "information"],
            transition="Without energy/resource input, systems drift toward higher disorder",
            constraints=[
                "Local entropy can decrease with external energy input",
                "Maintenance cost is ongoing",
            ],
            failures=[
                "Assumes closed system",
                "Ignores external energy sources",
                "Over-applies to self-organizing systems",
            ],
            evidence="Thermodynamics / information theory / software engineering",
            examples=[
                "Technical debt growth",
                "Skill atrophy",
                "Data staleness",
                "Relationship drift without contact",
            ],
        ),
        _make_law(
            "emergence",
            "emergence",
            "systems",
            "Complex behavior arises from simple component interactions that cannot be predicted from components alone.",
            governs=["system-level behavior", "composition effects"],
            primitives=["entity", "relationship", "state", "change"],
            transition="Component interactions produce system-level properties not present in individual components",
            constraints=[
                "Emergent properties are not designed, they arise",
                "Prediction requires simulation or observation",
            ],
            failures=[
                "Reductionism fails to predict emergent behavior",
                "Over-attributing emergence to simple effects",
            ],
            evidence="Complexity science / biology / network theory",
            examples=[
                "Market prices from individual trades",
                "Traffic jams from individual driving",
                "Culture from individual behaviors",
            ],
        ),
        _make_law(
            "constraint_law",
            "constraint",
            "formal",
            "Every system operates within boundaries that limit valid states and transitions.",
            governs=["validity boundaries", "feasibility limits"],
            primitives=["constraint", "state", "action", "environment"],
            transition="Constraints filter the space of reachable states and permissible actions",
            constraints=[
                "Constraints interact — satisfying one may violate another",
                "Hidden constraints exist",
            ],
            failures=[
                "Unknown constraints",
                "Constraint relaxation without validation",
                "Over-constraining eliminates viable solutions",
            ],
            evidence="Optimization theory / formal methods / governance",
            examples=["API rate limits", "Budget boundaries", "Physics laws", "Legal requirements"],
        ),
        _make_law(
            "equilibrium",
            "equilibrium",
            "systems",
            "Systems tend toward stable states where opposing forces balance.",
            governs=["stability dynamics", "market clearing", "homeostasis"],
            primitives=["state", "constraint", "feedback", "resource"],
            transition="Disturbed systems move toward a new balance point through corrective feedback",
            constraints=[
                "Equilibrium may be suboptimal",
                "Multiple equilibria possible",
                "External shocks can shift equilibrium",
            ],
            failures=[
                "Unstable equilibrium collapses",
                "Path-dependent lock-in",
                "Assumes feedback mechanisms exist",
            ],
            evidence="Physics / economics / ecology / control theory",
            examples=[
                "Supply-demand price equilibrium",
                "Homeostasis in organisms",
                "System load balancing",
            ],
        ),
        _make_law(
            "temporal_dependency",
            "temporal_dependency",
            "formal",
            "Some operations must occur in a specific order; sequence constraints are real.",
            governs=["ordering requirements", "sequencing", "dependency chains"],
            primitives=["time", "action", "change", "constraint"],
            transition="Later operations depend on results of earlier ones; reordering can invalidate outcomes",
            constraints=[
                "Cannot parallelize dependent operations",
                "Ordering violations produce invalid states",
            ],
            failures=[
                "Hidden dependencies",
                "Assumed independence that does not hold",
                "Circular dependencies",
            ],
            evidence="Formal modeling / distributed systems / project management",
            examples=[
                "Database migration order",
                "Build dependency graph",
                "Onboarding sequence",
                "Boot sequence steps",
            ],
        ),
        _make_law(
            "conservation",
            "conservation",
            "physical",
            "Resources and energy are finite; consumption in one area reduces availability elsewhere.",
            governs=["resource allocation", "budget constraints", "zero-sum dynamics"],
            primitives=["resource", "energy_effort", "constraint", "action"],
            transition="Using resources for one purpose makes them unavailable for another",
            constraints=["Total resource is bounded", "Allocation is a tradeoff"],
            failures=[
                "Assumes strict conservation — some resources regenerate",
                "Ignores value creation from combination",
            ],
            evidence="Thermodynamics / economics / accounting",
            examples=[
                "Budget allocation",
                "Time management",
                "Compute resource scheduling",
                "Attention allocation",
            ],
        ),
        _make_law(
            "leverage",
            "leverage",
            "economic",
            "Some resource/action configurations multiply outcome relative to input.",
            governs=["efficiency", "force multiplication", "disproportionate returns"],
            primitives=["resource", "action", "outcome", "constraint"],
            transition="Leveraged actions produce outsized returns per unit input",
            constraints=["Leverage is context-dependent", "Wrong leverage amplifies losses too"],
            failures=[
                "Wrong context",
                "Hidden constraints",
                "Diminishing returns",
                "Misidentified leverage point",
            ],
            evidence="Economics / systems thinking / engineering",
            examples=[
                "Software scales without per-unit cost",
                "Delegation multiplies output",
                "Content repurposing",
                "Capital allocation",
            ],
        ),
        _make_law(
            "signal_noise",
            "signal_noise",
            "informational",
            "Useful information is embedded in noise; extraction quality determines decision quality.",
            governs=["information quality", "decision inputs", "measurement"],
            primitives=["information", "signal", "uncertainty", "feedback"],
            transition="Better signal extraction leads to better state estimation and action selection",
            constraints=[
                "Perfect signal extraction is impossible",
                "Filtering has computational cost",
            ],
            failures=[
                "Overfitting to noise",
                "Filtering out real signal",
                "Insufficient data for separation",
            ],
            evidence="Information theory / signal processing / statistics",
            examples=[
                "A/B test statistical significance",
                "Log analysis vs log noise",
                "Market signal vs rumor",
            ],
        ),
        _make_law(
            "uncertainty_law",
            "uncertainty",
            "informational",
            "Every observation, prediction, and model carries irreducible uncertainty.",
            governs=["prediction limits", "confidence bounds", "risk assessment"],
            primitives=["uncertainty", "information", "state", "outcome"],
            transition="Decisions must account for what is not known; overconfidence creates fragility",
            constraints=["Cannot eliminate all uncertainty", "Must budget for unknown unknowns"],
            failures=["Treating estimates as certainty", "Ignoring tail risks", "False precision"],
            evidence="Probability theory / epistemology / risk management",
            examples=[
                "Weather forecasting limits",
                "Startup outcome uncertainty",
                "Model prediction intervals",
            ],
        ),
        UniversalLaw(
            law_id="law_unity_oneness",
            name="unity_oneness",
            law_name=UniversalLawName.UNITY_ONENESS,
            law_type=LawType.SYSTEMS,
            scope=LawScope.UNIVERSAL,
            definition=(
                "All apparent parts are differentiated expressions within a larger relational "
                "whole. Entities, states, relationships, actions, feedback loops, contradictions, "
                "and outcomes may be distinguished operationally, but they are not absolutely "
                "isolated from shared context, dependencies, constraints, and systemic effects."
            ),
            governs=[
                "relational context",
                "differentiation",
                "system coherence",
                "interdependence",
                "boundary-within-whole",
                "non-isolated effects",
            ],
            applies_to_primitives=[
                "entity",
                "relationship",
                "state",
                "environment",
                "constraint",
                "resource",
                "action",
                "feedback",
                "outcome",
                "uncertainty",
            ],
            state_transition_effect=(
                "Local state transitions may create wider effects through relationships, "
                "dependencies, shared resources, constraints, feedback loops, and common context."
            ),
            constraints_created=[
                "Do not model entities as absolutely isolated.",
                "Preserve both distinction and relationship.",
                "Maintain explicit boundaries while modeling interdependence.",
                "Check systemic effects before high-impact local action.",
            ],
            abstraction_scope="universal",
            evidence_basis=(
                "Cross-domain systems abstraction / relational modeling / systems theory / "
                "network and dependency reasoning / operational coherence principle"
            ),
            failure_conditions=[
                "Do not collapse differentiation into sameness.",
                "Do not erase boundaries, identity, ownership, scope, contracts, or governance.",
                "Do not assume all relations are equally relevant.",
                "Do not claim empirical certainty for metaphysical interpretations without evidence.",
                "Do not use unity to bypass authorization or safety boundaries.",
            ],
            confidence=0.85,
            examples=[
                "Single execution spine with differentiated modules",
                "Local action causing downstream effects through dependencies",
                "One world-model context with scoped entities",
                "Many interface surfaces sharing one control boundary",
                "Human/business/software systems understood through relational context",
            ],
            tags=["universal", "kernel"],
            metadata={
                "doctrine": "differentiated unity",
                "metaphysical_note": (
                    "May correspond to oneness/non-duality framing, but operational "
                    "use is relational/systemic."
                ),
                "implementation_projection": [
                    "single execution spine",
                    "shared world model",
                    "storage discipline",
                    "governance boundary",
                    "typed contracts",
                ],
            },
        ),
    ]


_DEFAULT_LAWS: list[UniversalLaw] | None = None


def get_laws() -> list[UniversalLaw]:
    global _DEFAULT_LAWS
    if _DEFAULT_LAWS is None:
        _DEFAULT_LAWS = get_default_universal_laws()
    return list(_DEFAULT_LAWS)


def get_law_by_id(law_id: str) -> UniversalLaw | None:
    for law in get_laws():
        if law.law_id == law_id:
            return law
    return None


def get_law_by_name(name: str) -> UniversalLaw | None:
    nl = name.lower()
    for law in get_laws():
        if law.name.lower() == nl:
            return law
    return None


def export_storage_descriptors() -> list[Any]:
    from umh.storage.contracts import (
        StorageBackendType,
        StorageMutability,
        StorageRecordDescriptor,
        StorageRecordType,
        StorageScope,
        StorageSource,
    )

    descriptors: list[StorageRecordDescriptor] = []
    for law in get_laws():
        descriptors.append(
            StorageRecordDescriptor(
                record_id=law.law_id,
                record_type=StorageRecordType.ONTOLOGY_LAW,
                scope=StorageScope.SYSTEM,
                mutability=StorageMutability.IMMUTABLE,
                source=StorageSource.ONTOLOGY,
                backend_type=StorageBackendType.MEMORY,
            )
        )
    return descriptors
