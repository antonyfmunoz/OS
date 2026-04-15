"""Primitive Transformation Engine — restructures primitive compositions.

Given a set of primitives, an objective, and constraints, the transformer
analyses the composition for gaps and inefficiencies then returns an
improved primitive set.  It never mutates the input, never introduces new
primitive types, and every decision is recorded in the TransformationResult.

Usage:
    from core.transformer import transform

    result = transform(
        primitives={PrimitiveTag.STATE, PrimitiveTag.GOAL},
        objective="generate personalised outreach",
        constraints={"must_include_feedback": True},
        context=ctx,
    )
    print(result.reasoning)
    print(result.transformed_primitives)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.primitives import L0, PrimitiveTag, validate_composition_tags


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransformationResult:
    """Immutable record of a transformation decision.

    Everything is traceable: original input, what changed, why, and
    the expected impact.
    """

    original_primitives: frozenset[PrimitiveTag]
    transformed_primitives: frozenset[PrimitiveTag]
    reasoning: list[str]
    expected_impact: dict[str, Any]
    rules_applied: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return self.original_primitives != self.transformed_primitives

    @property
    def added(self) -> frozenset[PrimitiveTag]:
        return self.transformed_primitives - self.original_primitives

    @property
    def removed(self) -> frozenset[PrimitiveTag]:
        return self.original_primitives - self.transformed_primitives

    def to_dict(self) -> dict[str, Any]:
        return {
            "original": sorted(t.value for t in self.original_primitives),
            "transformed": sorted(t.value for t in self.transformed_primitives),
            "changed": self.changed,
            "added": sorted(t.value for t in self.added),
            "removed": sorted(t.value for t in self.removed),
            "reasoning": self.reasoning,
            "expected_impact": self.expected_impact,
            "rules_applied": list(self.rules_applied),
        }


# ---------------------------------------------------------------------------
# Transformation rules
#
# Each rule is a pure function: (tags, objective, constraints) -> (tags, reasons).
# Rules are composable and order-independent (each operates on the
# accumulated tag set from prior rules).
# ---------------------------------------------------------------------------

TransformRule = tuple[
    str,  # rule name
    Any,  # Callable — typed loosely to avoid forward-ref issues
]


def _rule_ensure_goal_action(
    tags: set[PrimitiveTag],
    objective: str,
    constraints: dict[str, Any],
) -> tuple[set[PrimitiveTag], list[str]]:
    """Every executable composition needs GOAL + ACTION at minimum."""
    reasons: list[str] = []
    if PrimitiveTag.GOAL not in tags:
        tags = tags | {PrimitiveTag.GOAL}
        reasons.append("added GOAL — every executable composition needs a target state")
    if PrimitiveTag.ACTION not in tags:
        tags = tags | {PrimitiveTag.ACTION}
        reasons.append("added ACTION — execution requires at least one action")
    return tags, reasons


def _rule_feedback_loop(
    tags: set[PrimitiveTag],
    objective: str,
    constraints: dict[str, Any],
) -> tuple[set[PrimitiveTag], list[str]]:
    """If OUTCOME is present, FEEDBACK should be too — results need evaluation."""
    reasons: list[str] = []
    if PrimitiveTag.OUTCOME in tags and PrimitiveTag.FEEDBACK not in tags:
        tags = tags | {PrimitiveTag.FEEDBACK}
        reasons.append(
            "added FEEDBACK — OUTCOME without FEEDBACK means results "
            "are measured but never evaluated"
        )
    return tags, reasons


def _rule_state_tracking(
    tags: set[PrimitiveTag],
    objective: str,
    constraints: dict[str, Any],
) -> tuple[set[PrimitiveTag], list[str]]:
    """CHANGE without STATE is incoherent — you need a before/after."""
    reasons: list[str] = []
    if PrimitiveTag.CHANGE in tags and PrimitiveTag.STATE not in tags:
        tags = tags | {PrimitiveTag.STATE}
        reasons.append("added STATE — CHANGE requires observable before/after states")
    return tags, reasons


def _rule_outcome_closure(
    tags: set[PrimitiveTag],
    objective: str,
    constraints: dict[str, Any],
) -> tuple[set[PrimitiveTag], list[str]]:
    """ACTION + GOAL without OUTCOME means we act but never measure success."""
    reasons: list[str] = []
    if (
        PrimitiveTag.ACTION in tags
        and PrimitiveTag.GOAL in tags
        and PrimitiveTag.OUTCOME not in tags
    ):
        tags = tags | {PrimitiveTag.OUTCOME}
        reasons.append("added OUTCOME — ACTION toward GOAL needs measurable results")
    return tags, reasons


def _rule_resource_awareness(
    tags: set[PrimitiveTag],
    objective: str,
    constraints: dict[str, Any],
) -> tuple[set[PrimitiveTag], list[str]]:
    """If constraints mention cost/budget/capacity, ensure RESOURCE is present."""
    reasons: list[str] = []
    cost_keywords = {"cost", "budget", "capacity", "resource", "spend", "limit"}
    constraint_text = " ".join(str(v) for v in constraints.values()).lower()
    if any(kw in constraint_text for kw in cost_keywords):
        if PrimitiveTag.RESOURCE not in tags:
            tags = tags | {PrimitiveTag.RESOURCE}
            reasons.append(
                "added RESOURCE — constraints reference cost/budget/capacity"
            )
    return tags, reasons


def _rule_signal_for_detection(
    tags: set[PrimitiveTag],
    objective: str,
    constraints: dict[str, Any],
) -> tuple[set[PrimitiveTag], list[str]]:
    """Outreach/detection objectives need SIGNAL for observability."""
    reasons: list[str] = []
    detection_keywords = {"outreach", "detect", "find", "monitor", "discover", "signal"}
    if any(kw in objective.lower() for kw in detection_keywords):
        if PrimitiveTag.SIGNAL not in tags:
            tags = tags | {PrimitiveTag.SIGNAL}
            reasons.append(
                "added SIGNAL — objective involves detection/outreach "
                "which requires observable signals"
            )
    return tags, reasons


def _rule_temporal_binding(
    tags: set[PrimitiveTag],
    objective: str,
    constraints: dict[str, Any],
) -> tuple[set[PrimitiveTag], list[str]]:
    """If constraints include deadlines or scheduling, add TIME."""
    reasons: list[str] = []
    time_keywords = {"deadline", "schedule", "before", "after", "within", "by", "daily"}
    constraint_text = " ".join(str(v) for v in constraints.values()).lower()
    if any(kw in constraint_text for kw in time_keywords):
        if PrimitiveTag.TIME not in tags:
            tags = tags | {PrimitiveTag.TIME}
            reasons.append("added TIME — constraints include temporal bounds")
    return tags, reasons


def _rule_constraint_must_include(
    tags: set[PrimitiveTag],
    objective: str,
    constraints: dict[str, Any],
) -> tuple[set[PrimitiveTag], list[str]]:
    """Honour explicit must_include_* constraints."""
    reasons: list[str] = []
    for key, value in constraints.items():
        if not key.startswith("must_include_") or not value:
            continue
        tag_name = key.replace("must_include_", "").upper()
        try:
            required_tag = PrimitiveTag(tag_name.lower())
        except ValueError:
            continue
        if required_tag not in tags:
            tags = tags | {required_tag}
            reasons.append(
                f"added {required_tag.value.upper()} — explicitly required by constraint"
            )
    return tags, reasons


# Ordered list of rules. Order matters only for readability — each rule
# sees the accumulated result of prior rules.
TRANSFORM_RULES: list[tuple[str, Any]] = [
    ("ensure_goal_action", _rule_ensure_goal_action),
    ("feedback_loop", _rule_feedback_loop),
    ("state_tracking", _rule_state_tracking),
    ("outcome_closure", _rule_outcome_closure),
    ("resource_awareness", _rule_resource_awareness),
    ("signal_for_detection", _rule_signal_for_detection),
    ("temporal_binding", _rule_temporal_binding),
    ("constraint_must_include", _rule_constraint_must_include),
]


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------


def transform(
    primitives: set[PrimitiveTag],
    objective: str,
    constraints: dict[str, Any] | None = None,
    context: Any
    | None = None,  # CompositionContext — kept loose to avoid circular import
) -> TransformationResult:
    """Analyse and transform a primitive set based on objective + constraints.

    Returns a new set (never mutates input). Every addition/removal is
    explained in the reasoning list.

    Args:
        primitives: Current L0 primitive tags.
        objective: What the composition is trying to achieve.
        constraints: Key-value constraints (e.g. {"must_include_feedback": True}).
        context: Optional CompositionContext for additional signals.

    Returns:
        TransformationResult with original, transformed, reasoning, impact.
    """
    constraints = constraints or {}
    original = frozenset(primitives)
    working = set(primitives)
    all_reasons: list[str] = []
    rules_applied: list[str] = []

    for rule_name, rule_fn in TRANSFORM_RULES:
        working, reasons = rule_fn(working, objective, constraints)
        if reasons:
            all_reasons.extend(reasons)
            rules_applied.append(rule_name)

    transformed = frozenset(working)

    # Validate the result
    validation_warnings = validate_composition_tags(
        working, require_goal=False, require_action=False
    )
    if validation_warnings:
        all_reasons.append(f"post-transform validation warnings: {validation_warnings}")

    # Calculate expected impact
    added = transformed - original
    removed = original - transformed
    impact: dict[str, Any] = {
        "primitives_added": len(added),
        "primitives_removed": len(removed),
        "completeness_before": _completeness_score(original),
        "completeness_after": _completeness_score(transformed),
        "relationship_closure_before": _closure_score(original),
        "relationship_closure_after": _closure_score(transformed),
    }

    return TransformationResult(
        original_primitives=original,
        transformed_primitives=transformed,
        reasoning=all_reasons,
        expected_impact=impact,
        rules_applied=rules_applied,
    )


def _completeness_score(tags: frozenset[PrimitiveTag]) -> float:
    """Ratio of primitives present to total available (0.0–1.0)."""
    return len(tags) / len(PrimitiveTag) if PrimitiveTag else 0.0


def _closure_score(tags: frozenset[PrimitiveTag]) -> float:
    """Fraction of relationship references that are satisfied (0.0–1.0).

    A score of 1.0 means every primitive's declared relationships are
    also present in the set.
    """
    if not tags:
        return 0.0
    total_refs = 0
    satisfied = 0
    for tag in tags:
        defn = L0[tag]
        for rel in defn.relationships:
            total_refs += 1
            try:
                if PrimitiveTag(rel) in tags:
                    satisfied += 1
            except ValueError:
                pass
    return satisfied / total_refs if total_refs else 1.0


__all__ = [
    "TransformationResult",
    "transform",
    "TRANSFORM_RULES",
]
