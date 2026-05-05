"""CreatorOS domain compositions — content creation structures.

Maps content-creation concepts to L0 primitives following the same
pattern as EOS business compositions.

Usage:
    from core.domain.creator import Content, Audience, Platform, Engagement

    content = Content(name="ig-reel-001", format="short_video", topic="structure over discipline")
    print(content.to_primitives())  # {ACTION, GOAL, RESOURCE, TIME, SIGNAL, OUTCOME}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.domain.eos import DomainComposition
from core.primitives import PrimitiveTag


# ---------------------------------------------------------------------------
# Content
# Decomposes to: ACTION + GOAL + RESOURCE + TIME + SIGNAL + OUTCOME
# ---------------------------------------------------------------------------


@dataclass
class Content(DomainComposition):
    """A piece of content to be created and distributed."""

    format: str = ""  # "short_video", "long_form", "carousel", "tweet", etc.
    topic: str = ""
    hook: str = ""
    call_to_action: str = ""
    estimated_time: str = ""

    def _primitive_tags(self) -> set[PrimitiveTag]:
        return {
            PrimitiveTag.ACTION,  # creation is an action
            PrimitiveTag.GOAL,  # what the content achieves
            PrimitiveTag.RESOURCE,  # time/effort to create
            PrimitiveTag.TIME,  # publish timing
            PrimitiveTag.SIGNAL,  # the content itself is a signal
            PrimitiveTag.OUTCOME,  # measurable performance
        }


# ---------------------------------------------------------------------------
# Audience
# Decomposes to: STATE + SIGNAL + GOAL + CONSTRAINT + FEEDBACK
# ---------------------------------------------------------------------------


@dataclass
class Audience(DomainComposition):
    """A defined audience segment with known characteristics and signals."""

    segment: str = ""
    size: int = 0
    signals: list[str] = field(default_factory=list)
    pain_points: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)

    def _primitive_tags(self) -> set[PrimitiveTag]:
        return {
            PrimitiveTag.STATE,  # who they are
            PrimitiveTag.SIGNAL,  # how we detect/reach them
            PrimitiveTag.GOAL,  # what they want
            PrimitiveTag.CONSTRAINT,  # what limits them
            PrimitiveTag.FEEDBACK,  # how they respond to content
        }


# ---------------------------------------------------------------------------
# Platform
# Decomposes to: RESOURCE + CONSTRAINT + SIGNAL + ACTION + TIME
# ---------------------------------------------------------------------------


@dataclass
class Platform(DomainComposition):
    """A distribution platform with its rules, costs, and reach."""

    platform_name: str = ""
    reach: int = 0
    rules: list[str] = field(default_factory=list)
    cost: float = 0.0
    best_times: list[str] = field(default_factory=list)

    def _primitive_tags(self) -> set[PrimitiveTag]:
        return {
            PrimitiveTag.RESOURCE,  # platform as a distribution resource
            PrimitiveTag.CONSTRAINT,  # platform rules and limits
            PrimitiveTag.SIGNAL,  # platform as signal channel
            PrimitiveTag.ACTION,  # posting/distributing
            PrimitiveTag.TIME,  # timing and frequency constraints
        }


# ---------------------------------------------------------------------------
# Engagement
# Decomposes to: OUTCOME + FEEDBACK + SIGNAL + STATE + CHANGE
# ---------------------------------------------------------------------------


@dataclass
class Engagement(DomainComposition):
    """Engagement metrics and patterns for content performance."""

    metric_type: str = ""  # "likes", "comments", "shares", "saves", "replies"
    value: float = 0.0
    benchmark: float = 0.0
    trend: str = ""  # "up", "down", "flat"

    def _primitive_tags(self) -> set[PrimitiveTag]:
        return {
            PrimitiveTag.OUTCOME,  # the measurable result
            PrimitiveTag.FEEDBACK,  # what it tells us
            PrimitiveTag.SIGNAL,  # the data signal
            PrimitiveTag.STATE,  # current engagement state
            PrimitiveTag.CHANGE,  # trend / movement
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

CREATOR_DOMAIN_TYPES: dict[str, type[DomainComposition]] = {
    "content": Content,
    "audience": Audience,
    "platform": Platform,
    "engagement": Engagement,
}


__all__ = [
    "Content",
    "Audience",
    "Platform",
    "Engagement",
    "CREATOR_DOMAIN_TYPES",
]
