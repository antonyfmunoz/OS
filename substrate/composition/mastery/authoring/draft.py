"""Draft authored section content from SectionEvidence.

Author Intelligence. Takes the evidence output of mapping.py
and renders it as markdown. Pattern-priority: structured signals (install
commands, setup flows, JSON schema fields, workflow sequences) are
rendered as concrete markdown primitives (code fences, ordered lists),
not paraphrased into prose. Prose excerpts are a fallback, not the
default.

Every rendered section carries explicit grounding: a `[SOURCE: url]`
marker, the excerpt used, and the pattern kind (when applicable). No
implicit claims. No synthesis. No LLM.
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

# Pattern kinds that are literal shell/code and should be rendered as
# a code fence (not a blockquote). Everything else gets blockquoted.
_CODE_FENCE_KINDS = {
    "install_command",
    "config_block",
    "config_pattern",
    "function_signature",
    "endpoints",
    "api_objects",
    "json_schema_fields",
    "version_header",
    "version_constraint",
    "pinned_dependencies",
    "error_handling_pattern",
}

# Pattern kinds that represent ordered flows — render as a numbered list
# when the excerpt has multiple newline-separated lines.
_ORDERED_KINDS = {
    "setup_flow",
    "stepwise_workflow",
    "ordered_workflow",
    "workflow_sequence",
    "quickstart_flow",
    "tutorial_progression",
}

# Human labels for pattern kinds — shown beside the [SOURCE: …] marker
# so readers can see at a glance *why* this excerpt was promoted.
_PATTERN_LABELS: dict[str, str] = {
    "install_command": "install command",
    "setup_flow": "setup flow",
    "config_block": "config block",
    "config_pattern": "config pattern",
    "function_signature": "function signature",
    "parameter_definitions": "parameter definitions",
    "endpoints": "endpoint",
    "api_objects": "API object",
    "json_schema_fields": "JSON schema fields",
    "stepwise_workflow": "stepwise workflow",
    "ordered_workflow": "ordered workflow",
    "workflow_sequence": "workflow sequence",
    # Code/config extraction kinds
    "version_header": "version header",
    "version_constraint": "version constraint",
    "pinned_dependencies": "pinned dependencies",
    "version_pin_guidance": "version pin guidance",
    "design_rationale": "design rationale",
    "comparison_table": "comparison table",
    "tradeoff_reasoning": "trade-off reasoning",
    "warning_admonition": "warning / caveat",
    "error_handling_pattern": "error handling",
    "retry_backoff_pattern": "retry / backoff",
    "edge_case_documentation": "edge case",
    "quickstart_flow": "quickstart flow",
    "conceptual_explanation": "conceptual explanation",
    "tutorial_progression": "tutorial progression",
}


def _label_for(kind: str) -> str:
    return _PATTERN_LABELS.get(kind, kind.replace("_", " "))


def _render_ordered_list(excerpt: str) -> list[str]:
    """Turn a multi-line excerpt into a markdown ordered list.

    If the excerpt is a single line we fall back to a blockquote so the
    output does not lie about the structure of the source material.
    """
    lines = [ln.strip().lstrip("-*•").strip() for ln in excerpt.splitlines()]
    lines = [ln for ln in lines if ln]
    if len(lines) < 2:
        return ["> " + excerpt.replace("\n", " ")]
    out: list[str] = []
    for i, ln in enumerate(lines, start=1):
        out.append(f"{i}. {ln}")
    return out


def _render_pattern(pattern: dict) -> list[str]:
    """Render a single structured pattern as markdown lines.

    Grounding contract: every pattern block starts with a
    `[SOURCE: url]` line and names its pattern kind, so the reader can
    see both the evidence and the provenance at once.
    """
    kind = str(pattern.get("kind", ""))
    excerpt = str(pattern.get("excerpt", "")).strip()
    url = str(pattern.get("url", ""))
    conf = str(pattern.get("confidence", "medium"))
    occ = int(pattern.get("occurrences", 0) or 0)
    label = _label_for(kind)

    header = (
        f"**{label.title()}** — `[SOURCE: {url}]`  "
        f"_(confidence: {conf}" + (f", {occ} occurrences" if occ else "") + ")_"
    )

    body: list[str] = []
    if kind in _CODE_FENCE_KINDS:
        body.append("```")
        body.append(excerpt)
        body.append("```")
    elif kind in _ORDERED_KINDS:
        body.extend(_render_ordered_list(excerpt))
    else:
        # Default: blockquote the excerpt so it cannot be mistaken for
        # agent-authored prose.
        body.append("> " + excerpt.replace("\n", "\n> "))

    return [header, ""] + body + [""]


def _render_prose_excerpt(excerpt: str, index: int) -> list[str]:
    """Render a raw-capture prose excerpt as a bounded blockquote."""
    return [
        f"**Excerpt {index}:**",
        "",
        "> " + excerpt.replace("\n", "\n> "),
        "",
    ]


def _looks_marketing(text: str) -> bool:
    """Detect marketing/fluff phrases that should be rejected.

    Quality constraint: generic summaries and marketing language
    are not mastery signal. We prefer concrete patterns over vague
    prose. This gate catches the most obvious offenders without trying
    to be an LLM.
    """
    low = text.lower()
    fluff_markers = (
        "world-class",
        "best-in-class",
        "cutting-edge",
        "industry-leading",
        "revolutionary",
        "game-changing",
        "seamlessly",
        "unlock the power",
        "empower",
        "leverage",
    )
    hits = sum(1 for m in fluff_markers if m in low)
    return hits >= 2


def _render_sourced_content(ev: SectionEvidence) -> tuple[str, str, int]:
    """Render markdown for a section with real evidence.

    Returns ``(markdown, grounding_label, pattern_count)`` so the caller
    can populate SectionDraft stats without re-scanning the evidence.
    """
    lines: list[str] = []
    grounding = "uncovered"
    pattern_count = len(ev.patterns)

    # ---- Pattern-priority block -------------------------------------
    if ev.patterns:
        lines.append(
            f"_Grounded in {pattern_count} structured pattern(s) extracted "
            "from the raw research captures. Patterns are preferred over "
            "prose because they carry their own provenance and confidence._"
        )
        lines.append("")
        for pattern in ev.patterns:
            lines.extend(_render_pattern(pattern))
        grounding = "pattern"

    # ---- Prose fallback ---------------------------------------------
    # Only include prose excerpts when we have no patterns, or when the
    # prose adds genuinely new URLs (controlled multi-source synthesis).
    prose_excerpts = [e for e in ev.excerpts if not _looks_marketing(e)]
    pattern_urls = {p.get("url") for p in ev.patterns}
    prose_urls_new = [u for u in ev.source_urls if u not in pattern_urls]

    include_prose = False
    if prose_excerpts:
        if not ev.patterns:
            include_prose = True
        elif prose_urls_new:
            # Multi-source synthesis: prose adds a distinct URL not
            # already covered by a pattern. This is allowed because
            # we still ground each excerpt against its own source.
            include_prose = True

    if include_prose:
        if ev.patterns:
            lines.append("---")
            lines.append("")
            lines.append(
                "_Additional prose context from independent sources "
                "(cross-referenced to increase section coverage)._"
            )
            lines.append("")
            grounding = "mixed"
        else:
            lines.append(
                "_Source-grounded excerpts from fetched documentation. "
                "Keyword matches: "
                + ", ".join(
                    f"`{k}`"
                    for k in ev.matched_keywords
                    if not k.startswith("pattern:")
                )
                + "._"
            )
            lines.append("")
            grounding = "prose"
        for i, excerpt in enumerate(prose_excerpts, start=1):
            lines.extend(_render_prose_excerpt(excerpt, i))

    # ---- Explicit source list ---------------------------------------
    if ev.source_urls:
        lines.append("**Sources:**")
        for url in ev.source_urls:
            lines.append(f"- {url}")
        lines.append("")

    lines.append(
        "> _Authored by tool_mastery_author_agent with pattern-priority "
        "rendering. Human review recommended before treating as "
        "creator-level mastery._"
    )

    # Grounding can be "uncovered" here only if we had neither patterns
    # nor usable prose — in that case the caller should have routed
    # this section through _render_uncovered_content instead.
    return "\n".join(lines), grounding, pattern_count


def _render_uncovered_content(ev: SectionEvidence) -> str:
    """Render honest placeholder for a section with no evidence."""
    hints = ""
    weak = [k for k in ev.matched_keywords if not k.startswith("pattern:")]
    if weak:
        hints = (
            "\n\n_Weak signals observed (below 2-hit threshold): "
            + ", ".join(f"`{k}`" for k in weak)
            + "._"
        )
    return UNCOVERED_PLACEHOLDER + hints


def _has_usable_evidence(ev: SectionEvidence) -> bool:
    """Section is sourced AND has at least one pattern or non-fluff excerpt."""
    if not ev.sourced:
        return False
    if ev.patterns:
        return True
    return any(not _looks_marketing(e) for e in ev.excerpts)


def build_drafts(evidence: list[SectionEvidence]) -> list[SectionDraft]:
    """Convert every piece of evidence into a SectionDraft.

    Honest-fallback rule: a section with zero patterns AND no
    non-marketing prose remains uncovered even if ``ev.sourced`` is
    True. We do not force completion.
    """
    drafts: list[SectionDraft] = []
    for ev in evidence:
        if _has_usable_evidence(ev):
            content, grounding, pcount = _render_sourced_content(ev)
            drafts.append(
                SectionDraft(
                    section=ev.section,
                    content=content,
                    sourced=True,
                    source_urls=list(ev.source_urls),
                    raw_paths=list(ev.raw_paths),
                    rationale=(
                        f"{pcount} pattern(s), "
                        f"{len([e for e in ev.excerpts if not _looks_marketing(e)])} prose excerpt(s), "
                        f"{len(ev.source_urls)} source(s)"
                    ),
                    grounding=grounding,
                    pattern_count=pcount,
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
                        else "evidence was below confidence threshold or failed quality gate"
                    ),
                    grounding="uncovered",
                    pattern_count=0,
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
    lines.append(f"_Drafted by tool_mastery_author_agent at {generated_at}._")
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
        badge = _status_badge(draft)
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
        badge = _status_badge(draft)
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


def _status_badge(draft: SectionDraft | None) -> str:
    """Render a status badge that tells the reader *how* it was sourced."""
    if draft is None or not draft.sourced:
        return "Uncovered"
    if draft.grounding == "pattern":
        return f"Sourced (pattern × {draft.pattern_count})"
    if draft.grounding == "mixed":
        return f"Sourced (pattern × {draft.pattern_count} + prose)"
    if draft.grounding == "prose":
        return "Sourced (prose)"
    return "Sourced"


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
