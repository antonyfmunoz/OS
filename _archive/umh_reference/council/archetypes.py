"""Phase 85B thinker archetypes — typed advisory lenses for council deliberation.

Each archetype represents a distinct thinking mode (contrarian, skeptic,
first-principles, leverage-maximizer, etc.). Archetypes are assigned to
deliberation requests based on domain and urgency, then generate
deterministic stub thinker reports.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.council.contracts import (
    Assumption,
    ConfidenceLevel,
    DeliberationDomain,
    EvidenceItem,
    EvidenceStrength,
    UrgencyLevel,
    _council_id,
    clamp_score,
)
from umh.council.perspective import PerspectiveReport, create_perspective_report


class ThinkerArchetype(str, Enum):
    CONTRARIAN = "contrarian"
    SKEPTIC = "skeptic"
    RED_TEAM = "red_team"
    BLUE_TEAM = "blue_team"
    FIRST_PRINCIPLES = "first_principles"
    LEVERAGE_MAXIMIZER = "leverage_maximizer"
    FUTURE_BACKCASTER = "future_backcaster"
    OPERATOR = "operator"
    STRATEGIST = "strategist"
    TECHNICAL_ARCHITECT = "technical_architect"
    FINANCIAL_ANALYST = "financial_analyst"
    LEGAL_REGULATORY = "legal_regulatory"
    SECURITY_REVIEWER = "security_reviewer"
    CUSTOMER_ADVOCATE = "customer_advocate"
    PRODUCT_REVIEWER = "product_reviewer"
    SYSTEMS_THINKER = "systems_thinker"
    ONTOLOGY_LAW_REVIEWER = "ontology_law_reviewer"
    MEMORY_HISTORIAN = "memory_historian"
    QUALITY_JUDGE = "quality_judge"
    EVIDENCE_JUDGE = "evidence_judge"
    BRAND_STRATEGIST = "brand_strategist"
    GROWTH_DISTRIBUTION = "growth_distribution"
    HUMAN_FACTOR_REVIEWER = "human_factor_reviewer"
    UNKNOWN = "unknown"


def normalize_thinker_archetype(value: str) -> ThinkerArchetype:
    v = value.strip().lower().replace(" ", "_").replace("-", "_")
    for m in ThinkerArchetype:
        if m.value == v:
            return m
    return ThinkerArchetype.UNKNOWN


@dataclass
class ThinkerProfile:
    """Describes a single thinker archetype's lens and biases."""

    archetype: ThinkerArchetype = ThinkerArchetype.UNKNOWN
    name: str = ""
    lens: str = ""
    asks: list[str] = field(default_factory=list)
    blind_spots: list[str] = field(default_factory=list)
    weight: float = 1.0
    adversarial: bool = False
    domains: list[DeliberationDomain] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "archetype": self.archetype.value,
            "name": self.name,
            "lens": self.lens,
            "asks": self.asks,
            "blind_spots": self.blind_spots,
            "weight": self.weight,
            "adversarial": self.adversarial,
            "domains": [d.value for d in self.domains],
            "metadata": self.metadata,
        }


_ALL_PROFILES: list[ThinkerProfile] = [
    ThinkerProfile(
        archetype=ThinkerArchetype.CONTRARIAN,
        name="Contrarian Thinker",
        lens="What if the opposite of the majority position is correct?",
        asks=[
            "What evidence would falsify the consensus?",
            "Is groupthink suppressing a valid alternative?",
        ],
        blind_spots=["May oppose for opposition's sake"],
        weight=0.9,
        adversarial=True,
        domains=[DeliberationDomain.CROSS_DOMAIN],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.SKEPTIC,
        name="Skeptic",
        lens="What is actually proven vs. assumed?",
        asks=["Where is the hard evidence?", "What assumptions remain untested?"],
        blind_spots=["May paralyze action by demanding impossible certainty"],
        weight=1.0,
        adversarial=True,
        domains=[DeliberationDomain.CROSS_DOMAIN],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.RED_TEAM,
        name="Red Team Attacker",
        lens="How would an adversary exploit this plan?",
        asks=["What are the attack surfaces?", "Where does this fail under hostile conditions?"],
        blind_spots=["May over-index on threat scenarios that are unlikely"],
        weight=1.1,
        adversarial=True,
        domains=[DeliberationDomain.SOFTWARE, DeliberationDomain.BUSINESS],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.BLUE_TEAM,
        name="Blue Team Defender",
        lens="How do we make this resilient, recoverable, and safe?",
        asks=["What is the recovery plan?", "What guardrails prevent catastrophic failure?"],
        blind_spots=["May over-engineer defenses that slow execution"],
        weight=1.1,
        adversarial=False,
        domains=[DeliberationDomain.SOFTWARE, DeliberationDomain.BUSINESS],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.FIRST_PRINCIPLES,
        name="First-Principles Decomposer",
        lens="Strip away assumptions — what is fundamentally true here?",
        asks=["What are the atomic facts?", "Which constraints are real vs. inherited?"],
        blind_spots=["May discard valid heuristics that save time"],
        weight=1.0,
        adversarial=False,
        domains=[DeliberationDomain.CROSS_DOMAIN],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.LEVERAGE_MAXIMIZER,
        name="Leverage Maximizer",
        lens="What is the highest-leverage action available?",
        asks=["What produces disproportionate return?", "What is the binding constraint?"],
        blind_spots=["May ignore necessary low-leverage hygiene work"],
        weight=1.2,
        adversarial=False,
        domains=[DeliberationDomain.BUSINESS, DeliberationDomain.CROSS_DOMAIN],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.FUTURE_BACKCASTER,
        name="Future Backcaster",
        lens="Working backward from the desired future state — what must be true now?",
        asks=[
            "What does success look like in 10 years?",
            "What irreversible decision must happen now?",
        ],
        blind_spots=["May optimize for distant future at the expense of survival today"],
        weight=1.0,
        adversarial=False,
        domains=[DeliberationDomain.BUSINESS, DeliberationDomain.CROSS_DOMAIN],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.OPERATOR,
        name="Operator",
        lens="Can this actually be executed with current resources and constraints?",
        asks=["Who does this?", "What is the daily/weekly cadence?", "What breaks first?"],
        blind_spots=["May reject ambitious plans as impractical too quickly"],
        weight=1.0,
        adversarial=False,
        domains=[DeliberationDomain.BUSINESS, DeliberationDomain.HUMAN],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.STRATEGIST,
        name="Strategist",
        lens="Market position, timing, competitive dynamics, resource allocation",
        asks=["What is the opportunity cost?", "Is the timing right?"],
        blind_spots=["May undervalue technical debt", "May overvalue short-term revenue"],
        weight=1.2,
        adversarial=False,
        domains=[DeliberationDomain.BUSINESS],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.TECHNICAL_ARCHITECT,
        name="Technical Architect",
        lens="Structural integrity, modularity, maintainability, scalability",
        asks=["Does this fit the architecture?", "What is the maintenance cost?"],
        blind_spots=["May over-engineer simple problems"],
        weight=1.0,
        adversarial=False,
        domains=[DeliberationDomain.SOFTWARE, DeliberationDomain.UMH_INTERNAL],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.FINANCIAL_ANALYST,
        name="Financial Analyst",
        lens="Cost, revenue impact, unit economics, ROI, cash flow",
        asks=[
            "What does this cost?",
            "What is the payback period?",
            "Does this improve unit economics?",
        ],
        blind_spots=["May reduce strategic bets to spreadsheet logic"],
        weight=1.0,
        adversarial=False,
        domains=[DeliberationDomain.BUSINESS],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.LEGAL_REGULATORY,
        name="Legal / Regulatory Reviewer",
        lens="Compliance, liability, intellectual property, regulatory risk",
        asks=["Is this legal?", "What regulatory exposure exists?", "Are IP boundaries clear?"],
        blind_spots=["May block innovation with excessive caution"],
        weight=0.8,
        adversarial=False,
        domains=[DeliberationDomain.BUSINESS, DeliberationDomain.CROSS_DOMAIN],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.SECURITY_REVIEWER,
        name="Security Reviewer",
        lens="Attack surface, data exposure, credential handling, access control",
        asks=["What can be compromised?", "Are secrets safe?", "What is the blast radius?"],
        blind_spots=["May impose friction that degrades usability"],
        weight=1.0,
        adversarial=True,
        domains=[DeliberationDomain.SOFTWARE],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.CUSTOMER_ADVOCATE,
        name="Customer Advocate",
        lens="Does this serve the customer's real need and build trust?",
        asks=["What does the customer actually want?", "Does this create or erode trust?"],
        blind_spots=["May conflate vocal minority with majority"],
        weight=1.0,
        adversarial=False,
        domains=[DeliberationDomain.HUMAN, DeliberationDomain.BUSINESS],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.PRODUCT_REVIEWER,
        name="Product Reviewer",
        lens="Feature coherence, user journey, product-market fit, scope discipline",
        asks=["Does this ship?", "Does this solve a real problem?", "Is the scope right?"],
        blind_spots=["May ship too fast at the expense of quality"],
        weight=1.0,
        adversarial=False,
        domains=[DeliberationDomain.BUSINESS, DeliberationDomain.SOFTWARE],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.SYSTEMS_THINKER,
        name="Systems Thinker",
        lens="Feedback loops, second-order effects, emergent behavior, dependencies",
        asks=["What are the second-order effects?", "Where are the feedback loops?"],
        blind_spots=["May over-complicate with systems models that delay action"],
        weight=1.0,
        adversarial=False,
        domains=[DeliberationDomain.CROSS_DOMAIN],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.ONTOLOGY_LAW_REVIEWER,
        name="Ontology / Law Reviewer",
        lens="Alignment with universal laws, polarity synthesis, structural coherence",
        asks=["Does this violate any universal law?", "Are there unresolved polarities?"],
        blind_spots=["May over-abstract practical problems"],
        weight=0.8,
        adversarial=False,
        domains=[DeliberationDomain.UMH_INTERNAL],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.MEMORY_HISTORIAN,
        name="Memory Historian",
        lens="What has been tried before? What context is being lost or repeated?",
        asks=[
            "Has this been attempted?",
            "What did we learn last time?",
            "What context is missing?",
        ],
        blind_spots=["May anchor too heavily on past failures"],
        weight=0.9,
        adversarial=False,
        domains=[DeliberationDomain.CROSS_DOMAIN],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.QUALITY_JUDGE,
        name="Quality Judge",
        lens="Does this meet the quality bar? Is it complete, tested, verified?",
        asks=["Is this verified?", "What tests exist?", "What edge cases are uncovered?"],
        blind_spots=["May delay shipping with perfectionism"],
        weight=1.0,
        adversarial=False,
        domains=[DeliberationDomain.SOFTWARE, DeliberationDomain.CROSS_DOMAIN],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.EVIDENCE_JUDGE,
        name="Evidence Judge",
        lens="Is the evidence sufficient, relevant, and correctly interpreted?",
        asks=[
            "Is this correlation or causation?",
            "Is the sample size meaningful?",
            "What is the confidence interval?",
        ],
        blind_spots=["May reject valid intuition that lacks formal evidence"],
        weight=1.0,
        adversarial=True,
        domains=[DeliberationDomain.CROSS_DOMAIN],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.BRAND_STRATEGIST,
        name="Brand Strategist",
        lens="Brand coherence, positioning, perception, trust, differentiation",
        asks=["Does this strengthen or dilute the brand?", "Is this on-message?"],
        blind_spots=["May over-index on brand consistency at expense of speed"],
        weight=0.9,
        adversarial=False,
        domains=[DeliberationDomain.CONTENT, DeliberationDomain.BUSINESS],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.GROWTH_DISTRIBUTION,
        name="Growth / Distribution Strategist",
        lens="Channels, virality, CAC, distribution leverage, audience building",
        asks=["How does this reach people?", "What is the distribution advantage?"],
        blind_spots=["May prioritize growth over product quality"],
        weight=1.0,
        adversarial=False,
        domains=[DeliberationDomain.BUSINESS, DeliberationDomain.CONTENT],
    ),
    ThinkerProfile(
        archetype=ThinkerArchetype.HUMAN_FACTOR_REVIEWER,
        name="Human Factor Reviewer",
        lens="Cognitive load, emotional impact, human limitations, ergonomics",
        asks=["Can a human actually sustain this?", "What is the cognitive load?"],
        blind_spots=["May under-estimate human adaptability"],
        weight=0.9,
        adversarial=False,
        domains=[DeliberationDomain.HUMAN, DeliberationDomain.CROSS_DOMAIN],
    ),
]


def get_all_thinker_profiles() -> list[ThinkerProfile]:
    """Return all 23 thinker archetype profiles."""
    return list(_ALL_PROFILES)


def get_adversarial_profiles() -> list[ThinkerProfile]:
    """Return only adversarial archetypes (contrarian, skeptic, red team, security, evidence judge)."""
    return [p for p in _ALL_PROFILES if p.adversarial]


def get_profiles_for_domain(domain: DeliberationDomain) -> list[ThinkerProfile]:
    """Return profiles relevant to a specific domain (includes cross-domain)."""
    return [
        p
        for p in _ALL_PROFILES
        if domain in p.domains or DeliberationDomain.CROSS_DOMAIN in p.domains
    ]


def assign_archetypes_for_request(
    domain: DeliberationDomain,
    urgency: UrgencyLevel = UrgencyLevel.MEDIUM,
    *,
    include_adversarial: bool = True,
    max_archetypes: int = 12,
) -> list[ThinkerProfile]:
    """Select thinker archetypes appropriate for a request.

    Always includes at least one adversarial thinker if include_adversarial is True.
    Higher urgency = fewer thinkers (faster deliberation).
    """
    domain_profiles = get_profiles_for_domain(domain)

    if urgency == UrgencyLevel.CRITICAL:
        cap = min(max_archetypes, 6)
    elif urgency == UrgencyLevel.HIGH:
        cap = min(max_archetypes, 8)
    else:
        cap = max_archetypes

    adversarial = [p for p in domain_profiles if p.adversarial]
    non_adversarial = [p for p in domain_profiles if not p.adversarial]

    selected: list[ThinkerProfile] = []

    if include_adversarial and adversarial:
        selected.append(adversarial[0])
        adversarial = adversarial[1:]

    remaining_slots = cap - len(selected)

    combined = sorted(non_adversarial + adversarial, key=lambda p: p.weight, reverse=True)
    selected.extend(combined[:remaining_slots])

    return selected


def generate_stub_thinker_report(
    request_id: str,
    profile: ThinkerProfile,
    question: str,
) -> PerspectiveReport:
    """Generate a deterministic stub perspective from a thinker archetype.

    No LLM calls. Uses archetype lens and asks to construct a template report.
    """
    position = f"[{profile.name}] Analysis of: {question[:100]}"
    reasoning = f"Applying {profile.lens.lower()} to evaluate the question."
    recommendation = (
        f"Ensure {profile.asks[0].lower()}" if profile.asks else "Further analysis required."
    )

    evidence = [
        EvidenceItem(
            evidence_id=_council_id("ev"),
            claim=f"Stub evidence from {profile.name} lens",
            strength=EvidenceStrength.WEAK,
            source=f"archetype:{profile.archetype.value}",
            confidence=0.3,
        )
    ]

    assumptions = [
        Assumption(
            assumption_id=_council_id("asm"),
            statement=f"Assumes {profile.lens.lower()} is relevant to this question",
            basis="Archetype assignment",
            risk_if_wrong=f"Analysis from {profile.name} may be misapplied",
            confidence=0.5,
        )
    ]

    risks = [f"Blind spot: {bs}" for bs in profile.blind_spots]

    base_score = 0.5
    if profile.adversarial:
        base_score = 0.4

    return create_perspective_report(
        request_id,
        f"archetype:{profile.archetype.value}",
        position=position,
        reasoning=reasoning,
        recommendation=recommendation,
        evidence=evidence,
        assumptions=assumptions,
        risks_identified=risks,
        confidence=ConfidenceLevel.LOW,
        score=clamp_score(base_score),
        metadata={"archetype": profile.archetype.value, "adversarial": profile.adversarial},
    )
