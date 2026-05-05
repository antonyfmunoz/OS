"""Phase 81 domain projections — project universal primitives/laws into domains.

Domain projections are not independent universals. They point back
to universal primitive/law IDs.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.ontology.laws import DomainLawProjection, clamp_confidence
from umh.ontology.primitives import PrimitiveProjection


class DomainType(str, Enum):
    BUSINESS = "business"
    SOFTWARE = "software"
    HUMAN = "human"
    HEALTH = "health"
    FINANCE = "finance"
    CONTENT = "content"
    OPERATIONS = "operations"
    RELATIONSHIP = "relationship"
    LEARNING = "learning"
    PHYSICAL = "physical"
    AI_SYSTEM = "ai_system"
    UMH_INTERNAL = "umh_internal"
    GENERAL = "general"
    UNKNOWN = "unknown"


def normalize_domain_type(value: str) -> DomainType:
    v = value.strip().lower()
    for m in DomainType:
        if m.value == v:
            return m
    return DomainType.UNKNOWN


@dataclass
class DomainProjectionSet:
    domain: DomainType = DomainType.UNKNOWN
    primitive_projections: list[PrimitiveProjection] = field(default_factory=list)
    law_projections: list[DomainLawProjection] = field(default_factory=list)
    domain_constraints: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    evidence_basis: str = ""
    confidence: float = 0.7
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain.value,
            "primitive_projections": [p.to_dict() for p in self.primitive_projections],
            "law_projections": [l.to_dict() for l in self.law_projections],
            "domain_constraints": self.domain_constraints,
            "examples": self.examples,
            "evidence_basis": self.evidence_basis,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DomainProjectionSet:
        return cls(
            domain=normalize_domain_type(data.get("domain", "unknown")),
            primitive_projections=[
                PrimitiveProjection.from_dict(p) for p in data.get("primitive_projections", [])
            ],
            law_projections=[
                DomainLawProjection.from_dict(l) for l in data.get("law_projections", [])
            ],
            domain_constraints=data.get("domain_constraints", []),
            examples=data.get("examples", []),
            evidence_basis=data.get("evidence_basis", ""),
            confidence=clamp_confidence(data.get("confidence", 0.7)),
            metadata=data.get("metadata", {}),
        )


def _pp(
    pid: str,
    uid: str,
    domain: str,
    local_name: str,
    defn: str,
    constraints: list[str] | None = None,
    examples: list[str] | None = None,
    evidence: str = "",
) -> PrimitiveProjection:
    return PrimitiveProjection(
        projection_id=pid,
        universal_primitive_id=uid,
        domain=domain,
        local_name=local_name,
        local_definition=defn,
        local_constraints=constraints or [],
        examples=examples or [],
        evidence_basis=evidence,
        confidence=0.75,
    )


def _lp(
    pid: str,
    uid: str,
    domain: str,
    local_name: str,
    expr: str,
    applies: list[str] | None = None,
    not_applies: list[str] | None = None,
    constraints: list[str] | None = None,
    evidence: str = "",
) -> DomainLawProjection:
    return DomainLawProjection(
        projection_id=pid,
        universal_law_id=uid,
        domain=domain,
        local_name=local_name,
        local_expression=expr,
        applies_when=applies or [],
        does_not_apply_when=not_applies or [],
        domain_constraints=constraints or [],
        evidence_basis=evidence,
        confidence=0.7,
    )


def get_default_domain_projection_sets() -> list[DomainProjectionSet]:
    return [
        DomainProjectionSet(
            domain=DomainType.BUSINESS,
            primitive_projections=[
                _pp(
                    "bp_resource",
                    "prim_resource",
                    "business",
                    "business resource",
                    "Cash, team, brand, audience, capital, distribution channel",
                    examples=["monthly ad budget", "sales team headcount"],
                ),
                _pp(
                    "bp_constraint",
                    "prim_constraint",
                    "business",
                    "business constraint",
                    "Bottleneck, cash-flow limit, team capacity, market demand ceiling",
                    examples=["runway months", "lead generation capacity"],
                ),
                _pp(
                    "bp_feedback",
                    "prim_feedback",
                    "business",
                    "market feedback",
                    "Sales data, customer response, retention, churn",
                    examples=["monthly churn rate", "NPS score"],
                ),
            ],
            law_projections=[
                _lp(
                    "bl_leverage",
                    "law_leverage",
                    "business",
                    "business leverage",
                    "Some investments multiply returns disproportionately",
                    applies=["capital allocation", "hiring", "software automation"],
                    constraints=["Context-dependent", "Wrong leverage amplifies losses"],
                ),
                _lp(
                    "bl_compounding",
                    "law_compounding",
                    "business",
                    "revenue compounding",
                    "Consistent small improvements to conversion/retention compound over time",
                    applies=["subscription models", "content libraries"],
                ),
                _lp(
                    "bl_unity",
                    "law_unity_oneness",
                    "business",
                    "business as interconnected system",
                    (
                        "Business is an interconnected system of offer, customer, team, "
                        "capital, operations, brand, market, and feedback. Optimizing one "
                        "function while damaging the whole is a failure mode."
                    ),
                    applies=["strategic decisions", "resource allocation", "organizational change"],
                    not_applies=["isolated tactical micro-decisions"],
                    constraints=[
                        "Must check systemic effects of major decisions",
                        "Do not optimize one function at expense of the whole",
                    ],
                ),
            ],
            domain_constraints=["Cash-flow constraint", "Market demand ceiling"],
            evidence_basis="Business operations / economics",
            confidence=0.75,
        ),
        DomainProjectionSet(
            domain=DomainType.SOFTWARE,
            primitive_projections=[
                _pp(
                    "sp_state",
                    "prim_state",
                    "software",
                    "software state",
                    "Database record, runtime state, cache, session, config",
                    examples=["user session", "deployment config"],
                ),
                _pp(
                    "sp_constraint",
                    "prim_constraint",
                    "software",
                    "software constraint",
                    "Interface contract, API rate limit, auth boundary",
                    examples=["rate limit 100/min", "auth scope restriction"],
                ),
            ],
            law_projections=[
                _lp(
                    "sl_entropy",
                    "law_entropy",
                    "software",
                    "technical debt",
                    "Without maintenance, software drifts toward disorder and fragility",
                    applies=["long-lived codebases", "dependency management"],
                    evidence="Software engineering experience",
                ),
                _lp(
                    "sl_temporal",
                    "law_temporal_dependency",
                    "software",
                    "migration ordering",
                    "Database migrations and deployments have strict ordering requirements",
                    applies=["schema changes", "multi-service deploys"],
                ),
                _lp(
                    "sl_unity",
                    "law_unity_oneness",
                    "software",
                    "module interdependence",
                    (
                        "Module behavior depends on dependency graph, interfaces, runtime state, "
                        "tests, and deployment context. Treating a file as isolated from callers, "
                        "contracts, side effects, and state is a failure mode."
                    ),
                    applies=["refactoring", "architecture changes", "dependency updates"],
                    not_applies=["purely local formatting changes"],
                    constraints=[
                        "Check callers and contracts before modifying interfaces",
                        "Do not treat files as isolated from their dependency graph",
                    ],
                ),
            ],
            domain_constraints=["Interface contracts", "Backward compatibility"],
            evidence_basis="Software engineering",
            confidence=0.8,
        ),
        DomainProjectionSet(
            domain=DomainType.HUMAN,
            primitive_projections=[
                _pp(
                    "hp_energy",
                    "prim_energy_effort",
                    "human",
                    "human energy",
                    "Focus, willpower, sleep quality, emotional energy",
                    examples=["morning focus window", "post-lunch dip"],
                ),
                _pp(
                    "hp_feedback",
                    "prim_feedback",
                    "human",
                    "habit reinforcement",
                    "Behavior reinforcement through reward/consequence signals",
                    examples=["exercise habit streak", "skill practice results"],
                ),
                _pp(
                    "hp_constraint",
                    "prim_constraint",
                    "human",
                    "human constraint",
                    "Cognitive load, time, attention, health limitations",
                    examples=["8h sleep requirement", "attention span limits"],
                ),
            ],
            law_projections=[
                _lp(
                    "hl_feedback",
                    "law_feedback",
                    "human",
                    "habit loop",
                    "Repeated behavior + reward signal strengthens habit formation",
                    applies=["routine building", "skill acquisition"],
                    not_applies=["one-time decisions"],
                ),
                _lp(
                    "hl_conservation",
                    "law_conservation",
                    "human",
                    "energy budget",
                    "Willpower and focus are finite daily resources",
                    applies=["task scheduling", "decision fatigue management"],
                ),
                _lp(
                    "hl_unity",
                    "law_unity_oneness",
                    "human",
                    "integrated person",
                    (
                        "Person as integrated body, mind, energy, identity, relationships, "
                        "environment, habits, history, and goals. Optimizing one dimension "
                        "while destabilizing others is a failure mode."
                    ),
                    applies=["lifestyle design", "health decisions", "identity work"],
                    not_applies=["isolated micro-habits with no systemic impact"],
                    constraints=[
                        "Do not optimize one dimension at expense of overall well-being",
                        "Check cross-domain effects of major life changes",
                    ],
                ),
            ],
            domain_constraints=["Cognitive load limits", "Sleep requirements"],
            evidence_basis="Behavioral science / neuroscience",
            confidence=0.7,
        ),
        DomainProjectionSet(
            domain=DomainType.CONTENT,
            primitive_projections=[
                _pp(
                    "cp_signal",
                    "prim_signal",
                    "content",
                    "content signal",
                    "Hook, message, story, visual, audio that captures attention",
                    examples=["video thumbnail", "email subject line"],
                ),
                _pp(
                    "cp_feedback",
                    "prim_feedback",
                    "content",
                    "audience feedback",
                    "Retention, click-through, comments, conversion metrics",
                    examples=["view-through rate", "comment sentiment"],
                ),
            ],
            law_projections=[
                _lp(
                    "cl_leverage",
                    "law_leverage",
                    "content",
                    "distribution leverage",
                    "Content repurposing and evergreen assets multiply reach per unit effort",
                    applies=["multi-platform publishing", "content libraries"],
                ),
                _lp(
                    "cl_signal_noise",
                    "law_signal_noise",
                    "content",
                    "content quality",
                    "Audience attention is scarce; signal quality determines engagement",
                    applies=["crowded markets", "algorithm feeds"],
                ),
                _lp(
                    "cl_unity",
                    "law_unity_oneness",
                    "content",
                    "communication system unity",
                    (
                        "Message, medium, audience, algorithm, timing, identity, feedback, "
                        "and offer form one communication system. Optimizing hooks while "
                        "breaking brand trust or conversion context is a failure mode."
                    ),
                    applies=["content strategy", "multi-platform campaigns", "brand building"],
                    not_applies=["isolated one-off posts with no brand context"],
                    constraints=[
                        "Do not optimize engagement metrics at expense of brand coherence",
                        "Content exists within a conversion and trust system",
                    ],
                ),
            ],
            domain_constraints=["Platform algorithm changes", "Attention scarcity"],
            evidence_basis="Content marketing / media studies",
            confidence=0.7,
        ),
        DomainProjectionSet(
            domain=DomainType.UMH_INTERNAL,
            primitive_projections=[
                _pp(
                    "up_action",
                    "prim_action",
                    "umh_internal",
                    "governed execution",
                    "An action that passes through governance before adapter dispatch",
                    examples=["execute_governed() call", "adapter backend execution"],
                ),
                _pp(
                    "up_feedback",
                    "prim_feedback",
                    "umh_internal",
                    "outcome/feedback record",
                    "OutcomeRecord and FeedbackRecord from the feedback loop",
                    examples=[
                        "OutcomeRecord with status=success",
                        "FeedbackRecord with user_positive",
                    ],
                ),
                _pp(
                    "up_resource",
                    "prim_resource",
                    "umh_internal",
                    "registry item",
                    "Adapter, capability, model, template, or any RegistryItem",
                    examples=["cap_cli.command", "bknd_local"],
                ),
                _pp(
                    "up_constraint",
                    "prim_constraint",
                    "umh_internal",
                    "governance rule",
                    "Authority level, environment restriction, approval requirement",
                    examples=["AuthorityLevel.ACT required", "requires_approval=True"],
                ),
            ],
            law_projections=[
                _lp(
                    "ul_entropy",
                    "law_entropy",
                    "umh_internal",
                    "registry staleness",
                    "Registry items and adapters degrade without maintenance/validation",
                    applies=["long-running deployments", "unmonitored adapters"],
                ),
                _lp(
                    "ul_feedback",
                    "law_feedback",
                    "umh_internal",
                    "feedback loop integration",
                    "Execution outcomes must feed back into learning for system improvement",
                    applies=["post-execution classification", "memory candidate creation"],
                ),
                _lp(
                    "ul_constraint",
                    "law_constraint_law",
                    "umh_internal",
                    "governance gating",
                    "Every execution must pass governance constraints before dispatch",
                    applies=["all adapter executions"],
                ),
                _lp(
                    "ul_unity",
                    "law_unity_oneness",
                    "umh_internal",
                    "runtime coherence",
                    (
                        "Differentiated modules share one governed runtime, control plane, "
                        "storage discipline, registry, ontology, and execution spine. "
                        "Fragmented tools/stores/agents creating multiple hidden sources "
                        "of truth is a failure mode."
                    ),
                    applies=["architecture decisions", "new module creation", "integration work"],
                    not_applies=["internal implementation details of a single module"],
                    constraints=[
                        "Maintain single source of truth across subsystems",
                        "New modules must integrate with existing governance and registry",
                    ],
                ),
            ],
            domain_constraints=["Governance authority levels", "Adapter contract compliance"],
            evidence_basis="UMH architecture / Phase 75B-80 implementation",
            confidence=0.85,
        ),
    ]


_DEFAULT_PROJECTIONS: list[DomainProjectionSet] | None = None


def get_domain_projections() -> list[DomainProjectionSet]:
    global _DEFAULT_PROJECTIONS
    if _DEFAULT_PROJECTIONS is None:
        _DEFAULT_PROJECTIONS = get_default_domain_projection_sets()
    return list(_DEFAULT_PROJECTIONS)


def get_projection_by_domain(domain: str) -> DomainProjectionSet | None:
    dt = normalize_domain_type(domain)
    for ps in get_domain_projections():
        if ps.domain == dt:
            return ps
    return None


def project_primitive(universal_primitive_id: str, domain: str) -> PrimitiveProjection | None:
    ps = get_projection_by_domain(domain)
    if ps is None:
        return None
    for pp in ps.primitive_projections:
        if pp.universal_primitive_id == universal_primitive_id:
            return pp
    return None


def project_law(universal_law_id: str, domain: str) -> DomainLawProjection | None:
    ps = get_projection_by_domain(domain)
    if ps is None:
        return None
    for lp in ps.law_projections:
        if lp.universal_law_id == universal_law_id:
            return lp
    return None
