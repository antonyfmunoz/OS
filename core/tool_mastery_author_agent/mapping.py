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

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(text: str) -> str:
    """Crude HTML-to-text. Good enough for keyword search + excerpting.

    We intentionally avoid pulling in BeautifulSoup — keyword scanning
    is resilient to imperfect stripping, and the raw captures are
    already stored verbatim for audit.
    """
    no_tags = _TAG_RE.sub(" ", text)
    return _WS_RE.sub(" ", unescape(no_tags)).strip()


@dataclass
class SectionEvidence:
    """Result of scanning the raw captures for one TME section."""

    section: str
    sourced: bool
    excerpts: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    raw_paths: list[str] = field(default_factory=list)
    matched_keywords: list[str] = field(default_factory=list)


def _find_excerpt(
    plain: str, keyword: str, window: int = 280
) -> str | None:
    """Return a bounded excerpt around the first case-insensitive match."""
    idx = plain.lower().find(keyword.lower())
    if idx < 0:
        return None
    start = max(0, idx - window // 2)
    end = min(len(plain), idx + window // 2)
    excerpt = plain[start:end].strip()
    if len(excerpt) > MAX_EXCERPT_CHARS:
        excerpt = excerpt[:MAX_EXCERPT_CHARS].rstrip() + "…"
    return excerpt


def _scan_capture_for_section(
    capture: RawCapture, section: str, plain: str
) -> tuple[list[str], list[str]]:
    """Return (matched_keywords, excerpts) for a single capture/section."""
    lowered = plain.lower()
    kws = SECTION_KEYWORDS.get(section, [])
    matched: list[str] = []
    excerpts: list[str] = []
    for kw in kws:
        if kw.lower() in lowered:
            matched.append(kw)
            if len(excerpts) < MAX_EXCERPTS_PER_SECTION:
                excerpt = _find_excerpt(plain, kw)
                if excerpt:
                    excerpts.append(excerpt)
    return matched, excerpts


def map_sections(artifact: LoadedArtifact) -> list[SectionEvidence]:
    """Scan each section against all raw captures.

    A section is marked ``sourced=True`` only when its keyword set
    hits at least ``MIN_KEYWORD_HITS`` distinct keywords across the
    available captures. One-hit matches are treated as insufficient
    evidence — honest uncovered.
    """

    # Pre-strip each capture once to avoid N*M HTML stripping.
    plain_by_capture: list[tuple[RawCapture, str]] = [
        (c, _strip_html(c.text)) for c in artifact.raw_captures
    ]

    evidence: list[SectionEvidence] = []
    for section in TME_SECTIONS:
        all_matched: set[str] = set()
        all_excerpts: list[str] = []
        hit_urls: list[str] = []
        hit_paths: list[str] = []
        for capture, plain in plain_by_capture:
            matched, excerpts = _scan_capture_for_section(capture, section, plain)
            if not matched:
                continue
            all_matched.update(matched)
            if capture.url not in hit_urls:
                hit_urls.append(capture.url)
                hit_paths.append(capture.raw_path)
            for ex in excerpts:
                if len(all_excerpts) < MAX_EXCERPTS_PER_SECTION:
                    all_excerpts.append(ex)
        sourced = len(all_matched) >= MIN_KEYWORD_HITS
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
    return evidence
