"""Context types — immutable value objects for the context composition layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class ContextPriority(IntEnum):
    """Section priority for token budget allocation.

    Lower value = higher priority = last to be truncated.
    Mirrors the legacy ContextBuilder's implicit ordering but makes it explicit.
    """

    CRITICAL = 1
    HIGH = 2
    STANDARD = 3
    LOW = 4
    SUPPLEMENTARY = 5


@dataclass(frozen=True)
class ContextSection:
    """A single section of assembled context.

    Each section is independently provided and fault-isolated.
    The builder never raises on a bad section — it records the failure
    and continues with the remaining sections.
    """

    name: str
    content: str
    priority: ContextPriority = ContextPriority.STANDARD
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def estimated_tokens(self) -> int:
        return len(self.content) // 4


@dataclass(frozen=True)
class ContextResult:
    """Output of ContextBuilder.build().

    Provides system_prompt / user_prompt separation for LLM routing
    and a flat prompt for non-LLM routing.
    """

    system_prompt: str
    user_prompt: str
    sections_used: tuple[str, ...]
    sections_dropped: tuple[str, ...]
    failed_sources: tuple[str, ...]
    estimated_tokens: int
    was_truncated: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def flat_prompt(self) -> str:
        parts = [p for p in (self.system_prompt, self.user_prompt) if p]
        return "\n\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "system_prompt_length": len(self.system_prompt),
            "user_prompt_length": len(self.user_prompt),
            "sections_used": list(self.sections_used),
            "sections_dropped": list(self.sections_dropped),
            "failed_sources": list(self.failed_sources),
            "estimated_tokens": self.estimated_tokens,
            "was_truncated": self.was_truncated,
        }
