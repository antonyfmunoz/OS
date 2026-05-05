"""ContextBuilder — fault-isolated, priority-aware context assembly.

Extracted from the legacy umh/context_builder.py architecture.
Keeps the layered assembly, per-section fault isolation, token budget,
and source attribution. Drops all EOS-specific data sources.
"""

from __future__ import annotations

from typing import Any, Callable

from umh.context.budget import TokenBudget
from umh.context.types import ContextPriority, ContextResult, ContextSection


SectionProvider = Callable[[], ContextSection | None]


class ContextBuilder:
    """Assembles context from multiple fault-isolated section providers.

    Usage:
        builder = ContextBuilder(max_tokens=128_000)
        builder.add_section(ContextSection(name="identity", content="...", priority=CRITICAL))
        builder.add_provider("world", lambda: ContextSection(...))
        result = builder.build(user_prompt="What should I do?")
    """

    def __init__(self, max_tokens: int = 128_000) -> None:
        self._budget = TokenBudget(max_tokens)
        self._static_sections: list[ContextSection] = []
        self._providers: list[tuple[str, SectionProvider]] = []

    def add_section(self, section: ContextSection) -> None:
        self._static_sections.append(section)

    def add_provider(self, name: str, provider: SectionProvider) -> None:
        self._providers.append((name, provider))

    def build(
        self,
        user_prompt: str = "",
        *,
        extra_sections: list[ContextSection] | None = None,
    ) -> ContextResult:
        """Assemble all sections, apply budget, return result.

        Each provider is called in its own fault-isolation boundary.
        A failing provider is recorded in failed_sources but never
        prevents the build from completing.
        """
        sections: list[ContextSection] = list(self._static_sections)
        if extra_sections:
            sections.extend(extra_sections)

        failed_sources: list[str] = []

        for provider_name, provider_fn in self._providers:
            try:
                section = provider_fn()
                if section is not None and section.content:
                    sections.append(section)
            except Exception as exc:
                failed_sources.append(f"{provider_name}: {exc}")

        kept, dropped = self._budget.fit(sections)

        system_parts = [s.content for s in kept]
        system_prompt = "\n\n".join(system_parts)
        total_tokens = self._budget.estimate_tokens(
            system_prompt + "\n\n" + user_prompt
        )

        return ContextResult(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            sections_used=tuple(s.name for s in kept),
            sections_dropped=tuple(s.name for s in dropped),
            failed_sources=tuple(failed_sources),
            estimated_tokens=total_tokens,
            was_truncated=len(dropped) > 0,
        )
