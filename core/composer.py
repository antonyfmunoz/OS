"""Composition Engine — converts intent + context into executable primitive structures.

Flow:
    intent (str)
    → resolve domain composition type (L2)
    → populate from context (L1)
    → validate primitive mapping (L0)
    → return ComposedStructure ready for execution

Usage:
    from core.composer import compose, validate_composition, trace_to_primitives

    result = compose(
        intent="generate outreach message for ICP",
        context=CompositionContext(
            client_context={"venture": "lyfe_institute", "stage": 1},
        ),
    )
    print(result.primitive_trace)  # full L0 audit trail
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.context import CompositionContext, ContextualComposition, apply_context
from core.domain.eos import (
    DOMAIN_TYPES,
    Channel,
    DomainComposition,
    ICP,
    KPI,
    Offer,
    Role,
    Workflow,
)
from core.domain.lyfe import Habit, Energy, Focus, IdentityState
from core.domain.creator import Content, Audience, Platform, Engagement
from core.primitives import PrimitiveTag, decompose_to_dict, validate_composition_tags


# ---------------------------------------------------------------------------
# Intent → domain type resolution
# ---------------------------------------------------------------------------

# Keyword mapping: words in the intent → which domain composition to use.
# Ordered by specificity (more specific keywords first).
_INTENT_KEYWORDS: list[tuple[list[str], str]] = [
    # CreatorOS domains (specific keywords first to avoid EOS collisions)
    (["content", "post", "reel", "video", "article", "carousel"], "content"),
    (["followers", "community", "subscribers", "audience growth"], "audience"),
    (["engagement", "likes", "comments", "shares", "saves"], "engagement"),
    (["distribution", "publishing"], "platform"),
    # LyfeOS domains
    (["habit", "routine", "streak", "daily practice"], "habit"),
    (["energy", "fatigue", "recovery", "peak state"], "energy"),
    (["focus", "attention", "deep work", "time block"], "focus"),
    (["identity", "becoming", "who i am"], "identity_state"),
    # EOS business domains
    (["outreach", "message", "dm", "reach out"], "icp"),
    (["icp", "customer", "prospect", "lead", "audience"], "icp"),
    (["offer", "pricing", "package", "proposal", "sell"], "offer"),
    (["channel", "platform", "medium", "instagram", "linkedin", "email"], "channel"),
    (["workflow", "process", "sequence", "automate", "pipeline"], "workflow"),
    (["kpi", "metric", "measure", "track", "performance"], "kpi"),
    (["role", "agent", "responsibility", "hire", "assign"], "role"),
]


def resolve_domain_type(intent: str) -> str:
    """Map a natural-language intent to a domain composition type key.

    Returns the DOMAIN_TYPES key (e.g. "icp", "offer").
    Falls back to "workflow" when no keywords match — most intents
    describe a process to execute.
    """
    intent_lower = intent.lower()
    for keywords, dtype in _INTENT_KEYWORDS:
        if any(kw in intent_lower for kw in keywords):
            return dtype
    return "workflow"


# ---------------------------------------------------------------------------
# Composition result
# ---------------------------------------------------------------------------


@dataclass
class ComposedStructure:
    """The output of `compose()` — ready for execution.

    Contains:
    - The contextualised composition (L2 + L1)
    - The resolved domain type
    - The original intent
    - Primitive trace (full L0 audit trail)
    - Validation errors (empty = ready to execute)
    """

    intent: str
    domain_type: str
    contextual: ContextualComposition
    primitive_trace: list[dict[str, Any]]
    validation_errors: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return len(self.validation_errors) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "domain_type": self.domain_type,
            "ok": self.ok,
            "validation_errors": self.validation_errors,
            "contextual": self.contextual.to_dict(),
            "primitive_trace": self.primitive_trace,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Populate helpers
# ---------------------------------------------------------------------------


def _populate_from_context(
    composition: DomainComposition,
    context: CompositionContext,
) -> DomainComposition:
    """Fill composition fields from context where applicable.

    This is the L1 → L2 bridge: context data flows into domain fields
    without changing which primitives the composition maps to.
    """
    cc = context.client_context

    if isinstance(composition, ICP):
        composition.current_state = cc.get("current_state", composition.current_state)
        composition.desired_state = cc.get("desired_state", composition.desired_state)
        if "constraints" in cc:
            composition.constraints = list(cc["constraints"])
        if "signals" in cc:
            composition.signals = list(cc["signals"])

    elif isinstance(composition, Offer):
        composition.promise = cc.get("promise", composition.promise)
        composition.price = cc.get("price", composition.price)
        if "deliverables" in cc:
            composition.deliverables = list(cc["deliverables"])

    elif isinstance(composition, Channel):
        composition.medium = cc.get("medium", composition.medium)
        composition.cost_per_touch = cc.get(
            "cost_per_touch", composition.cost_per_touch
        )

    elif isinstance(composition, Workflow):
        composition.trigger = cc.get("trigger", composition.trigger)
        composition.goal = cc.get("goal", composition.goal)
        if "steps" in cc:
            composition.steps = list(cc["steps"])

    elif isinstance(composition, KPI):
        composition.metric = cc.get("metric", composition.metric)
        composition.target = cc.get("target", composition.target)
        composition.current = cc.get("current", composition.current)

    elif isinstance(composition, Role):
        composition.objective = cc.get("objective", composition.objective)
        if "responsibilities" in cc:
            composition.responsibilities = list(cc["responsibilities"])

    # LyfeOS domains
    elif isinstance(composition, Habit):
        composition.trigger = cc.get("trigger", composition.trigger)
        composition.frequency = cc.get("frequency", composition.frequency)
        composition.goal = cc.get("goal", composition.goal)
        composition.current_streak = cc.get(
            "current_streak", composition.current_streak
        )

    elif isinstance(composition, Energy):
        composition.level = cc.get("level", composition.level)
        if "sources" in cc:
            composition.sources = list(cc["sources"])
        if "drains" in cc:
            composition.drains = list(cc["drains"])

    elif isinstance(composition, Focus):
        composition.current_focus = cc.get("current_focus", composition.current_focus)
        composition.priority_goal = cc.get("priority_goal", composition.priority_goal)
        composition.time_block = cc.get("time_block", composition.time_block)

    elif isinstance(composition, IdentityState):
        composition.current_identity = cc.get(
            "current_identity", composition.current_identity
        )
        composition.target_identity = cc.get(
            "target_identity", composition.target_identity
        )

    # CreatorOS domains
    elif isinstance(composition, Content):
        composition.format = cc.get("format", composition.format)
        composition.topic = cc.get("topic", composition.topic)
        composition.hook = cc.get("hook", composition.hook)
        composition.call_to_action = cc.get(
            "call_to_action", composition.call_to_action
        )

    elif isinstance(composition, Audience):
        composition.segment = cc.get("segment", composition.segment)
        composition.size = cc.get("size", composition.size)
        if "signals" in cc:
            composition.signals = list(cc["signals"])
        if "pain_points" in cc:
            composition.pain_points = list(cc["pain_points"])

    elif isinstance(composition, Platform):
        composition.platform_name = cc.get("platform_name", composition.platform_name)
        composition.reach = cc.get("reach", composition.reach)
        composition.cost = cc.get("cost", composition.cost)

    elif isinstance(composition, Engagement):
        composition.metric_type = cc.get("metric_type", composition.metric_type)
        composition.value = cc.get("value", composition.value)
        composition.benchmark = cc.get("benchmark", composition.benchmark)
        composition.trend = cc.get("trend", composition.trend)

    return composition


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------


def compose(
    intent: str,
    context: CompositionContext | None = None,
) -> ComposedStructure:
    """Convert intent + context into an executable composition.

    This is the main entry point.  Steps:
    1. Resolve which domain type the intent maps to
    2. Instantiate the domain composition
    3. Populate from context
    4. Apply context (freezes primitive tags)
    5. Validate the primitive mapping
    6. Build the primitive trace (audit trail)
    """
    context = context or CompositionContext(intent=intent)
    if not context.intent:
        context.intent = intent

    # 1. Resolve domain type
    domain_type = resolve_domain_type(intent)
    cls = DOMAIN_TYPES[domain_type]

    # 2. Instantiate
    composition = cls(name=f"{domain_type}:{intent[:60]}")

    # 3. Populate from context
    composition = _populate_from_context(composition, context)

    # 4. Apply context (creates ContextualComposition with frozen tags)
    contextual = apply_context(composition, context)

    # 5. Validate
    tags = contextual.to_primitives()
    validation_errors = validate_composition_tags(
        tags,
        require_goal=False,
        require_action=False,
    )
    isolation_errors = contextual.validate_isolation()
    all_errors = isolation_errors  # isolation errors are hard failures

    # 6. Primitive trace
    trace = decompose_to_dict(tags)

    return ComposedStructure(
        intent=intent,
        domain_type=domain_type,
        contextual=contextual,
        primitive_trace=trace,
        validation_errors=all_errors,
        metadata={
            "relationship_warnings": validation_errors,
        },
    )


def validate_composition(structure: ComposedStructure) -> list[str]:
    """Re-validate a composed structure (e.g. after mutation)."""
    errors = structure.contextual.validate_isolation()
    tags = structure.contextual.to_primitives()
    errors.extend(
        validate_composition_tags(tags, require_goal=False, require_action=False)
    )
    return errors


def trace_to_primitives(structure: ComposedStructure) -> list[dict[str, Any]]:
    """Return the full primitive trace for a composed structure."""
    return structure.primitive_trace


__all__ = [
    "ComposedStructure",
    "compose",
    "resolve_domain_type",
    "validate_composition",
    "trace_to_primitives",
]
