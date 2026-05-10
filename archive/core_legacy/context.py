"""L1 Context Layer — customisation inputs that shape compositions.

Context captures intent, preferences, identity, and client-specific
data.  It affects HOW domain compositions (L2) are populated but
NEVER modifies L0 primitives.

The key function is `apply_context()`:
    composition + context → enriched composition (same primitive tags)

Usage:
    from core.context import CompositionContext, apply_context

    ctx = CompositionContext(
        intent="generate outreach message for ICP",
        preferences={"tone": "direct", "length": "short"},
        client_context={"venture": "lyfe_institute", "stage": 1},
    )
    enriched = apply_context(icp, ctx)
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from core.domain.eos import DomainComposition
from core.primitives import PrimitiveTag


# ---------------------------------------------------------------------------
# L1 context structure
# ---------------------------------------------------------------------------


@dataclass
class CompositionContext:
    """L1 customisation inputs.

    These travel alongside compositions through the system but never
    alter which L0 primitives a composition maps to.
    """

    intent: str = ""
    preferences: dict[str, Any] = field(default_factory=dict)
    values: dict[str, Any] = field(default_factory=dict)
    identity: dict[str, Any] = field(default_factory=dict)
    client_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "preferences": dict(self.preferences),
            "values": dict(self.values),
            "identity": dict(self.identity),
            "client_context": dict(self.client_context),
        }


# ---------------------------------------------------------------------------
# Context application
# ---------------------------------------------------------------------------


@dataclass
class ContextualComposition:
    """A domain composition enriched with L1 context.

    The primitive tags remain identical to the original composition —
    context only affects content, not structure.
    """

    composition: DomainComposition
    context: CompositionContext
    _original_tags: set[PrimitiveTag] = field(default_factory=set, repr=False)

    def __post_init__(self) -> None:
        self._original_tags = self.composition.to_primitives()

    def to_primitives(self) -> set[PrimitiveTag]:
        """Primitive tags are preserved — context doesn't change structure."""
        return self._original_tags

    def validate_isolation(self) -> list[str]:
        """Verify L1 context has not modified L0 structure."""
        current = self.composition.to_primitives()
        errors: list[str] = []
        if current != self._original_tags:
            errors.append(
                f"Context violated L0 isolation: "
                f"original={sorted(t.value for t in self._original_tags)}, "
                f"current={sorted(t.value for t in current)}"
            )
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "composition": self.composition.to_dict(),
            "context": self.context.to_dict(),
            "isolation_valid": len(self.validate_isolation()) == 0,
        }


def apply_context(
    composition: DomainComposition,
    context: CompositionContext,
) -> ContextualComposition:
    """Apply L1 context to an L2 composition.

    Returns a ContextualComposition that wraps the original with
    context metadata.  The composition's primitive tags are frozen
    at call time — any subsequent mutation that changes them will
    be caught by `validate_isolation()`.
    """
    # Defensive copy so context application can't mutate the caller's object
    enriched = copy.deepcopy(composition)
    return ContextualComposition(composition=enriched, context=context)


__all__ = [
    "CompositionContext",
    "ContextualComposition",
    "apply_context",
]
