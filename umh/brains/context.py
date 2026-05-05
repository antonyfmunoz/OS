"""Brain context — the epigenetic injection layer.

Builds a BrainContext that shapes interpretation, decomposition,
and planning WITHOUT touching execution.

BrainContext is a frozen data object. It influences:
  - Intent compilation (concept weighting)
  - Task decomposition (pattern bias, role inference)
  - Plan objective context (injected into PlanObjective.context)

BrainContext does NOT:
  - Execute actions
  - Call tools
  - Route providers
  - Mutate substrate state

Usage:
    from umh.brains.context import build_brain_context

    ctx = build_brain_context("ceo_brain")
    intent = compile_intent(bundle, brain_context=ctx)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.brains.profile import AuthorityLevel, BrainProfile, ExpressionState
from umh.brains.registry import (
    get_expression_state,
    resolve_with_inheritance,
)


@dataclass(frozen=True)
class BrainContext:
    """Immutable context object injected into interpretation + planning.

    This is the single interface between brains and the rest of UMH.
    Every field is read-only. No methods mutate external state.
    """

    brain_id: str
    active_primitives: frozenset[str]
    retrieval_weights: dict[str, float]
    amplified_concepts: frozenset[str]
    silenced_concepts: frozenset[str]
    preferred_patterns: tuple[str, ...]
    authority_level: AuthorityLevel
    concept_weights: dict[str, float]
    suppressed_intents: frozenset[str]
    pattern_bias: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "brain_id": self.brain_id,
            "active_primitives": sorted(self.active_primitives),
            "retrieval_weights": self.retrieval_weights,
            "amplified_concepts": sorted(self.amplified_concepts),
            "silenced_concepts": sorted(self.silenced_concepts),
            "preferred_patterns": list(self.preferred_patterns),
            "authority_level": self.authority_level.value,
            "concept_weights": self.concept_weights,
            "suppressed_intents": sorted(self.suppressed_intents),
            "pattern_bias": self.pattern_bias,
        }

    def weight_for_concept(self, concept: str) -> float:
        """Return the effective weight for a concept.

        Amplified concepts get a boost, silenced concepts get suppressed,
        explicit concept_weights override both.
        """
        if concept in self.concept_weights:
            return self.concept_weights[concept]
        if concept in self.silenced_concepts:
            return 0.0
        if concept in self.amplified_concepts:
            return 2.0
        return 1.0

    def should_suppress_intent(self, intent_type: str) -> bool:
        return intent_type in self.suppressed_intents

    def pattern_weight(self, pattern: str) -> float:
        """Return the bias weight for a pattern (default 1.0)."""
        return self.pattern_bias.get(pattern, 1.0)


_EMPTY_CONTEXT = BrainContext(
    brain_id="",
    active_primitives=frozenset(),
    retrieval_weights={},
    amplified_concepts=frozenset(),
    silenced_concepts=frozenset(),
    preferred_patterns=(),
    authority_level=AuthorityLevel.OBSERVE,
    concept_weights={},
    suppressed_intents=frozenset(),
    pattern_bias={},
)


def build_brain_context(brain_id: str) -> BrainContext:
    """Build a complete BrainContext from profile + expression state.

    Returns _EMPTY_CONTEXT if the brain_id is not registered.
    Applies inheritance before merging with expression state.
    """
    profile = resolve_with_inheritance(brain_id)
    if profile is None:
        return _EMPTY_CONTEXT

    expression = get_expression_state(brain_id)

    concept_weights: dict[str, float] = {}
    suppressed_intents: frozenset[str] = frozenset()
    pattern_bias: dict[str, float] = {}

    if expression is not None:
        concept_weights = dict(expression.concept_weights)
        suppressed_intents = frozenset(expression.suppressed_intents)
        pattern_bias = dict(expression.pattern_bias)

    return BrainContext(
        brain_id=profile.brain_id,
        active_primitives=frozenset(profile.active_primitives),
        retrieval_weights=dict(profile.retrieval_weights),
        amplified_concepts=profile.amplified_concepts,
        silenced_concepts=profile.silenced_concepts,
        preferred_patterns=profile.preferred_patterns,
        authority_level=profile.authority,
        concept_weights=concept_weights,
        suppressed_intents=suppressed_intents,
        pattern_bias=pattern_bias,
    )


def empty_context() -> BrainContext:
    """Return the neutral/no-op brain context."""
    return _EMPTY_CONTEXT
