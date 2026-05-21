"""L0 Ontological Primitives — the immutable atoms of UMH.

Every domain concept decomposes into combinations of these 10
universal primitives.  They are ontological — they describe *what exists*
in any system that acts on the world — and they never change.

Layer model:
    L0  Ontological primitives  (this file — immutable, universal)
    L1  Customisation inputs    (intent, preferences, values, identity, client context)
    L2  Domain compositions     (Offer, ICP, Channel … — built from L0)
    L3  Instance / runtime      (real-time data, metrics, environment)

Canonical location: umh.primitives.ontological
Compatibility shim: core.primitives (re-exports from here)

Usage:
    from umh.primitives.ontological import L0, PrimitiveTag, validate_primitive_set
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any


# ---------------------------------------------------------------------------
# L0 primitive enum — the canonical set
# ---------------------------------------------------------------------------


@unique
class PrimitiveTag(Enum):
    """The 10 ontological primitives.

    These tags annotate every composition and every action so the system
    can trace *what kind of thing* is being operated on at the most
    fundamental level.
    """

    STATE = "state"
    CHANGE = "change"
    CONSTRAINT = "constraint"
    RESOURCE = "resource"
    TIME = "time"
    SIGNAL = "signal"
    FEEDBACK = "feedback"
    GOAL = "goal"
    ACTION = "action"
    OUTCOME = "outcome"


# ---------------------------------------------------------------------------
# Primitive definition
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OntologicalPrimitive:
    """Full definition of a single L0 primitive.

    Frozen so no runtime code can mutate the foundation.
    """

    tag: PrimitiveTag
    definition: str
    constraints: tuple[str, ...]
    relationships: tuple[str, ...]  # tags of related primitives


# ---------------------------------------------------------------------------
# Canonical registry — the single source of truth
# ---------------------------------------------------------------------------

L0: dict[PrimitiveTag, OntologicalPrimitive] = {
    PrimitiveTag.STATE: OntologicalPrimitive(
        tag=PrimitiveTag.STATE,
        definition="A snapshot of any entity at a point in time.",
        constraints=(
            "Must be observable or inferrable",
            "Must be representable as key-value pairs",
        ),
        relationships=("change", "outcome"),
    ),
    PrimitiveTag.CHANGE: OntologicalPrimitive(
        tag=PrimitiveTag.CHANGE,
        definition="A transition from one state to another.",
        constraints=(
            "Requires a before-state and an after-state",
            "Must be attributable to an action or external event",
        ),
        relationships=("state", "action"),
    ),
    PrimitiveTag.CONSTRAINT: OntologicalPrimitive(
        tag=PrimitiveTag.CONSTRAINT,
        definition="A boundary that limits what actions or states are valid.",
        constraints=(
            "Must be evaluable as true/false against a state",
            "Cannot be self-contradictory within a composition",
        ),
        relationships=("state", "action", "resource"),
    ),
    PrimitiveTag.RESOURCE: OntologicalPrimitive(
        tag=PrimitiveTag.RESOURCE,
        definition="Anything consumed, allocated, or required to perform an action.",
        constraints=(
            "Must be quantifiable or at least enumerable",
            "Consumption must be trackable",
        ),
        relationships=("action", "constraint", "time"),
    ),
    PrimitiveTag.TIME: OntologicalPrimitive(
        tag=PrimitiveTag.TIME,
        definition="A temporal coordinate or duration that bounds when things happen.",
        constraints=(
            "Must be expressible as a point or interval",
            "Ordering must be total within a single timeline",
        ),
        relationships=("state", "action", "constraint"),
    ),
    PrimitiveTag.SIGNAL: OntologicalPrimitive(
        tag=PrimitiveTag.SIGNAL,
        definition="An observable event that carries information about state or change.",
        constraints=(
            "Must be detectable by at least one observer",
            "Must carry enough context to be actionable or ignorable",
        ),
        relationships=("state", "change", "feedback"),
    ),
    PrimitiveTag.FEEDBACK: OntologicalPrimitive(
        tag=PrimitiveTag.FEEDBACK,
        definition="Information about the effect of a prior action, used to adjust future actions.",
        constraints=(
            "Must reference a prior action or outcome",
            "Must be timely enough to influence the next decision",
        ),
        relationships=("action", "outcome", "signal"),
    ),
    PrimitiveTag.GOAL: OntologicalPrimitive(
        tag=PrimitiveTag.GOAL,
        definition="A desired future state that motivates action.",
        constraints=(
            "Must be expressible as a target state",
            "Must be evaluable — you can tell if you reached it",
        ),
        relationships=("state", "action", "outcome"),
    ),
    PrimitiveTag.ACTION: OntologicalPrimitive(
        tag=PrimitiveTag.ACTION,
        definition="An operation performed by an agent that may change state.",
        constraints=(
            "Must have a defined trigger or initiator",
            "Must produce an observable outcome (even if null)",
        ),
        relationships=("state", "change", "resource", "goal"),
    ),
    PrimitiveTag.OUTCOME: OntologicalPrimitive(
        tag=PrimitiveTag.OUTCOME,
        definition="The measurable result of an action, compared against the goal.",
        constraints=(
            "Must be observable after the action completes",
            "Must be comparable to the goal that motivated the action",
        ),
        relationships=("action", "goal", "state", "feedback"),
    ),
}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_primitive_set(tags: set[PrimitiveTag]) -> list[str]:
    """Check a set of primitive tags for structural issues.

    Returns a list of warnings (empty = valid).  Checks:
    1. No unknown tags (enforced by enum, but belt-and-suspenders).
    2. No duplicate tags (set guarantees this, included for API clarity).
    3. Relationship closure — every related tag in the set's definitions
       must also be present in the set, or a warning is emitted.
    """
    warnings: list[str] = []
    all_tag_values = {t.value for t in PrimitiveTag}

    for tag in tags:
        if tag.value not in all_tag_values:
            warnings.append(f"Unknown primitive tag: {tag}")
            continue
        defn = L0[tag]
        for rel in defn.relationships:
            try:
                rel_tag = PrimitiveTag(rel)
            except ValueError:
                warnings.append(
                    f"{tag.value}: relationship '{rel}' is not a valid primitive"
                )
                continue
            if rel_tag not in tags:
                warnings.append(f"{tag.value}: related primitive '{rel}' not in set")
    return warnings


def validate_composition_tags(
    tags: set[PrimitiveTag],
    *,
    require_goal: bool = True,
    require_action: bool = True,
) -> list[str]:
    """Validate that a composition's primitive tags form a coherent set.

    A valid composition for execution must include at minimum:
    - GOAL (what we're trying to achieve)
    - ACTION (what we're doing)

    Returns list of errors (empty = valid).
    """
    errors: list[str] = []
    if require_goal and PrimitiveTag.GOAL not in tags:
        errors.append("Composition missing GOAL primitive")
    if require_action and PrimitiveTag.ACTION not in tags:
        errors.append("Composition missing ACTION primitive")
    errors.extend(validate_primitive_set(tags))
    return errors


def decompose_to_dict(tags: set[PrimitiveTag]) -> list[dict[str, Any]]:
    """Return the full definitions for a set of primitive tags.

    Useful for serialisation, logging, and audit trails.
    """
    result = []
    for tag in sorted(tags, key=lambda t: t.value):
        defn = L0[tag]
        result.append(
            {
                "tag": defn.tag.value,
                "definition": defn.definition,
                "constraints": list(defn.constraints),
                "relationships": list(defn.relationships),
            }
        )
    return result


__all__ = [
    "PrimitiveTag",
    "OntologicalPrimitive",
    "L0",
    "validate_primitive_set",
    "validate_composition_tags",
    "decompose_to_dict",
]
