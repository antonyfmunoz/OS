"""Phase 87 leverage taxonomy — typed taxonomy of all leverage categories.

Each LeverageTaxonomyNode describes what the leverage type is, when to use it,
when it fails, and what resources/tools relate to it. The taxonomy is the
foundation for scoring and recommendation logic.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.leverage.contracts import (
    LeverageType,
    ResourceProfile,
    ResourceType,
    ToolProfile,
    ToolType,
    _lev_id,
)


@dataclass
class LeverageTaxonomyNode:
    node_id: str = ""
    leverage_type: LeverageType = LeverageType.UNKNOWN
    name: str = ""
    description: str = ""
    examples: list[str] = field(default_factory=list)
    best_for: list[str] = field(default_factory=list)
    weak_when: list[str] = field(default_factory=list)
    common_failure_modes: list[str] = field(default_factory=list)
    related_resource_types: list[ResourceType] = field(default_factory=list)
    related_tool_types: list[ToolType] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "leverage_type": self.leverage_type.value,
            "name": self.name,
            "description": self.description,
            "examples": self.examples,
            "best_for": self.best_for,
            "weak_when": self.weak_when,
            "common_failure_modes": self.common_failure_modes,
            "related_resource_types": [r.value for r in self.related_resource_types],
            "related_tool_types": [t.value for t in self.related_tool_types],
            "metadata": self.metadata,
        }


def _node(
    lt: LeverageType,
    name: str,
    description: str,
    examples: list[str],
    best_for: list[str],
    weak_when: list[str],
    failure_modes: list[str],
    resource_types: list[ResourceType],
    tool_types: list[ToolType],
) -> LeverageTaxonomyNode:
    return LeverageTaxonomyNode(
        node_id=_lev_id("taxn"),
        leverage_type=lt,
        name=name,
        description=description,
        examples=examples,
        best_for=best_for,
        weak_when=weak_when,
        common_failure_modes=failure_modes,
        related_resource_types=resource_types,
        related_tool_types=tool_types,
    )


_DEFAULT_TAXONOMY: list[LeverageTaxonomyNode] | None = None


def build_default_leverage_taxonomy() -> list[LeverageTaxonomyNode]:
    global _DEFAULT_TAXONOMY
    if _DEFAULT_TAXONOMY is not None:
        return list(_DEFAULT_TAXONOMY)

    nodes = [
        _node(
            LeverageType.HUMAN,
            "Human Leverage",
            "Other people's time, skill, expertise, labor, judgment",
            ["hiring a VA", "delegating content editing", "advisory board"],
            ["tasks requiring diverse skill sets", "scaling beyond founder hours"],
            ["trust not established", "unclear task definition", "misaligned incentives"],
            ["poor delegation", "unclear outcomes", "misaligned incentives", "micromanagement"],
            [ResourceType.HUMAN, ResourceType.NETWORK],
            [ToolType.HUMAN_EXPERT],
        ),
        _node(
            LeverageType.CODE_SOFTWARE,
            "Code / Software Leverage",
            "Scalable execution through software — build once, deploy infinitely",
            ["UMH codebase", "SaaS products", "automation scripts", "APIs"],
            ["repeated tasks", "data processing", "scalable delivery"],
            ["process not yet understood", "one-time tasks", "high ambiguity"],
            ["building before process clarity", "premature optimization", "technical debt"],
            [ResourceType.CODE, ResourceType.DATA],
            [ToolType.SOFTWARE, ToolType.API],
        ),
        _node(
            LeverageType.CONTENT_MEDIA,
            "Content / Media Leverage",
            "One-to-many attention and trust through content",
            ["Instagram reels", "YouTube videos", "blog posts", "carousels", "podcasts"],
            ["building audience", "establishing authority", "lead generation"],
            ["no distribution", "no conversion strategy", "audience mismatch"],
            ["content without conversion", "no strategy", "inconsistency", "vanity metrics"],
            [ResourceType.MEDIA_ASSET, ResourceType.AUDIENCE],
            [ToolType.SOCIAL_PLATFORM, ToolType.MEDIA_CHANNEL],
        ),
        _node(
            LeverageType.CAPITAL,
            "Capital Leverage",
            "Money as force multiplier — buy time, talent, tools, distribution",
            ["hiring", "ads spend", "equipment purchase", "software subscriptions"],
            ["validated systems needing scale", "buying speed", "acquiring assets"],
            ["system not validated", "no ROI tracking", "burning cash pre-product-market-fit"],
            ["deploying capital before validated system", "no measurement", "lifestyle creep"],
            [ResourceType.MONEY],
            [ToolType.CAPITAL_INSTRUMENT],
        ),
        _node(
            LeverageType.SYSTEMS_PROCESS,
            "Systems / Process Leverage",
            "Repeatable workflows, SOPs, templates — predictability at scale",
            ["content production SOP", "sales call script", "onboarding checklist"],
            ["repeated workflows", "quality consistency", "delegation prep"],
            ["one-time tasks", "highly creative work", "early exploration"],
            ["bureaucratic bloat", "process for process sake", "rigidity"],
            [ResourceType.PROCESS, ResourceType.TEMPLATE],
            [ToolType.TEMPLATE, ToolType.WORKFLOW],
        ),
        _node(
            LeverageType.AI_MODEL,
            "AI / Model Leverage",
            "Cognition and computation leverage — amplify thinking and execution",
            ["Claude Code for development", "ChatGPT for research", "Gemini for analysis"],
            ["reasoning", "code generation", "content drafting", "analysis", "summarization"],
            ["high-stakes judgment", "physical tasks", "relationship building"],
            ["hallucination", "missing context", "ungated execution", "over-reliance"],
            [ResourceType.AI_MODEL],
            [ToolType.AI_MODEL, ToolType.COMPUTER_USE],
        ),
        _node(
            LeverageType.NETWORK_RELATIONSHIP,
            "Network / Relationship Leverage",
            "Access to people, opportunities, and distribution through relationships",
            ["mentors", "joint ventures", "referral partnerships", "community"],
            ["deal flow", "warm introductions", "trust transfer", "distribution"],
            ["no reciprocity", "transactional approach", "no follow-up"],
            ["weak trust", "poor follow-up", "taking without giving", "wrong network"],
            [ResourceType.NETWORK, ResourceType.HUMAN],
            [ToolType.HUMAN_EXPERT, ToolType.SOCIAL_PLATFORM],
        ),
        _node(
            LeverageType.ATTENTION_FOCUS,
            "Attention / Focus Leverage",
            "The user's highest-value resource — concentrated attention on highest-leverage work",
            ["deep work blocks", "priority ruthlessness", "saying no"],
            ["strategic thinking", "creative work", "high-trust selling"],
            ["fragmented across too many things", "reactive mode", "low-value tasks"],
            ["fragmentation", "context switching", "busy but unproductive", "distraction"],
            [ResourceType.ATTENTION, ResourceType.TIME, ResourceType.ENERGY],
            [],
        ),
        _node(
            LeverageType.DATA,
            "Data Leverage",
            "Accumulated evidence, feedback, and metrics that improve decisions",
            ["KPI dashboards", "customer feedback", "A/B test results", "execution traces"],
            ["optimization", "pattern detection", "evidence-based decisions"],
            ["insufficient data", "dirty data", "analysis paralysis"],
            ["dirty data", "stale data", "unstructured data", "vanity metrics"],
            [ResourceType.DATA, ResourceType.KNOWLEDGE_ASSET],
            [ToolType.SOFTWARE, ToolType.API],
        ),
        _node(
            LeverageType.DISTRIBUTION,
            "Distribution Leverage",
            "Ability to reach your market repeatedly and predictably",
            ["email list", "social following", "SEO rankings", "partnerships"],
            ["launch amplification", "consistent lead flow", "audience monetization"],
            ["audience mismatch", "single-channel dependency", "no conversion"],
            ["audience mismatch", "platform dependency", "reach without conversion"],
            [ResourceType.AUDIENCE, ResourceType.PLATFORM],
            [ToolType.SOCIAL_PLATFORM, ToolType.MEDIA_CHANNEL],
        ),
        _node(
            LeverageType.BRAND,
            "Brand Leverage",
            "Trust, meaning, status, and identity that compounds over time",
            ["personal brand", "Lyfe Institute brand", "Empyrean Studio positioning"],
            ["premium pricing", "trust transfer", "talent attraction", "partnerships"],
            ["new market", "inconsistent messaging", "no proof"],
            ["inconsistency", "overextension", "promise-delivery gap", "dilution"],
            [ResourceType.BRAND, ResourceType.AUDIENCE],
            [ToolType.SOCIAL_PLATFORM, ToolType.MEDIA_CHANNEL],
        ),
        _node(
            LeverageType.PHYSICAL_INFRASTRUCTURE,
            "Physical Infrastructure Leverage",
            "Owned physical capacity — studios, offices, servers, warehouses",
            ["VPS servers", "recording studio", "office space"],
            ["operations requiring physical presence", "controlled environments"],
            ["capital constrained", "early stage", "remote-first"],
            ["capital intensity too early", "maintenance burden", "location lock-in"],
            [ResourceType.REAL_ESTATE, ResourceType.EQUIPMENT],
            [ToolType.PHYSICAL_ASSET],
        ),
        _node(
            LeverageType.ROBOTICS_AUTOMATION,
            "Robotics / Automation Leverage",
            "Physical actuation leverage — machines doing physical work",
            ["3D printing", "CNC machining", "warehouse robotics", "manufacturing automation"],
            ["repetitive physical tasks", "precision manufacturing", "scale production"],
            ["low volume", "high variety", "early prototyping"],
            ["premature complexity", "maintenance costs", "integration difficulty"],
            [ResourceType.ROBOTICS, ResourceType.EQUIPMENT],
            [ToolType.ROBOTIC_SYSTEM, ToolType.PHYSICAL_ASSET],
        ),
        _node(
            LeverageType.REAL_ESTATE,
            "Real Estate Leverage",
            "Asset, cash-flow, and location leverage through property",
            ["rental income", "studio space", "commercial property"],
            ["passive income", "asset appreciation", "business operations"],
            ["capital constrained", "market downturn", "illiquidity needed"],
            ["illiquidity", "debt risk", "management overhead", "market timing"],
            [ResourceType.REAL_ESTATE, ResourceType.MONEY],
            [ToolType.CAPITAL_INSTRUMENT],
        ),
        _node(
            LeverageType.MANUFACTURING,
            "Manufacturing Leverage",
            "Production ownership — control quality, cost, and supply chain",
            ["private label products", "custom merchandise", "physical goods"],
            ["product-market fit proven", "volume economics", "quality control"],
            ["unproven demand", "low volume", "high capital requirements"],
            ["quality issues", "capex overrun", "supply chain complexity", "inventory risk"],
            [ResourceType.MANUFACTURING, ResourceType.EQUIPMENT],
            [ToolType.PHYSICAL_ASSET, ToolType.ROBOTIC_SYSTEM],
        ),
        _node(
            LeverageType.FULFILLMENT,
            "Fulfillment Leverage",
            "Delivery and logistics leverage — getting products to customers",
            ["shipping", "digital delivery", "course access", "onboarding"],
            ["proven product", "recurring delivery", "customer retention"],
            ["unproven product", "one-off delivery", "no repeat customers"],
            ["operational overhead", "customer service burden", "scaling bottlenecks"],
            [ResourceType.FULFILLMENT, ResourceType.PROCESS],
            [ToolType.WORKFLOW, ToolType.SOFTWARE],
        ),
        _node(
            LeverageType.REGULATORY,
            "Regulatory Leverage",
            "Compliance, licensing, and regulatory moats",
            ["business licenses", "certifications", "IP protection", "trademarks"],
            ["defensibility", "market access", "trust signaling"],
            ["early stage", "moving fast", "testing market"],
            ["compliance overhead", "regulatory capture", "slow adaptation"],
            [ResourceType.KNOWLEDGE_ASSET],
            [ToolType.DOCUMENT],
        ),
        _node(
            LeverageType.TIME,
            "Time Leverage",
            "Compounding advantage from starting early and staying consistent",
            ["compound content library", "skill development", "relationship building"],
            ["long-term positioning", "compounding returns", "moat building"],
            ["urgent short-term needs", "pivoting frequently"],
            ["impatience", "premature optimization", "not starting"],
            [ResourceType.TIME],
            [],
        ),
        _node(
            LeverageType.ENERGY,
            "Energy Leverage",
            "Physical and mental energy deployed at peak effectiveness",
            ["deep work mornings", "exercise for cognitive boost", "sleep optimization"],
            ["high-quality output", "creative work", "strategic decisions"],
            ["depleted state", "burnout risk", "chronic stress"],
            ["ignoring recovery", "overcommitment", "poor health habits"],
            [ResourceType.ENERGY],
            [],
        ),
        _node(
            LeverageType.KNOWLEDGE,
            "Knowledge Leverage",
            "Accumulated expertise, frameworks, and understanding",
            ["domain expertise", "technical skills", "market knowledge", "curriculum"],
            ["teaching", "consulting", "product creation", "decision quality"],
            ["rapidly changing field", "knowledge hoarding", "theory without practice"],
            ["outdated knowledge", "ivory tower", "not sharing", "not applying"],
            [ResourceType.KNOWLEDGE_ASSET],
            [ToolType.DOCUMENT, ToolType.COURSE_CONTENT],
        ),
    ]

    _DEFAULT_TAXONOMY = nodes
    return list(nodes)


def get_taxonomy_node(leverage_type: LeverageType) -> LeverageTaxonomyNode | None:
    for node in build_default_leverage_taxonomy():
        if node.leverage_type == leverage_type:
            return node
    return None


def explain_leverage_type(leverage_type: LeverageType) -> str:
    node = get_taxonomy_node(leverage_type)
    if node is None:
        return f"Unknown leverage type: {leverage_type.value}"
    return f"{node.name}: {node.description}"


_RESOURCE_TO_LEVERAGE: dict[ResourceType, LeverageType] = {
    ResourceType.HUMAN: LeverageType.HUMAN,
    ResourceType.MONEY: LeverageType.CAPITAL,
    ResourceType.TIME: LeverageType.TIME,
    ResourceType.ENERGY: LeverageType.ENERGY,
    ResourceType.ATTENTION: LeverageType.ATTENTION_FOCUS,
    ResourceType.DATA: LeverageType.DATA,
    ResourceType.CODE: LeverageType.CODE_SOFTWARE,
    ResourceType.TOOL: LeverageType.CODE_SOFTWARE,
    ResourceType.PLATFORM: LeverageType.DISTRIBUTION,
    ResourceType.AUDIENCE: LeverageType.DISTRIBUTION,
    ResourceType.NETWORK: LeverageType.NETWORK_RELATIONSHIP,
    ResourceType.BRAND: LeverageType.BRAND,
    ResourceType.PROCESS: LeverageType.SYSTEMS_PROCESS,
    ResourceType.TEMPLATE: LeverageType.SYSTEMS_PROCESS,
    ResourceType.LIBRARY: LeverageType.KNOWLEDGE,
    ResourceType.AI_MODEL: LeverageType.AI_MODEL,
    ResourceType.REAL_ESTATE: LeverageType.REAL_ESTATE,
    ResourceType.EQUIPMENT: LeverageType.PHYSICAL_INFRASTRUCTURE,
    ResourceType.MANUFACTURING: LeverageType.MANUFACTURING,
    ResourceType.FULFILLMENT: LeverageType.FULFILLMENT,
    ResourceType.ROBOTICS: LeverageType.ROBOTICS_AUTOMATION,
    ResourceType.MEDIA_ASSET: LeverageType.CONTENT_MEDIA,
    ResourceType.KNOWLEDGE_ASSET: LeverageType.KNOWLEDGE,
}

_TOOL_TO_LEVERAGE: dict[ToolType, LeverageType] = {
    ToolType.SOFTWARE: LeverageType.CODE_SOFTWARE,
    ToolType.AI_MODEL: LeverageType.AI_MODEL,
    ToolType.HUMAN_EXPERT: LeverageType.HUMAN,
    ToolType.TEMPLATE: LeverageType.SYSTEMS_PROCESS,
    ToolType.WORKFLOW: LeverageType.SYSTEMS_PROCESS,
    ToolType.CAPITAL_INSTRUMENT: LeverageType.CAPITAL,
    ToolType.MEDIA_CHANNEL: LeverageType.CONTENT_MEDIA,
    ToolType.PHYSICAL_ASSET: LeverageType.PHYSICAL_INFRASTRUCTURE,
    ToolType.ROBOTIC_SYSTEM: LeverageType.ROBOTICS_AUTOMATION,
    ToolType.API: LeverageType.CODE_SOFTWARE,
    ToolType.COMPUTER_USE: LeverageType.AI_MODEL,
    ToolType.MANUAL_PROCESS: LeverageType.HUMAN,
    ToolType.DOCUMENT: LeverageType.KNOWLEDGE,
    ToolType.COURSE_CONTENT: LeverageType.KNOWLEDGE,
    ToolType.SOCIAL_PLATFORM: LeverageType.DISTRIBUTION,
}


def map_resource_to_leverage(resource: ResourceProfile) -> LeverageType:
    return _RESOURCE_TO_LEVERAGE.get(resource.resource_type, LeverageType.UNKNOWN)


def map_tool_to_leverage(tool: ToolProfile) -> LeverageType:
    return _TOOL_TO_LEVERAGE.get(tool.tool_type, LeverageType.UNKNOWN)


def taxonomy_node_to_dict(node: LeverageTaxonomyNode) -> dict[str, Any]:
    return node.to_dict()
