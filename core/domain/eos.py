"""EOS domain compositions — L2 business structures mapped to L0 primitives.

Every structure here decomposes into ontological primitives via
`to_primitives()`.  These are the canonical building blocks of the
EOS business domain.  Other domains (LyfeOS, CreatorOS) will follow
the same pattern in separate files.

Usage:
    from core.domain.eos import ICP, Offer, Workflow, Channel, KPI, Role

    icp = ICP(
        name="struggling-founder",
        current_state="pre-revenue, building alone",
        desired_state="$10K/month, systematised",
        constraints=["no team", "limited capital"],
        signals=["posts about hustling", "asks about automation"],
    )
    primitives = icp.to_primitives()
    # → {STATE, GOAL, CONSTRAINT, SIGNAL}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.primitives import PrimitiveTag, decompose_to_dict, validate_composition_tags


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


@dataclass
class DomainComposition:
    """Base class for all L2 domain structures.

    Subclasses define which L0 primitives they map to by implementing
    `_primitive_tags()`.  The public API (`to_primitives`, `validate`,
    `to_dict`) is inherited.
    """

    name: str

    def _primitive_tags(self) -> set[PrimitiveTag]:
        raise NotImplementedError

    def to_primitives(self) -> set[PrimitiveTag]:
        """Return the L0 primitive tags this composition maps to."""
        return self._primitive_tags()

    def validate(self) -> list[str]:
        """Validate the primitive mapping is coherent."""
        return validate_composition_tags(
            self._primitive_tags(),
            require_goal=False,
            require_action=False,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise composition with full primitive trace."""
        return {
            "type": type(self).__name__,
            "name": self.name,
            "primitive_tags": sorted(t.value for t in self._primitive_tags()),
            "primitive_details": decompose_to_dict(self._primitive_tags()),
        }


# ---------------------------------------------------------------------------
# ICP — Ideal Customer Profile
# Decomposes to: STATE + GOAL + CONSTRAINT + SIGNAL
# ---------------------------------------------------------------------------


@dataclass
class ICP(DomainComposition):
    """Who we serve — defined by their current reality, desired future,
    limitations, and how we detect them.
    """

    current_state: str = ""
    desired_state: str = ""
    constraints: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)

    def _primitive_tags(self) -> set[PrimitiveTag]:
        return {
            PrimitiveTag.STATE,  # who they are now
            PrimitiveTag.GOAL,  # what they want to become
            PrimitiveTag.CONSTRAINT,  # what limits them
            PrimitiveTag.SIGNAL,  # how we detect them
        }


# ---------------------------------------------------------------------------
# Offer
# Decomposes to: GOAL + ACTION + OUTCOME + RESOURCE + CONSTRAINT
# ---------------------------------------------------------------------------


@dataclass
class Offer(DomainComposition):
    """What we sell — a promise of transformation backed by specific
    actions, constrained by what we require.
    """

    promise: str = ""
    deliverables: list[str] = field(default_factory=list)
    price: float = 0.0
    guarantee: str = ""
    requirements: list[str] = field(default_factory=list)

    def _primitive_tags(self) -> set[PrimitiveTag]:
        return {
            PrimitiveTag.GOAL,  # the transformation promised
            PrimitiveTag.ACTION,  # what we deliver
            PrimitiveTag.OUTCOME,  # the measurable result
            PrimitiveTag.RESOURCE,  # what it costs / requires
            PrimitiveTag.CONSTRAINT,  # conditions and guarantees
        }


# ---------------------------------------------------------------------------
# Channel
# Decomposes to: SIGNAL + ACTION + RESOURCE + CONSTRAINT
# ---------------------------------------------------------------------------


@dataclass
class Channel(DomainComposition):
    """How we reach the ICP — the medium, its costs, and its limits."""

    medium: str = ""
    cost_per_touch: float = 0.0
    capacity: str = ""
    rules: list[str] = field(default_factory=list)

    def _primitive_tags(self) -> set[PrimitiveTag]:
        return {
            PrimitiveTag.SIGNAL,  # where we broadcast / listen
            PrimitiveTag.ACTION,  # the outreach action
            PrimitiveTag.RESOURCE,  # cost and capacity
            PrimitiveTag.CONSTRAINT,  # platform rules, limits
        }


# ---------------------------------------------------------------------------
# Workflow
# Decomposes to: ACTION + STATE + CHANGE + TIME + RESOURCE + GOAL
# ---------------------------------------------------------------------------


@dataclass
class Workflow(DomainComposition):
    """A repeatable sequence of actions that moves state toward a goal."""

    steps: list[str] = field(default_factory=list)
    trigger: str = ""
    goal: str = ""
    estimated_duration: str = ""

    def _primitive_tags(self) -> set[PrimitiveTag]:
        return {
            PrimitiveTag.ACTION,  # the steps
            PrimitiveTag.STATE,  # before / after
            PrimitiveTag.CHANGE,  # the transitions
            PrimitiveTag.TIME,  # sequencing and duration
            PrimitiveTag.RESOURCE,  # what's consumed
            PrimitiveTag.GOAL,  # why we run it
        }


# ---------------------------------------------------------------------------
# KPI — Key Performance Indicator
# Decomposes to: OUTCOME + FEEDBACK + SIGNAL + GOAL + TIME
# ---------------------------------------------------------------------------


@dataclass
class KPI(DomainComposition):
    """A measurable signal that tells us whether we're moving toward
    or away from a goal over time.
    """

    metric: str = ""
    target: float = 0.0
    current: float = 0.0
    period: str = ""

    def _primitive_tags(self) -> set[PrimitiveTag]:
        return {
            PrimitiveTag.OUTCOME,  # what we measure
            PrimitiveTag.FEEDBACK,  # what it tells us
            PrimitiveTag.SIGNAL,  # the observable data point
            PrimitiveTag.GOAL,  # the target
            PrimitiveTag.TIME,  # measurement period
        }


# ---------------------------------------------------------------------------
# Role
# Decomposes to: ACTION + CONSTRAINT + RESOURCE + GOAL
# ---------------------------------------------------------------------------


@dataclass
class Role(DomainComposition):
    """A defined set of responsibilities, authorities, and objectives
    assigned to an agent (human or AI).
    """

    responsibilities: list[str] = field(default_factory=list)
    authority_boundary: list[str] = field(default_factory=list)
    objective: str = ""

    def _primitive_tags(self) -> set[PrimitiveTag]:
        return {
            PrimitiveTag.ACTION,  # what the role does
            PrimitiveTag.CONSTRAINT,  # authority limits
            PrimitiveTag.RESOURCE,  # what the role controls
            PrimitiveTag.GOAL,  # the role's objective
        }


# ---------------------------------------------------------------------------
# Registry of all domain compositions
# ---------------------------------------------------------------------------

DOMAIN_TYPES: dict[str, type[DomainComposition]] = {
    "icp": ICP,
    "offer": Offer,
    "channel": Channel,
    "workflow": Workflow,
    "kpi": KPI,
    "role": Role,
}


def _register_cross_domain() -> None:
    """Register LyfeOS and CreatorOS domain types into the global registry.

    Called at import time — new domains integrate automatically.
    """
    try:
        from core.domain.lyfe import LYFE_DOMAIN_TYPES

        DOMAIN_TYPES.update(LYFE_DOMAIN_TYPES)
    except ImportError:
        pass
    try:
        from core.domain.creator import CREATOR_DOMAIN_TYPES

        DOMAIN_TYPES.update(CREATOR_DOMAIN_TYPES)
    except ImportError:
        pass


_register_cross_domain()


__all__ = [
    "DomainComposition",
    "ICP",
    "Offer",
    "Channel",
    "Workflow",
    "KPI",
    "Role",
    "DOMAIN_TYPES",
]
