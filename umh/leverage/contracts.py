"""Phase 87 leverage contracts — enums, types, and base structures.

Defines the typed vocabulary for the Leverage + Resource / Tool Taxonomy:
leverage types, resource types, tool types, actions, time horizons,
risk levels, confidence, and the core dataclasses consumed by scoring,
recommendations, and views.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ─── Enums ──────────────────────────────────────────────────────────


class LeverageType(str, Enum):
    HUMAN = "human"
    CODE_SOFTWARE = "code_software"
    CONTENT_MEDIA = "content_media"
    CAPITAL = "capital"
    SYSTEMS_PROCESS = "systems_process"
    AI_MODEL = "ai_model"
    NETWORK_RELATIONSHIP = "network_relationship"
    ATTENTION_FOCUS = "attention_focus"
    DATA = "data"
    DISTRIBUTION = "distribution"
    BRAND = "brand"
    PHYSICAL_INFRASTRUCTURE = "physical_infrastructure"
    ROBOTICS_AUTOMATION = "robotics_automation"
    REGULATORY = "regulatory"
    TIME = "time"
    ENERGY = "energy"
    KNOWLEDGE = "knowledge"
    REAL_ESTATE = "real_estate"
    MANUFACTURING = "manufacturing"
    FULFILLMENT = "fulfillment"
    UNKNOWN = "unknown"


class ResourceType(str, Enum):
    HUMAN = "human"
    MONEY = "money"
    TIME = "time"
    ENERGY = "energy"
    ATTENTION = "attention"
    DATA = "data"
    CODE = "code"
    TOOL = "tool"
    PLATFORM = "platform"
    AUDIENCE = "audience"
    NETWORK = "network"
    BRAND = "brand"
    PROCESS = "process"
    TEMPLATE = "template"
    LIBRARY = "library"
    AI_MODEL = "ai_model"
    REAL_ESTATE = "real_estate"
    EQUIPMENT = "equipment"
    MANUFACTURING = "manufacturing"
    FULFILLMENT = "fulfillment"
    ROBOTICS = "robotics"
    MEDIA_ASSET = "media_asset"
    KNOWLEDGE_ASSET = "knowledge_asset"
    UNKNOWN = "unknown"


class ToolType(str, Enum):
    SOFTWARE = "software"
    AI_MODEL = "ai_model"
    HUMAN_EXPERT = "human_expert"
    TEMPLATE = "template"
    WORKFLOW = "workflow"
    CAPITAL_INSTRUMENT = "capital_instrument"
    MEDIA_CHANNEL = "media_channel"
    PHYSICAL_ASSET = "physical_asset"
    ROBOTIC_SYSTEM = "robotic_system"
    API = "api"
    COMPUTER_USE = "computer_use"
    MANUAL_PROCESS = "manual_process"
    DOCUMENT = "document"
    COURSE_CONTENT = "course_content"
    SOCIAL_PLATFORM = "social_platform"
    UNKNOWN = "unknown"


class LeverageAction(str, Enum):
    DO_SELF = "do_self"
    DELEGATE = "delegate"
    AUTOMATE = "automate"
    TEMPLATE = "template"
    HIRE = "hire"
    BUY = "buy"
    PARTNER = "partner"
    OUTSOURCE = "outsource"
    SYSTEMIZE = "systemize"
    ELIMINATE = "eliminate"
    DEFER = "defer"
    RESEARCH = "research"
    SIMULATE = "simulate"
    APPROVE_AND_EXECUTE_LATER = "approve_and_execute_later"
    UNKNOWN = "unknown"


class LeverageTimeHorizon(str, Enum):
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    THREE_YEAR = "three_year"
    TEN_YEAR = "ten_year"
    THIRTY_YEAR = "thirty_year"
    CENTURY = "century"
    UNKNOWN = "unknown"


class LeverageRiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class LeverageConfidence(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    UNKNOWN = "unknown"


# ─── Normalizers ────────────────────────────────────────────────────


def _normalize(enum_cls: type[Enum], value: str | Enum) -> Enum:
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(str(value).lower().strip())
    except (ValueError, KeyError):
        return enum_cls("unknown")


def normalize_leverage_type(v: str | LeverageType) -> LeverageType:
    return _normalize(LeverageType, v)  # type: ignore[return-value]


def normalize_resource_type(v: str | ResourceType) -> ResourceType:
    return _normalize(ResourceType, v)  # type: ignore[return-value]


def normalize_tool_type(v: str | ToolType) -> ToolType:
    return _normalize(ToolType, v)  # type: ignore[return-value]


def normalize_leverage_action(v: str | LeverageAction) -> LeverageAction:
    return _normalize(LeverageAction, v)  # type: ignore[return-value]


def normalize_time_horizon(v: str | LeverageTimeHorizon) -> LeverageTimeHorizon:
    return _normalize(LeverageTimeHorizon, v)  # type: ignore[return-value]


def normalize_risk_level(v: str | LeverageRiskLevel) -> LeverageRiskLevel:
    return _normalize(LeverageRiskLevel, v)  # type: ignore[return-value]


def normalize_confidence(v: str | LeverageConfidence) -> LeverageConfidence:
    return _normalize(LeverageConfidence, v)  # type: ignore[return-value]


# ─── Helpers ────────────────────────────────────────────────────────


def _lev_id(prefix: str = "lev") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def clamp_score(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


# ─── Dataclasses ────────────────────────────────────────────────────


@dataclass
class ResourceProfile:
    resource_id: str = ""
    name: str = ""
    resource_type: ResourceType = ResourceType.UNKNOWN
    description: str = ""
    availability: str = ""
    constraints: list[str] = field(default_factory=list)
    cost: str = ""
    owner: str = ""
    sensitivity: str = "normal"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "name": self.name,
            "resource_type": self.resource_type.value,
            "description": self.description,
            "availability": self.availability,
            "constraints": self.constraints,
            "cost": self.cost,
            "owner": self.owner,
            "sensitivity": self.sensitivity,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ResourceProfile:
        return cls(
            resource_id=d.get("resource_id", ""),
            name=d.get("name", ""),
            resource_type=normalize_resource_type(d.get("resource_type", "unknown")),
            description=d.get("description", ""),
            availability=d.get("availability", ""),
            constraints=d.get("constraints", []),
            cost=d.get("cost", ""),
            owner=d.get("owner", ""),
            sensitivity=d.get("sensitivity", "normal"),
            metadata=d.get("metadata", {}),
        )


@dataclass
class ToolProfile:
    tool_id: str = ""
    name: str = ""
    tool_type: ToolType = ToolType.UNKNOWN
    description: str = ""
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    cost: str = ""
    latency: str = ""
    reliability: str = ""
    authority_required: str = ""
    dependency_risk: str = "low"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "tool_type": self.tool_type.value,
            "description": self.description,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "cost": self.cost,
            "latency": self.latency,
            "reliability": self.reliability,
            "authority_required": self.authority_required,
            "dependency_risk": self.dependency_risk,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ToolProfile:
        return cls(
            tool_id=d.get("tool_id", ""),
            name=d.get("name", ""),
            tool_type=normalize_tool_type(d.get("tool_type", "unknown")),
            description=d.get("description", ""),
            inputs=d.get("inputs", []),
            outputs=d.get("outputs", []),
            cost=d.get("cost", ""),
            latency=d.get("latency", ""),
            reliability=d.get("reliability", ""),
            authority_required=d.get("authority_required", ""),
            dependency_risk=d.get("dependency_risk", "low"),
            metadata=d.get("metadata", {}),
        )


@dataclass
class LeverageOpportunity:
    opportunity_id: str = ""
    title: str = ""
    leverage_type: LeverageType = LeverageType.UNKNOWN
    description: str = ""
    target_goal: str = ""
    required_resources: list[str] = field(default_factory=list)
    applicable_tools: list[str] = field(default_factory=list)
    expected_multiplier: float = 1.0
    time_to_impact: str = ""
    cost: str = ""
    risk_level: LeverageRiskLevel = LeverageRiskLevel.UNKNOWN
    reversibility: str = "reversible"
    compounding_potential: float = 0.0
    strategic_alignment: float = 0.0
    attention_required: str = ""
    confidence: LeverageConfidence = LeverageConfidence.UNKNOWN
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "title": self.title,
            "leverage_type": self.leverage_type.value,
            "description": self.description,
            "target_goal": self.target_goal,
            "required_resources": self.required_resources,
            "applicable_tools": self.applicable_tools,
            "expected_multiplier": self.expected_multiplier,
            "time_to_impact": self.time_to_impact,
            "cost": self.cost,
            "risk_level": self.risk_level.value,
            "reversibility": self.reversibility,
            "compounding_potential": self.compounding_potential,
            "strategic_alignment": self.strategic_alignment,
            "attention_required": self.attention_required,
            "confidence": self.confidence.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LeverageOpportunity:
        return cls(
            opportunity_id=d.get("opportunity_id", ""),
            title=d.get("title", ""),
            leverage_type=normalize_leverage_type(d.get("leverage_type", "unknown")),
            description=d.get("description", ""),
            target_goal=d.get("target_goal", ""),
            required_resources=d.get("required_resources", []),
            applicable_tools=d.get("applicable_tools", []),
            expected_multiplier=d.get("expected_multiplier", 1.0),
            time_to_impact=d.get("time_to_impact", ""),
            cost=d.get("cost", ""),
            risk_level=normalize_risk_level(d.get("risk_level", "unknown")),
            reversibility=d.get("reversibility", "reversible"),
            compounding_potential=d.get("compounding_potential", 0.0),
            strategic_alignment=d.get("strategic_alignment", 0.0),
            attention_required=d.get("attention_required", ""),
            confidence=normalize_confidence(d.get("confidence", "unknown")),
            metadata=d.get("metadata", {}),
        )


@dataclass
class LeverageAssessment:
    assessment_id: str = ""
    context: str = ""
    goal: str = ""
    constraints: list[str] = field(default_factory=list)
    resources: list[ResourceProfile] = field(default_factory=list)
    tools: list[ToolProfile] = field(default_factory=list)
    opportunities: list[LeverageOpportunity] = field(default_factory=list)
    highest_leverage_opportunity: str = ""
    bottlenecks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "context": self.context,
            "goal": self.goal,
            "constraints": self.constraints,
            "resources": [r.to_dict() for r in self.resources],
            "tools": [t.to_dict() for t in self.tools],
            "opportunities": [o.to_dict() for o in self.opportunities],
            "highest_leverage_opportunity": self.highest_leverage_opportunity,
            "bottlenecks": self.bottlenecks,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


@dataclass
class LeverageRecommendation:
    recommendation_id: str = ""
    action: LeverageAction = LeverageAction.UNKNOWN
    summary: str = ""
    rationale: str = ""
    leverage_type: LeverageType = LeverageType.UNKNOWN
    expected_multiplier: float = 1.0
    required_resources: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    first_step: str = ""
    guardrails: list[str] = field(default_factory=list)
    non_actions: list[str] = field(default_factory=list)
    risk_level: LeverageRiskLevel = LeverageRiskLevel.UNKNOWN
    confidence: LeverageConfidence = LeverageConfidence.UNKNOWN
    time_horizon: LeverageTimeHorizon = LeverageTimeHorizon.UNKNOWN
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "action": self.action.value,
            "summary": self.summary,
            "rationale": self.rationale,
            "leverage_type": self.leverage_type.value,
            "expected_multiplier": self.expected_multiplier,
            "required_resources": self.required_resources,
            "required_tools": self.required_tools,
            "first_step": self.first_step,
            "guardrails": self.guardrails,
            "non_actions": self.non_actions,
            "risk_level": self.risk_level.value,
            "confidence": self.confidence.value,
            "time_horizon": self.time_horizon.value,
            "metadata": self.metadata,
        }
