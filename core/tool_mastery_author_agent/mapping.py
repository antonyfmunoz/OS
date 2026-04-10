"""Section → raw-capture evidence mapping.

The core truthfulness layer. Given a LoadedArtifact (raw HTML/text
captures), the mapper decides which of the 19 TME best_practices
sections have evidence in the captured material — and which do not.

Design constraints:
  1. NO LLM. Keyword scanning only. This is intentional: the output
     must be reproducible and impossible to hallucinate.
  2. "Evidence" = the section's keyword set matches somewhere in at
     least one raw capture. The match returns bounded excerpts, not
     paraphrase.
  3. If no keywords match, the section is honestly marked uncovered.
     We never promote weak signals to "sourced".
  4. Excerpts are bounded (hard cap) so that best_practices.md does
     not explode on large HTML captures.

The section list and their long-form canonical names come directly
from the research agent's TME_SECTIONS list. We keep that as the
source of truth so verifier + research + author stay aligned.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape

from .loader import LoadedArtifact, RawCapture

# Long-form canonical TME section names (match research_agent.artifact.TME_SECTIONS).
# The verifier accepts these via section_present() prefix matching — e.g.
# heading "## Pagination Patterns" satisfies required section "Pagination".
TME_SECTIONS: list[str] = [
    # Tier 1 — Technical Mastery
    "Authentication",
    "Core Operations with Exact Signatures",
    "Pagination Patterns",
    "Rate Limits",
    "Error Codes and Recovery",
    "SDK Idioms",
    "Anti-Patterns",
    "Data Model",
    "Webhooks and Events",
    "Limits",
    "Cost Model",
    "Version Pinning",
    # Tier 2 — Creator Intelligence
    "Design Intent and Tradeoffs",
    "Problem-Solution Map and Hidden Capabilities",
    "Operational Behavior and Edge Cases",
    "Ecosystem Position and Composition",
    "Trajectory and Evolution",
    "Conceptual Model and Solution Recipes",
    "Industry Expert and Cutting-Edge Usage",
]

# Keywords per section. Intentionally conservative — we would rather
# honestly mark "uncovered" than falsely claim coverage.
#
# A section's keyword set matches iff at least TWO distinct keywords
# from the set appear in the raw capture (case-insensitive). The
# two-hit rule prevents "Authentication" matching every HTML page
# that happens to include the word "login".
SECTION_KEYWORDS: dict[str, list[str]] = {
    "Authentication": [
        "authentication",
        "authorization",
        "api key",
        "api token",
        "bearer",
        "oauth",
        "access token",
        "integration token",
    ],
    "Core Operations with Exact Signatures": [
        "endpoint",
        "post ",
        "get ",
        "patch ",
        "delete ",
        "request body",
        "response",
        "api reference",
        "method",
    ],
    "Pagination Patterns": [
        "pagination",
        "page_size",
        "next_cursor",
        "start_cursor",
        "has_more",
        "cursor",
        "limit",
        "offset",
        "next page",
    ],
    "Rate Limits": [
        "rate limit",
        "rate-limit",
        "429",
        "too many requests",
        "requests per second",
        "throttle",
        "quota",
    ],
    "Error Codes and Recovery": [
        "error code",
        "status code",
        "400",
        "401",
        "403",
        "404",
        "500",
        "error object",
        "retry",
    ],
    "SDK Idioms": [
        "sdk",
        "client library",
        "python client",
        "javascript client",
        "install",
        "npm install",
        "pip install",
        "import",
    ],
    "Anti-Patterns": [
        "anti-pattern",
        "antipattern",
        "do not",
        "avoid",
        "deprecated",
        "not recommended",
        "common mistakes",
    ],
    "Data Model": [
        "object",
        "schema",
        "property",
        "properties",
        "database",
        "page object",
        "block object",
        "field",
    ],
    "Webhooks and Events": [
        "webhook",
        "event",
        "subscription",
        "callback url",
        "payload",
        "push notification",
    ],
    "Limits": [
        "limit",
        "maximum",
        "max ",
        "size limit",
        "character limit",
        "request limit",
        "bytes",
    ],
    "Cost Model": [
        "pricing",
        "price",
        "cost",
        "billing",
        "free tier",
        "paid plan",
        "usage-based",
        "credits",
    ],
    "Version Pinning": [
        "api version",
        "version header",
        "notion-version",
        "x-api-version",
        "versioning",
        "changelog",
    ],
    # Tier 2 sections are harder to ground in raw HTML. Keep keyword
    # sets narrow so we rarely falsely claim creator-intelligence
    # coverage — that content almost always requires human research.
    "Design Intent and Tradeoffs": [
        "design principle",
        "philosophy",
        "trade-off",
        "tradeoff",
        "why we built",
        "design decision",
    ],
    "Problem-Solution Map and Hidden Capabilities": [
        "use case",
        "example",
        "recipe",
        "pattern",
        "tutorial",
        "how to",
        "guide",
    ],
    "Operational Behavior and Edge Cases": [
        "edge case",
        "caveat",
        "gotcha",
        "known issue",
        "limitation",
        "behavior",
    ],
    "Ecosystem Position and Composition": [
        "integration",
        "marketplace",
        "ecosystem",
        "partner",
        "compose",
        "works with",
    ],
    "Trajectory and Evolution": [
        "roadmap",
        "changelog",
        "release notes",
        "deprecation",
        "migration",
        "upcoming",
    ],
    "Conceptual Model and Solution Recipes": [
        "concept",
        "mental model",
        "overview",
        "getting started",
        "quickstart",
    ],
    "Industry Expert and Cutting-Edge Usage": [
        "advanced",
        "expert",
        "best practice",
        "production",
        "scale",
    ],
}

# Hard bound on any single excerpt. Keeps best_practices.md truthful
# and reviewable instead of a dump of the upstream doc.
MAX_EXCERPT_CHARS = 600
MAX_EXCERPTS_PER_SECTION = 3
MIN_KEYWORD_HITS = 2

# Prose gate — a text block must meet ALL of these to be considered
# human-readable prose eligible for sourcing.
PROSE_MIN_CHARS = 80
PROSE_MIN_WORDS = 12
PROSE_MAX_SYMBOL_RATIO = 0.08  # punctuation/letter density
PROSE_MIN_LETTER_RATIO = 0.65  # letters+spaces / total
PROSE_MIN_SENTENCE_HINTS = 1  # . ! ? — at least one sentence terminator

# Excerpt gate — additionally enforced at extraction time.
MIN_EXCERPT_CHARS = 120

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]+")
_CODE_SYMBOL_CHARS = set("{}[]();=<>/\\|`~*&^%$#@+_")
_SENTENCE_HINT_RE = re.compile(r"[.!?](?:\s|$)")
_BLOCK_SPLIT_RE = re.compile(r"\n{2,}|(?<=[.!?])\s+(?=[A-Z])")


def _strip_html(text: str) -> str:
    """HTML-to-text preserving paragraph boundaries for block splitting.

    Sanitisation in loader.py has already removed scripts/styles and
    heavy code lines. Here we strip tags, unescape entities, and collapse
    only intra-line whitespace — newlines are kept so downstream code can
    chunk the text into prose blocks.
    """
    no_tags = _TAG_RE.sub("\n", text)
    unescaped = unescape(no_tags)
    return "\n".join(_WS_RE.sub(" ", line).strip() for line in unescaped.splitlines())


def is_prose_block(text: str) -> bool:
    """Heuristic: does this chunk look like human-readable prose?

    The goal is to reject code, JSON blobs, config snippets, nav-menu
    spam, and feature-flag arrays. False negatives are acceptable — we
    would rather mark a section uncovered than source it from garbage.
    """
    if not text:
        return False
    stripped = text.strip()
    if len(stripped) < PROSE_MIN_CHARS:
        return False

    words = stripped.split()
    if len(words) < PROSE_MIN_WORDS:
        return False

    total = len(stripped)
    letters = sum(1 for c in stripped if c.isalpha() or c == " ")
    symbols = sum(1 for c in stripped if c in _CODE_SYMBOL_CHARS)

    if letters / total < PROSE_MIN_LETTER_RATIO:
        return False
    if symbols / total > PROSE_MAX_SYMBOL_RATIO:
        return False

    sentence_hints = len(_SENTENCE_HINT_RE.findall(stripped))
    if sentence_hints < PROSE_MIN_SENTENCE_HINTS:
        return False

    # Average word length sanity — both ultra-short (nav) and ultra-long
    # (hashes/slugs) are suspicious.
    avg_word_len = sum(len(w) for w in words) / len(words)
    if avg_word_len < 3.0 or avg_word_len > 12.0:
        return False

    return True


def _split_prose_blocks(plain: str) -> list[str]:
    """Chunk stripped text into candidate prose blocks and keep the prose ones."""
    if not plain:
        return []
    candidates = _BLOCK_SPLIT_RE.split(plain)
    return [c.strip() for c in candidates if is_prose_block(c)]


@dataclass
class SectionEvidence:
    """Result of scanning the raw captures for one TME section.

    Phase 6 note: ``patterns`` carries structured signals (install
    commands, setup flows, schemas, workflows) extracted by the research
    agent. The author renderer prefers these over ``excerpts`` because
    they are higher-signal and map cleanly to concrete markdown
    primitives (code fences, ordered lists) rather than bulk prose.
    """

    section: str
    sourced: bool
    excerpts: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    raw_paths: list[str] = field(default_factory=list)
    matched_keywords: list[str] = field(default_factory=list)
    patterns: list[dict] = field(default_factory=list)


def _excerpt_from_block(block: str, keyword: str) -> str | None:
    """Return a bounded, sentence-aware excerpt from a prose block.

    The block has already passed ``is_prose_block``, so we don't need to
    defend against code here — just bound the length and require enough
    surrounding context that the reader can judge the match.
    """
    low = block.lower()
    idx = low.find(keyword.lower())
    if idx < 0:
        return None

    # Expand to surrounding sentence boundaries when possible.
    start = max(0, idx - MAX_EXCERPT_CHARS // 2)
    end = min(len(block), idx + MAX_EXCERPT_CHARS // 2)
    excerpt = block[start:end].strip()

    # Don't emit truncated-mid-token excerpts — trim to word boundaries.
    if start > 0 and not excerpt[:1].isspace():
        space = excerpt.find(" ")
        if 0 < space < 40:
            excerpt = excerpt[space + 1 :].lstrip()
    if end < len(block):
        space = excerpt.rfind(" ")
        if space > len(excerpt) - 40:
            excerpt = excerpt[:space].rstrip() + "…"

    if len(excerpt) < MIN_EXCERPT_CHARS:
        return None
    if len(excerpt) > MAX_EXCERPT_CHARS:
        excerpt = excerpt[:MAX_EXCERPT_CHARS].rstrip() + "…"
    # Final guard: if what we pulled fails the prose gate, drop it.
    if not is_prose_block(excerpt):
        return None
    return excerpt


def _scan_capture_for_section(
    capture: RawCapture, section: str, prose_blocks: list[str]
) -> tuple[set[str], list[str], int]:
    """Scan prose blocks of one capture for a section.

    Returns ``(matched_keywords, excerpts, blocks_with_hits)``.

    Locality rule: a keyword only counts if it appears *inside* a prose
    block (not in the raw HTML). The number of distinct blocks that
    contained at least one hit is reported so the outer loop can reject
    isolated single-block single-token matches.
    """
    kws = SECTION_KEYWORDS.get(section, [])
    matched: set[str] = set()
    excerpts: list[str] = []
    blocks_with_hits = 0
    for block in prose_blocks:
        low = block.lower()
        block_hits: list[str] = []
        for kw in kws:
            if kw.lower() in low:
                block_hits.append(kw)
        if not block_hits:
            continue
        blocks_with_hits += 1
        matched.update(block_hits)
        if len(excerpts) < MAX_EXCERPTS_PER_SECTION:
            # Use the first keyword hit in this block to anchor the excerpt.
            excerpt = _excerpt_from_block(block, block_hits[0])
            if excerpt:
                excerpts.append(excerpt)
    return matched, excerpts, blocks_with_hits


# Phase 5 — pattern-kind → TME section routing. Mirrors the table in
# core.tool_mastery_research_agent.extraction.PATTERN_SECTION_MAP. We copy
# the map here rather than import so the author agent stays independent
# of the research agent package at import time.
_PATTERN_SECTION_MAP: dict[str, str] = {
    # SDK Idioms ← install + setup flows
    "install_command": "SDK Idioms",
    "setup_flow": "SDK Idioms",
    "config_block": "SDK Idioms",
    "config_pattern": "SDK Idioms",
    # Core Operations ← API signatures / endpoints
    "function_signature": "Core Operations with Exact Signatures",
    "parameter_definitions": "Core Operations with Exact Signatures",
    "endpoints": "Core Operations with Exact Signatures",
    "api_objects": "Core Operations with Exact Signatures",
    # Data Model ← JSON schema fields
    "json_schema_fields": "Data Model",
    # Conceptual Model ← workflows + tutorials
    "stepwise_workflow": "Conceptual Model and Solution Recipes",
    "ordered_workflow": "Conceptual Model and Solution Recipes",
    "workflow_sequence": "Conceptual Model and Solution Recipes",
    "quickstart_flow": "Conceptual Model and Solution Recipes",
    "conceptual_explanation": "Conceptual Model and Solution Recipes",
    "tutorial_progression": "Conceptual Model and Solution Recipes",
    # Version Pinning ← version headers, constraints, dependencies
    "version_header": "Version Pinning",
    "version_constraint": "Version Pinning",
    "pinned_dependencies": "Version Pinning",
    "version_pin_guidance": "Version Pinning",
    # Design Intent ← rationale, comparisons, trade-offs
    "design_rationale": "Design Intent and Tradeoffs",
    "comparison_table": "Design Intent and Tradeoffs",
    "tradeoff_reasoning": "Design Intent and Tradeoffs",
    # Operational Behavior ← warnings, errors, retries, edge cases
    "warning_admonition": "Operational Behavior and Edge Cases",
    "error_handling_pattern": "Operational Behavior and Edge Cases",
    "retry_backoff_pattern": "Operational Behavior and Edge Cases",
    "edge_case_documentation": "Operational Behavior and Edge Cases",
}


def _apply_pattern_evidence(
    evidence: list[SectionEvidence],
    extracted_patterns: dict[str, list[dict]],
) -> list[SectionEvidence]:
    """Merge Phase-5 extracted patterns into section evidence.

    Structured patterns carry their own confidence + provenance from
    the research agent, so they count as sourced evidence even if the
    raw-capture keyword scan did not hit the 2-keyword threshold for a
    section. A pattern's excerpt is appended (bounded) and its URL added
    to the section's source list.

    Honesty boundary: we do NOT upgrade a section to sourced from
    low-confidence patterns alone. Only patterns with confidence
    ``medium`` or ``high`` contribute — these are the ones that passed
    the repeat-signal rule (≥2 occurrences OR structured container).
    """
    by_section = {ev.section: ev for ev in evidence}
    all_patterns = (
        list(extracted_patterns.get("usage") or [])
        + list(extracted_patterns.get("api") or [])
        + list(extracted_patterns.get("workflows") or [])
    )
    # Phase 6 — patterns are stored as first-class structured evidence
    # on each section (draft.py renders them differently from prose).
    # Rules enforced here:
    #   1. Drop low-confidence patterns outright.
    #   2. Drop patterns missing excerpt OR url (no grounding → no use).
    #   3. Dedupe within a section by (kind, excerpt).
    #   4. Cap per-section pattern count so one pathological source
    #      cannot dominate a section.
    PATTERNS_PER_SECTION_CAP = 5

    for p in all_patterns:
        conf = str(p.get("confidence", "low"))
        if conf == "low":
            continue
        kind = str(p.get("kind", ""))
        section = _PATTERN_SECTION_MAP.get(kind)
        if not section or section not in by_section:
            continue
        excerpt = str(p.get("excerpt", "")).strip()
        url = str(p.get("url", "")).strip()
        if not excerpt or not url:
            # Explicit grounding is required — no url means no
            # [SOURCE: ...] line in the rendered output.
            continue
        if len(excerpt) > MAX_EXCERPT_CHARS:
            excerpt = excerpt[:MAX_EXCERPT_CHARS].rstrip() + "…"

        ev = by_section[section]
        # Dedupe: same (kind, excerpt) from the same url is one signal.
        sig = (kind, excerpt[:200], url)
        existing_sigs = {
            (pp.get("kind"), str(pp.get("excerpt", ""))[:200], pp.get("url"))
            for pp in ev.patterns
        }
        if sig in existing_sigs:
            continue
        if len(ev.patterns) >= PATTERNS_PER_SECTION_CAP:
            continue

        ev.patterns.append(
            {
                "kind": kind,
                "excerpt": excerpt,
                "url": url,
                "confidence": conf,
                "occurrences": int(p.get("occurrences", 0) or 0),
                "structured": bool(p.get("structured", False)),
            }
        )
        # Structured patterns are, by construction, strong enough
        # evidence on their own — promote the section to sourced.
        ev.sourced = True
        if url not in ev.source_urls:
            ev.source_urls.append(url)
        marker = f"pattern:{kind}"
        if marker not in ev.matched_keywords:
            ev.matched_keywords.append(marker)
    return evidence


def map_sections(artifact: LoadedArtifact) -> list[SectionEvidence]:
    """Scan each section against all raw captures.

    A section is marked ``sourced=True`` only when its keyword set
    hits at least ``MIN_KEYWORD_HITS`` distinct keywords across the
    available captures. One-hit matches are treated as insufficient
    evidence — honest uncovered.
    """

    # Pre-strip + pre-chunk each capture once. Prose blocks are computed
    # from the sanitized capture (loader already removed scripts/styles);
    # mapping then only ever looks at blocks that pass is_prose_block.
    blocks_by_capture: list[tuple[RawCapture, list[str]]] = []
    for c in artifact.raw_captures:
        plain = _strip_html(c.text)
        blocks = _split_prose_blocks(plain)
        blocks_by_capture.append((c, blocks))

    evidence: list[SectionEvidence] = []
    for section in TME_SECTIONS:
        all_matched: set[str] = set()
        all_excerpts: list[str] = []
        hit_urls: list[str] = []
        hit_paths: list[str] = []
        total_hit_blocks = 0
        for capture, blocks in blocks_by_capture:
            matched, excerpts, hit_blocks = _scan_capture_for_section(
                capture, section, blocks
            )
            if not matched or not excerpts:
                # Must have at least one qualifying excerpt — prevents
                # keyword-only promotion from tokens that didn't land in
                # recoverable prose context.
                continue
            all_matched.update(matched)
            total_hit_blocks += hit_blocks
            if capture.url not in hit_urls:
                hit_urls.append(capture.url)
                hit_paths.append(capture.raw_path)
            for ex in excerpts:
                if len(all_excerpts) < MAX_EXCERPTS_PER_SECTION:
                    all_excerpts.append(ex)

        # Locality rule: need ≥2 distinct keyword hits AND at least one
        # recoverable prose excerpt. A single keyword — or two keywords
        # that only ever appeared inside the same short block — is not
        # enough to claim section coverage.
        sourced = (
            len(all_matched) >= MIN_KEYWORD_HITS
            and len(all_excerpts) >= 1
            and total_hit_blocks >= 1
        )
        evidence.append(
            SectionEvidence(
                section=section,
                sourced=sourced,
                excerpts=all_excerpts if sourced else [],
                source_urls=hit_urls if sourced else [],
                raw_paths=hit_paths if sourced else [],
                matched_keywords=sorted(all_matched),
            )
        )

    # Phase 5 — fold structured patterns from the research agent into
    # the evidence list. Patterns can upgrade an uncovered section to
    # sourced because they carry their own provenance + confidence.
    if artifact.extracted_patterns:
        evidence = _apply_pattern_evidence(evidence, artifact.extracted_patterns)
    return evidence
