"""Draft authored section content from SectionEvidence.

Takes the truth-only output of mapping.py and renders it as markdown
ready to be written into SKILL.md / best_practices.md. Honest
placeholders for uncovered sections.

No synthesis. No prose generation. Just structured rendering of
bounded excerpts + provenance markers.
"""

from __future__ import annotations

from .mapping import SectionEvidence, TME_SECTIONS
from .models import SectionDraft


UNCOVERED_PLACEHOLDER = (
    "⚠ **Uncovered.** The research captures for this tool did not "
    "contain sufficient signal for this section. Requires manual "
    "research from upstream docs, creator content, or production "
    "experience before this section can be considered mastered."
)


def _render_sourced_content(ev: SectionEvidence) -> str:
    """Render markdown for a section with real evidence."""
    lines: list[str] = []
    lines.append(
        "_Source-grounded excerpts from fetched documentation. "
        "Keyword matches: "
        + ", ".join(f"`{k}`" for k in ev.matched_keywords)
        + "._"
    )
    lines.append("")
    for i, excerpt in enumerate(ev.excerpts, start=1):
        lines.append(f"**Excerpt {i}:**")
        lines.append("")
        lines.append("> " + excerpt.replace("\n", "\n> "))
        lines.append("")
    lines.append("**Sources:**")
    for url in ev.source_urls:
        lines.append(f"- {url}")
    lines.append("")
    lines.append(
        "> _Authored by tool_mastery_author_agent from source-grounded "
        "excerpts. Human review recommended before treating as "
        "creator-level mastery._"
    )
    return "\n".join(lines)


def _render_uncovered_content(ev: SectionEvidence) -> str:
    """Render honest placeholder for a section with no evidence."""
    hints = ""
    if ev.matched_keywords:
        hints = (
            "\n\n_Weak signals observed (below 2-hit threshold): "
            + ", ".join(f"`{k}`" for k in ev.matched_keywords)
            + "._"
        )
    return UNCOVERED_PLACEHOLDER + hints


def build_drafts(evidence: list[SectionEvidence]) -> list[SectionDraft]:
    """Convert every piece of evidence into a SectionDraft."""
    drafts: list[SectionDraft] = []
    for ev in evidence:
        if ev.sourced:
            drafts.append(
                SectionDraft(
                    section=ev.section,
                    content=_render_sourced_content(ev),
                    sourced=True,
                    source_urls=list(ev.source_urls),
                    raw_paths=list(ev.raw_paths),
                    rationale=f"{len(ev.matched_keywords)} keyword hits across {len(ev.source_urls)} source(s)",
                )
            )
        else:
            drafts.append(
                SectionDraft(
                    section=ev.section,
                    content=_render_uncovered_content(ev),
                    sourced=False,
                    rationale=(
                        "no keywords matched"
                        if not ev.matched_keywords
                        else f"only {len(ev.matched_keywords)} weak signal(s), below 2-hit threshold"
                    ),
                )
            )
    return drafts


def render_best_practices(
    tool_slug: str,
    display_name: str,
    drafts: list[SectionDraft],
    generated_at: str,
) -> str:
    """Render a complete best_practices.md from drafts.

    The output satisfies the verifier's 19-section requirement by
    always emitting all TME_SECTIONS as H2 headings in canonical
    order. Uncovered sections contain honest placeholders, not
    fabricated prose.
    """
    by_section = {d.section: d for d in drafts}
    lines: list[str] = []
    lines.append(f"# {display_name} — Creator-Level Best Practices")
    lines.append("")
    lines.append(
        f"_Drafted by tool_mastery_author_agent at {generated_at}._"
    )
    lines.append("")
    lines.append(
        "This document is source-grounded. Every **Sourced** section "
        "contains bounded excerpts from fetched official documentation "
        "and a list of source URLs. Every **Uncovered** section is "
        "honestly marked and must be filled by human research before "
        "the tool can be considered at creator-level mastery."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("# Tier 1 — Technical Mastery")
    lines.append("")
    for section in TME_SECTIONS[:12]:
        draft = by_section.get(section)
        badge = "Sourced" if (draft and draft.sourced) else "Uncovered"
        lines.append(f"## {section}")
        lines.append("")
        lines.append(f"**Status:** {badge}")
        lines.append("")
        if draft:
            lines.append(draft.content)
        else:
            lines.append(UNCOVERED_PLACEHOLDER)
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("# Tier 2 — Creator Intelligence")
    lines.append("")
    for section in TME_SECTIONS[12:]:
        draft = by_section.get(section)
        badge = "Sourced" if (draft and draft.sourced) else "Uncovered"
        lines.append(f"## {section}")
        lines.append("")
        lines.append(f"**Status:** {badge}")
        lines.append("")
        if draft:
            lines.append(draft.content)
        else:
            lines.append(UNCOVERED_PLACEHOLDER)
        lines.append("")
    return "\n".join(lines)


def render_skill_body(
    tool_slug: str,
    display_name: str,
    drafts: list[SectionDraft],
) -> str:
    """Render the body (after frontmatter) for a freshly scaffolded SKILL.md.

    Only used when reconcile.py decides to populate a scaffold's
    SKILL.md body from scratch. Existing high-quality SKILL.md files
    are preserved — see reconcile.should_populate_skill_md.
    """
    by_section = {d.section: d for d in drafts}
    auth = by_section.get("Authentication")

    lines: list[str] = []
    lines.append(f"# Tool: {display_name}")
    lines.append("")
    lines.append("## What This Tool Does")
    lines.append("")
    lines.append(
        f"_Drafted by tool_mastery_author_agent from source-grounded "
        f"research. This is a scaffold — flesh out with EOS-specific "
        f"integration details as you wire {display_name} into the "
        f"system._"
    )
    lines.append("")
    lines.append("## Authentication")
    lines.append("")
    if auth and auth.sourced:
        lines.append(auth.content)
    else:
        lines.append(UNCOVERED_PLACEHOLDER)
    lines.append("")
    lines.append("## Quick Reference")
    lines.append("")
    lines.append(
        "See `references/best_practices.md` for the full "
        "source-grounded section breakdown across all 19 TME "
        "mastery sections."
    )
    lines.append("")
    lines.append("## Gotchas")
    lines.append("")
    lines.append(
        "_No production gotchas recorded yet. This section compounds "
        "over time as real failures are encountered in EOS._"
    )
    lines.append("")
    return "\n".join(lines)
