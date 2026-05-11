"""
PrimitiveRegistry — ontological primitives for the Meta Harness.

These are the 10 fundamental building blocks that compose all templates,
world models, and system behaviors. They are domain-agnostic — they apply
to business, personal development, and any future domain.

Distinct from eos_ai/primitives.py which contains domain-specific
business rules (KnowledgePrimitive / PRIMITIVE_LIBRARY).
"""

import os
import sys
from dataclasses import dataclass, field

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


@dataclass
class Primitive:
    """A fundamental ontological building block."""

    id: str
    name: str
    description: str
    properties: dict
    relationships: list[str]  # IDs of related primitives
    laws: list[str]  # governing laws that constrain this primitive
    version: int = 1


_PRIMITIVES: dict[str, Primitive] = {
    "state": Primitive(
        id="state",
        name="State",
        description="A snapshot of a system at a point in time.",
        properties={"observable": True, "mutable": True, "bounded": True},
        relationships=["change", "constraint"],
        laws=[
            "Every state is the result of prior changes",
            "State without observation is unknown state",
        ],
    ),
    "change": Primitive(
        id="change",
        name="Change",
        description="A transition between states.",
        properties={"reversible": "sometimes", "measurable": True, "causal": True},
        relationships=["state", "action", "outcome"],
        laws=[
            "Change requires energy",
            "Unobserved change is indistinguishable from no change",
        ],
    ),
    "constraint": Primitive(
        id="constraint",
        name="Constraint",
        description="A boundary that limits what is possible.",
        properties={
            "explicit": "sometimes",
            "discoverable": True,
            "removable": "sometimes",
        },
        relationships=["state", "resource", "action"],
        laws=[
            "Every system has binding constraints",
            "Removing one constraint reveals the next",
        ],
    ),
    "resource": Primitive(
        id="resource",
        name="Resource",
        description="Anything consumed or deployed to produce change.",
        properties={"finite": True, "fungible": "sometimes", "depletable": True},
        relationships=["constraint", "action", "goal"],
        laws=[
            "Resources are always finite",
            "Allocation is a zero-sum game within a time window",
        ],
    ),
    "time": Primitive(
        id="time",
        name="Time",
        description="The irreversible dimension along which all change occurs.",
        properties={"irreversible": True, "uniform": False, "bounded": True},
        relationships=["change", "state", "constraint"],
        laws=[
            "Time flows one direction",
            "Opportunity cost is measured in time",
        ],
    ),
    "signal": Primitive(
        id="signal",
        name="Signal",
        description="Observable information that indicates state or change.",
        properties={"noisy": True, "perishable": True, "actionable": "sometimes"},
        relationships=["state", "feedback", "action"],
        laws=[
            "Signals decay with time",
            "Signal-to-noise ratio determines actionability",
        ],
    ),
    "feedback": Primitive(
        id="feedback",
        name="Feedback",
        description="Information about the outcome of an action fed back to the actor.",
        properties={"delayed": "usually", "lossy": True, "directional": True},
        relationships=["signal", "action", "outcome"],
        laws=[
            "Feedback without action is noise",
            "Delayed feedback distorts causality",
        ],
    ),
    "goal": Primitive(
        id="goal",
        name="Goal",
        description="A desired future state.",
        properties={"measurable": True, "time_bound": True, "hierarchical": True},
        relationships=["state", "action", "resource"],
        laws=[
            "A goal without a constraint is a wish",
            "Goals compose into hierarchies",
        ],
    ),
    "action": Primitive(
        id="action",
        name="Action",
        description="An intentional intervention to produce change.",
        properties={"reversible": "sometimes", "costly": True, "observable": True},
        relationships=["change", "resource", "goal", "outcome"],
        laws=[
            "Every action has a cost",
            "Action without feedback is gambling",
        ],
    ),
    "outcome": Primitive(
        id="outcome",
        name="Outcome",
        description="The result of an action, observed after the fact.",
        properties={
            "measurable": True,
            "stochastic": True,
            "attributable": "partially",
        },
        relationships=["action", "feedback", "state"],
        laws=[
            "Outcomes are probabilistic, not deterministic",
            "Attribution is always partial",
        ],
    ),
}


class PrimitiveRegistry:
    """Registry for ontological primitives used by the Meta Harness."""

    def __init__(self) -> None:
        self._primitives: dict[str, Primitive] = dict(_PRIMITIVES)

    def get(self, primitive_id: str) -> Primitive | None:
        """Return a primitive by ID, or None if not found."""
        return self._primitives.get(primitive_id)

    def list_all(self) -> list[Primitive]:
        """Return all registered primitives."""
        return list(self._primitives.values())

    def get_related(self, primitive_id: str) -> list[Primitive]:
        """Return all primitives related to the given primitive."""
        p = self._primitives.get(primitive_id)
        if not p:
            return []
        return [
            self._primitives[rid]
            for rid in p.relationships
            if rid in self._primitives
        ]

    def validate_composition(self, primitive_ids: list[str]) -> bool:
        """Check that a set of primitives forms a valid composition.

        Valid = every referenced relationship is either in the set
        or exists in the registry.
        """
        for pid in primitive_ids:
            p = self._primitives.get(pid)
            if not p:
                return False
            for rel in p.relationships:
                if rel not in self._primitives:
                    return False
        return True


if __name__ == "__main__":
    registry = PrimitiveRegistry()
    for p in registry.list_all():
        print(f"{p.id}: {p.name} — laws: {p.laws}")
    print(f"\nTotal: {len(registry.list_all())} primitives registered")
    # Validate a composition
    valid = registry.validate_composition(["state", "change", "action", "outcome"])
    print(f"Composition [state, change, action, outcome] valid: {valid}")
    # Get related
    related = registry.get_related("action")
    print(f"Action related to: {[r.id for r in related]}")
