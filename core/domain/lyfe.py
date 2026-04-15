"""LyfeOS domain compositions — personal operating system structures.

Maps life-optimization concepts to L0 primitives following the same
pattern as EOS business compositions.

Usage:
    from core.domain.lyfe import Habit, Energy, Focus, IdentityState

    habit = Habit(name="morning-routine", trigger="6am alarm", goal="peak state by 7am")
    print(habit.to_primitives())  # {ACTION, STATE, CHANGE, TIME, GOAL, CONSTRAINT}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.domain.eos import DomainComposition
from core.primitives import PrimitiveTag


# ---------------------------------------------------------------------------
# Habit
# Decomposes to: ACTION + STATE + CHANGE + TIME + GOAL + CONSTRAINT
# ---------------------------------------------------------------------------


@dataclass
class Habit(DomainComposition):
    """A repeatable behaviour pattern that changes state over time.

    Habits are the atomic unit of life change — constrained actions
    performed at specific times toward a goal.
    """

    trigger: str = ""
    frequency: str = ""
    goal: str = ""
    current_streak: int = 0
    constraints: list[str] = field(default_factory=list)

    def _primitive_tags(self) -> set[PrimitiveTag]:
        return {
            PrimitiveTag.ACTION,  # the behaviour itself
            PrimitiveTag.STATE,  # before/after state
            PrimitiveTag.CHANGE,  # the transformation over time
            PrimitiveTag.TIME,  # when and how often
            PrimitiveTag.GOAL,  # why we do it
            PrimitiveTag.CONSTRAINT,  # what limits adherence
        }


# ---------------------------------------------------------------------------
# Energy
# Decomposes to: STATE + RESOURCE + TIME + SIGNAL + CONSTRAINT
# ---------------------------------------------------------------------------


@dataclass
class Energy(DomainComposition):
    """Current energy state as a trackable resource with temporal patterns."""

    level: float = 0.0  # 0.0-1.0
    sources: list[str] = field(default_factory=list)
    drains: list[str] = field(default_factory=list)
    peak_times: list[str] = field(default_factory=list)

    def _primitive_tags(self) -> set[PrimitiveTag]:
        return {
            PrimitiveTag.STATE,  # current energy level
            PrimitiveTag.RESOURCE,  # energy as consumable resource
            PrimitiveTag.TIME,  # temporal energy patterns
            PrimitiveTag.SIGNAL,  # indicators of energy state
            PrimitiveTag.CONSTRAINT,  # limits on energy availability
        }


# ---------------------------------------------------------------------------
# Focus
# Decomposes to: STATE + ACTION + GOAL + TIME + CONSTRAINT + RESOURCE
# ---------------------------------------------------------------------------


@dataclass
class Focus(DomainComposition):
    """Attention allocation — what you're working on and what you're ignoring."""

    current_focus: str = ""
    blocked_items: list[str] = field(default_factory=list)
    time_block: str = ""
    priority_goal: str = ""

    def _primitive_tags(self) -> set[PrimitiveTag]:
        return {
            PrimitiveTag.STATE,  # current attention state
            PrimitiveTag.ACTION,  # the focused work
            PrimitiveTag.GOAL,  # what the focus serves
            PrimitiveTag.TIME,  # time-boxing
            PrimitiveTag.CONSTRAINT,  # what's deliberately excluded
            PrimitiveTag.RESOURCE,  # attention as finite resource
        }


# ---------------------------------------------------------------------------
# IdentityState
# Decomposes to: STATE + GOAL + CHANGE + FEEDBACK + SIGNAL
# ---------------------------------------------------------------------------


@dataclass
class IdentityState(DomainComposition):
    """Who you are becoming — the gap between current and target identity."""

    current_identity: str = ""
    target_identity: str = ""
    evidence: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)

    def _primitive_tags(self) -> set[PrimitiveTag]:
        return {
            PrimitiveTag.STATE,  # who you are now
            PrimitiveTag.GOAL,  # who you want to become
            PrimitiveTag.CHANGE,  # the identity transition
            PrimitiveTag.FEEDBACK,  # evidence of progress
            PrimitiveTag.SIGNAL,  # signals of identity alignment
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

LYFE_DOMAIN_TYPES: dict[str, type[DomainComposition]] = {
    "habit": Habit,
    "energy": Energy,
    "focus": Focus,
    "identity_state": IdentityState,
}


__all__ = [
    "Habit",
    "Energy",
    "Focus",
    "IdentityState",
    "LYFE_DOMAIN_TYPES",
]
