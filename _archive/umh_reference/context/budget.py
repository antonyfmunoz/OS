"""Token budget — priority-based truncation for context sections."""

from __future__ import annotations

from umh.context.types import ContextPriority, ContextSection


class TokenBudget:
    """Manages token allocation across context sections.

    When total tokens exceed max_tokens, drops lowest-priority sections
    first. Within the same priority, drops the largest section first.
    """

    def __init__(self, max_tokens: int = 128_000) -> None:
        self._max_tokens = max(1, max_tokens)

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    def fit(
        self, sections: list[ContextSection]
    ) -> tuple[list[ContextSection], list[ContextSection]]:
        """Return (kept, dropped) sections that fit within the token budget.

        Sections are sorted by priority (ascending = highest priority first).
        When budget is exceeded, the lowest-priority sections are dropped.
        Ties within the same priority are broken by largest-first.
        """
        if not sections:
            return ([], [])

        sorted_sections = sorted(
            sections,
            key=lambda s: (s.priority.value, s.estimated_tokens),
        )

        kept: list[ContextSection] = []
        dropped: list[ContextSection] = []
        tokens_used = 0

        for section in sorted_sections:
            section_tokens = section.estimated_tokens
            if tokens_used + section_tokens <= self._max_tokens:
                kept.append(section)
                tokens_used += section_tokens
            else:
                dropped.append(section)

        return (kept, dropped)

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4
