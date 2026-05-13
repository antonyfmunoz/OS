"""Business domain bridge — structural mapping from ontology to business primitives.

V1: keyword-based structural rules only. No LLM dependency.
Maps ontology observations to business primitive IDs from
runtime/primitives.py PRIMITIVE_LIBRARY.

V2 TODO: LLM-based semantic disambiguation for ambiguous cases
(e.g., "scale" could be growth, hiring, or infrastructure).
"""

from __future__ import annotations

from core.ontology.primitive_decomposition_v1 import PrimitiveObservation
from runtime.domain_bridge.contract import DomainProjection, make_projection_id
from runtime.domain_bridge.registry import default_registry


_DOMAIN_KEYWORD_MAP: dict[str, dict[str, list[str]]] = {
    "sales": {
        "offer_optimization": [
            "offer",
            "value prop",
            "value proposition",
            "irresistible",
            "price objection",
            "stack value",
        ],
        "outreach_before_content": [
            "outreach",
            "direct message",
            "cold email",
            "cold dm",
            "dm the",
            "prospect",
            "warm network",
        ],
        "pricing_psychology": [
            "pricing",
            "price signal",
            "charge what",
            "anchor",
            "penetration pricing",
            "value-based pricing",
        ],
    },
    "hiring": {
        "hire_salesperson": [
            "salesperson",
            "hire salesperson",
            "hiring a salesperson",
            "sales hire",
            "dedicated salesperson",
            "sales rep",
            "sales team",
        ],
        "hire_top_down": [
            "hire vp",
            "vp first",
            "a-player",
            "top-down hiring",
        ],
        "hire_bottom_up": [
            "replace yourself",
            "first hire",
            "hire to replace",
            "bottleneck hire",
            "lowest leverage",
        ],
        "_domain_generic": [
            "hire",
            "hiring",
            "recruit",
            "team building",
            "onboard",
            "staffing",
        ],
    },
    "marketing": {
        "paid_advertising": [
            "paid ads",
            "paid advertising",
            "paid acquisition",
            "ad spend",
            "cac",
            "cost per acquisition",
            "roas",
            "facebook ads",
            "google ads",
            "meta ads",
        ],
        "content_strategy": [
            "content strategy",
            "content marketing",
            "audience building",
            "content calendar",
            "followers",
            "brand content",
        ],
        "_domain_generic": [
            "marketing",
            "advertising",
            "campaign",
            "funnel",
            "lead magnet",
            "landing page",
        ],
    },
    "finance": {
        "unit_economics": [
            "unit economics",
            "cac",
            "ltv",
            "payback period",
            "cost per",
            "customer acquisition cost",
            "lifetime value",
        ],
        "cash_flow_management": [
            "cash flow",
            "runway",
            "burn rate",
            "revenue",
            "profit margin",
            "break even",
            "cash position",
        ],
        "_domain_generic": [
            "finance",
            "financial",
            "budget",
            "expense",
            "income",
            "bookkeeping",
        ],
    },
    "growth": {
        "retention_over_acquisition": [
            "retention",
            "churn",
            "customer retention",
            "nps",
            "reduce churn",
            "keep customer",
            "loyalty",
        ],
        "referral_flywheel": [
            "referral",
            "word of mouth",
            "refer a friend",
            "referral program",
            "advocacy",
        ],
        "_domain_generic": [
            "growth",
            "scale",
            "expand",
            "traction",
        ],
    },
    "validation": {
        "conversation_first": [
            "conversation",
            "customer discovery",
            "icp",
            "ideal customer",
            "validate",
            "mom test",
            "problem interview",
            "customer development",
        ],
    },
}

_BRIDGEABLE_ONTOLOGY_TYPES = frozenset(
    [
        "constraint",
        "action",
        "goal",
        "state",
        "resource",
    ]
)


class BusinessBridge:
    """Structural keyword bridge from ontology observations to business primitives."""

    @property
    def domain_id(self) -> str:
        return "business"

    def describes(self) -> str:
        return (
            "Maps ontology observations to business domain primitives "
            "(sales, hiring, marketing, finance, growth, validation) "
            "using structural keyword matching."
        )

    def bridge(self, observation: PrimitiveObservation) -> DomainProjection | None:
        if observation.primitive_type.value not in _BRIDGEABLE_ONTOLOGY_TYPES:
            return None

        text = f"{observation.label} {observation.description}".lower()

        best_domain: str | None = None
        best_primitive: str | None = None
        best_score = 0

        for domain, primitives in _DOMAIN_KEYWORD_MAP.items():
            for prim_id, keywords in primitives.items():
                score = sum(1 for kw in keywords if kw in text)
                if score > best_score:
                    best_score = score
                    best_domain = domain
                    best_primitive = prim_id

        if best_score == 0 or best_domain is None:
            return None

        if best_primitive and best_primitive.startswith("_domain_"):
            best_primitive = None

        confidence = min(observation.confidence, 0.70 + (best_score * 0.05))

        return DomainProjection(
            projection_id=make_projection_id(),
            domain_id=self.domain_id,
            domain_primitive_type=best_primitive or f"domain:{best_domain}",
            label=f"[business:{best_domain}] {observation.label}"[:80],
            description=observation.description,
            properties={
                "source_ontology_type": observation.primitive_type.value,
                "business_domain": best_domain,
                "business_primitive_id": best_primitive,
                "keyword_match_score": best_score,
            },
            ontology_observation_ref=observation.observation_id,
            confidence=confidence,
            evidence=observation.evidence,
            authority_tier=observation.authority_tier,
        )


_business_bridge = BusinessBridge()
default_registry.register(_business_bridge)
