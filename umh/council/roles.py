"""Phase 85 council roles — typed specialist definitions for deliberation.

Each role has a domain, perspective lens, evaluation criteria,
and known blind spots. Roles are advisory labels, not execution agents.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.council.contracts import DeliberationDomain, _council_id, normalize_deliberation_domain


class CouncilRoleType(str, Enum):
    CHAIR = "chair"
    STRATEGIST = "strategist"
    ENGINEER = "engineer"
    RISK_ANALYST = "risk_analyst"
    USER_ADVOCATE = "user_advocate"
    ONTOLOGY_SPECIALIST = "ontology_specialist"
    DOMAIN_EXPERT = "domain_expert"
    UNKNOWN = "unknown"


def normalize_council_role_type(value: str) -> CouncilRoleType:
    v = value.strip().lower().replace(" ", "_").replace("-", "_")
    for m in CouncilRoleType:
        if m.value == v:
            return m
    return CouncilRoleType.UNKNOWN


@dataclass
class CouncilRole:
    role_id: str = ""
    role_type: CouncilRoleType = CouncilRoleType.UNKNOWN
    name: str = ""
    domain: DeliberationDomain = DeliberationDomain.CROSS_DOMAIN
    perspective_lens: str = ""
    evaluation_criteria: list[str] = field(default_factory=list)
    known_blind_spots: list[str] = field(default_factory=list)
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "role_type": self.role_type.value,
            "name": self.name,
            "domain": self.domain.value,
            "perspective_lens": self.perspective_lens,
            "evaluation_criteria": self.evaluation_criteria,
            "known_blind_spots": self.known_blind_spots,
            "weight": self.weight,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CouncilRole:
        return cls(
            role_id=data.get("role_id", _council_id("role")),
            role_type=normalize_council_role_type(data.get("role_type", "unknown")),
            name=data.get("name", ""),
            domain=normalize_deliberation_domain(data.get("domain", "cross_domain")),
            perspective_lens=data.get("perspective_lens", ""),
            evaluation_criteria=data.get("evaluation_criteria", []),
            known_blind_spots=data.get("known_blind_spots", []),
            weight=max(0.0, min(5.0, float(data.get("weight", 1.0)))),
            metadata=data.get("metadata", {}),
        )


def get_default_council_roles() -> list[CouncilRole]:
    return [
        CouncilRole(
            role_id="role_chair",
            role_type=CouncilRoleType.CHAIR,
            name="Deliberation Chair",
            domain=DeliberationDomain.CROSS_DOMAIN,
            perspective_lens="Integration and synthesis across all perspectives",
            evaluation_criteria=[
                "Are all relevant perspectives represented?",
                "Is the synthesis coherent and actionable?",
                "Have disagreements been made explicit?",
            ],
            known_blind_spots=["May over-weight consensus over truth"],
            weight=1.5,
        ),
        CouncilRole(
            role_id="role_strategist",
            role_type=CouncilRoleType.STRATEGIST,
            name="Business Strategist",
            domain=DeliberationDomain.BUSINESS,
            perspective_lens="Revenue, market position, resource allocation, timing",
            evaluation_criteria=[
                "Does this move the needle on the primary metric?",
                "What is the opportunity cost?",
                "Is the timing right given current constraints?",
            ],
            known_blind_spots=[
                "May undervalue technical debt",
                "May overvalue short-term revenue",
            ],
            weight=1.2,
        ),
        CouncilRole(
            role_id="role_engineer",
            role_type=CouncilRoleType.ENGINEER,
            name="Technical Engineer",
            domain=DeliberationDomain.SOFTWARE,
            perspective_lens="Feasibility, architecture, maintainability, performance",
            evaluation_criteria=[
                "Is this technically sound?",
                "What are the maintenance implications?",
                "Does it fit the existing architecture?",
            ],
            known_blind_spots=[
                "May over-engineer simple problems",
                "May undervalue business urgency",
            ],
            weight=1.0,
        ),
        CouncilRole(
            role_id="role_risk",
            role_type=CouncilRoleType.RISK_ANALYST,
            name="Risk Analyst",
            domain=DeliberationDomain.CROSS_DOMAIN,
            perspective_lens="Failure modes, reversibility, blast radius, dependencies",
            evaluation_criteria=[
                "What could go wrong?",
                "Is this reversible?",
                "What is the blast radius of failure?",
            ],
            known_blind_spots=[
                "May produce analysis paralysis",
                "May undervalue upside of bold action",
            ],
            weight=1.0,
        ),
        CouncilRole(
            role_id="role_user_advocate",
            role_type=CouncilRoleType.USER_ADVOCATE,
            name="User Advocate",
            domain=DeliberationDomain.HUMAN,
            perspective_lens="User experience, accessibility, trust, friction",
            evaluation_criteria=[
                "Does this serve the user's actual need?",
                "Is the experience intuitive?",
                "Does this build or erode trust?",
            ],
            known_blind_spots=[
                "May resist necessary complexity",
                "May conflate vocal minority with majority",
            ],
            weight=1.0,
        ),
        CouncilRole(
            role_id="role_ontology",
            role_type=CouncilRoleType.ONTOLOGY_SPECIALIST,
            name="Ontology Specialist",
            domain=DeliberationDomain.UMH_INTERNAL,
            perspective_lens="Universal laws, polarity synthesis, structural coherence",
            evaluation_criteria=[
                "Does this align with universal laws?",
                "Are there polar tensions that need synthesis?",
                "Is the ontological framing consistent?",
            ],
            known_blind_spots=[
                "May over-abstract practical problems",
                "May prioritize structural elegance over pragmatic value",
            ],
            weight=0.8,
        ),
    ]
