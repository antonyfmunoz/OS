"""Source quality scoring for the Tool Mastery Research Agent.

Two jobs, one module:

1. **Pre-fetch scoring** — classify a candidate source as HIGH or LOW
   signal *before* we spend a fetch. High signal = URLs that historically
   contain dense technical prose (official docs, API references, GitHub
   repos, developer portals). Low signal = landing pages, marketing
   homepages, generic vendor roots, search result pages.

2. **Post-fetch signal measurement** — after a source is fetched, measure
   the density of human-readable technical prose in the captured body.
   Sources that don't clear the bar are dropped so they never reach the
   Author Agent.

Design constraints:
    - Pure functions, no network, no LLM.
    - Shared prose detector with the Author Agent (loader.sanitize_text +
      mapping.is_prose_block) so the research agent and the author agent
      agree on what counts as "usable".
    - Honest: we'd rather discard a weak source than promote it.

The principle encoded here: *find better information, not more*.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable
from urllib.parse import urlparse

from .models import SourceRef, SourceTier


# ---------------------------------------------------------------------------
# Signal tiers
# ---------------------------------------------------------------------------

SIGNAL_HIGH = "high"
SIGNAL_MEDIUM = "medium"
SIGNAL_LOW = "low"

# Host pattern families. Lowered URL is matched against each pattern.
# High-signal patterns are CANONICAL dev surfaces: documentation sites,
# API references, developer portals, GitHub repos (not search), language
# package indexes.
_HIGH_HOST_PREFIXES: tuple[str, ...] = (
    "docs.",
    "developer.",
    "developers.",
    "api.",
    "reference.",
    "help.",  # some vendors put API guides here
)

_HIGH_HOST_SUFFIXES: tuple[str, ...] = (
    ".readthedocs.io",
    ".readthedocs.org",
    ".github.io",
    ".gitbook.io",
    ".mintlify.com",
    ".netlify.app",  # often hosts docs
)

# Exact host matches that are always high signal.
_HIGH_HOST_EXACT: frozenset[str] = frozenset(
    {
        "pypi.org",
        "www.npmjs.com",
        "npmjs.com",
        "crates.io",
        "pkg.go.dev",
        "rubygems.org",
        "hexdocs.pm",
        # GitHub raw file endpoint — Phase 1 repo extractor pins to
        # a commit SHA and pulls README/docs/examples from here.
        "raw.githubusercontent.com",
    }
)

# Path segments that, when present on a non-docs host, still indicate a
# technical surface (e.g. github.com/<owner>/<repo> or example.com/docs).
_HIGH_PATH_HINTS: tuple[str, ...] = (
    "/docs",
    "/documentation",
    "/reference",
    "/api",
    "/developers",
    "/developer",
    "/guides",
    "/readme",
    "/wiki",
)

# Low-signal exact host matches — generic search / landing surfaces.
_LOW_HOST_EXACT: frozenset[str] = frozenset(
    {
        "www.google.com",
        "google.com",
        "www.bing.com",
        "bing.com",
        "duckduckgo.com",
        "www.reddit.com",
        "reddit.com",
        "medium.com",
        "x.com",
        "twitter.com",
        "www.facebook.com",
        "www.linkedin.com",
        "www.youtube.com",
    }
)

# Low-signal path hints — these are search / aggregator / marketing
# surfaces even when the host itself is neutral.
_LOW_PATH_HINTS: tuple[str, ...] = (
    "/search",
    "/pricing",
    "/plans",
    "/blog/",  # marketing blog index, not deep-dive
    "/about",
    "/contact",
    "/careers",
    "/press",
    "/legal",
    "/privacy",
    "/terms",
)


def _split_host(url: str) -> tuple[str, str]:
    """Return (host, path) lowercased. Missing components return empty strings."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return "", ""
    return (parsed.netloc or "").lower(), (parsed.path or "").lower()


def score_source(ref: SourceRef) -> str:
    """Classify a candidate source as high / medium / low signal.

    The scoring is intentionally coarse. Tiebreakers go to *low* —
    we'd rather deprioritize an honest high-signal source than let a
    marketing page through.
    """

    host, path = _split_host(ref.url)
    if not host:
        return SIGNAL_LOW

    # Explicit low-signal hosts (search engines, social) trump everything.
    if host in _LOW_HOST_EXACT:
        return SIGNAL_LOW

    # Exact high-signal package indexes.
    if host in _HIGH_HOST_EXACT:
        return SIGNAL_HIGH

    # Host prefix / suffix patterns.
    if any(host.startswith(p) for p in _HIGH_HOST_PREFIXES):
        return SIGNAL_HIGH
    if any(host.endswith(s) for s in _HIGH_HOST_SUFFIXES):
        return SIGNAL_HIGH

    # GitHub: a concrete repo path (github.com/owner/repo) is high signal,
    # but github.com/search?... is a low-signal aggregator.
    if host == "github.com":
        if path.startswith("/search"):
            return SIGNAL_LOW
        segments = [s for s in path.split("/") if s]
        if len(segments) >= 2:
            return SIGNAL_HIGH
        return SIGNAL_LOW

    # Tier-based boost: research agent's own tier enum is a strong prior.
    if ref.tier in (
        SourceTier.OFFICIAL_API_REF,
        SourceTier.OFFICIAL_REPO,
        SourceTier.OFFICIAL_PACKAGE,
    ):
        return SIGNAL_HIGH

    # Path hints on neutral hosts.
    if any(hint in path for hint in _HIGH_PATH_HINTS):
        return SIGNAL_HIGH
    if any(hint in path for hint in _LOW_PATH_HINTS):
        return SIGNAL_LOW

    # Bare vendor root (e.g. https://clo3d.com/) is low-signal by default —
    # these are marketing homepages, not docs.
    if path in ("", "/"):
        return SIGNAL_LOW

    return SIGNAL_MEDIUM


_SORT_KEY = {SIGNAL_HIGH: 0, SIGNAL_MEDIUM: 1, SIGNAL_LOW: 2}


def sort_sources_by_quality(
    sources: Iterable[SourceRef],
) -> list[tuple[SourceRef, str]]:
    """Return sources paired with their score, high signal first.

    Stable on the input order within each signal band — so the caller's
    existing ordering (registry > MCP > generated) is preserved within
    bands.
    """
    scored = [(s, score_source(s)) for s in sources]
    scored.sort(key=lambda pair: _SORT_KEY.get(pair[1], 99))
    return scored


# ---------------------------------------------------------------------------
# Post-fetch signal measurement
# ---------------------------------------------------------------------------


# Thresholds for post-fetch "is this worth passing to the Author Agent"
# check. Numbers are deliberately generous — the Author Agent has its
# own stricter prose gate; this pass is only meant to cut obvious dead
# weight (bot-wall stubs, 2KB Next.js shells, pure marketing pages).
MIN_SANITIZED_CHARS = 1500
MIN_PROSE_BLOCKS = 3
MIN_TOTAL_PROSE_CHARS = 400


@dataclass
class SignalReport:
    """Outcome of measuring one fetched source's prose density."""

    url: str
    raw_path: str
    sanitized_chars: int = 0
    prose_blocks: int = 0
    prose_chars: int = 0
    passes: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "url": self.url,
            "raw_path": self.raw_path,
            "sanitized_chars": self.sanitized_chars,
            "prose_blocks": self.prose_blocks,
            "prose_chars": self.prose_chars,
            "passes": self.passes,
            "reason": self.reason,
        }


def _is_raw_text_source(url: str) -> bool:
    """True for sources we know serve plain text/markdown directly.

    For these, we can skip HTML sanitisation and use a simpler gate —
    raw markdown files are prose by construction and the HTML-aware
    sanitiser actively damages them (stripping lines with legitimate
    punctuation density like tables or code fences).
    """
    host = urlparse(url).netloc.lower() if url else ""
    return host == "raw.githubusercontent.com"


def measure_signal(*, url: str, raw_path: str, raw_bytes: bytes) -> SignalReport:
    """Measure how much human-readable technical prose a capture contains.

    Uses the SAME sanitizer and prose detector the Author Agent uses,
    so research and author agree on what counts as usable. We import
    lazily to keep this module dependency-light at import time.
    """

    # Lazy imports: avoid circular load and keep this module optional.
    from core.tool_mastery_author_agent.loader import sanitize_text
    from core.tool_mastery_author_agent.mapping import (
        _split_prose_blocks,
        _strip_html,
    )

    report = SignalReport(url=url, raw_path=raw_path)

    try:
        text = raw_bytes.decode("utf-8", errors="replace")
    except Exception as err:  # pragma: no cover - decode('replace') won't raise
        report.reason = f"decode error: {err}"
        return report

    # Raw text sources (raw.githubusercontent.com) are pre-cleaned by
    # construction — use a relaxed gate that doesn't run the HTML
    # sanitiser, which would otherwise drop markdown tables / code
    # fences as "code lines".
    if _is_raw_text_source(url):
        report.sanitized_chars = len(text)
        if report.sanitized_chars < 400:
            report.reason = (
                f"raw text body too small ({report.sanitized_chars} < 400 chars)"
            )
            return report
        # Count non-empty lines as a proxy for prose blocks. We still
        # run the prose-block splitter on the plain text (no tag strip
        # needed) so that the author agent's mapper-compatible block
        # count is reported.
        blocks = _split_prose_blocks(text)
        report.prose_blocks = len(blocks)
        report.prose_chars = sum(len(b) for b in blocks)
        # Relaxed thresholds: a short but dense README is still usable.
        if report.prose_blocks < 1:
            report.reason = "raw text has zero prose blocks after splitter"
            return report
        if report.prose_chars < 200:
            report.reason = (
                f"raw text prose too thin ({report.prose_chars} < 200 chars)"
            )
            return report
        report.passes = True
        report.reason = "passes raw-text signal gate"
        return report

    sanitized = sanitize_text(text)
    report.sanitized_chars = len(sanitized)
    if report.sanitized_chars < MIN_SANITIZED_CHARS:
        report.reason = (
            f"sanitized body too small ({report.sanitized_chars} < "
            f"{MIN_SANITIZED_CHARS} chars)"
        )
        return report

    plain = _strip_html(sanitized)
    blocks = _split_prose_blocks(plain)
    report.prose_blocks = len(blocks)
    report.prose_chars = sum(len(b) for b in blocks)

    if report.prose_blocks < MIN_PROSE_BLOCKS:
        report.reason = (
            f"only {report.prose_blocks} prose block(s) (need ≥{MIN_PROSE_BLOCKS})"
        )
        return report
    if report.prose_chars < MIN_TOTAL_PROSE_CHARS:
        report.reason = (
            f"only {report.prose_chars} prose chars (need ≥{MIN_TOTAL_PROSE_CHARS})"
        )
        return report

    report.passes = True
    report.reason = "passes prose density gate"
    return report


# ---------------------------------------------------------------------------
# Run-level quality flag
# ---------------------------------------------------------------------------


def classify_quality(reports: list[SignalReport]) -> str:
    """Derive a run-level quality flag from per-source signal reports.

    Rules:
        - zero passing sources          → "low"
        - all passing sources           → "high"
        - mixed                         → "mixed"
    """
    if not reports:
        return SIGNAL_LOW
    passing = sum(1 for r in reports if r.passes)
    if passing == 0:
        return SIGNAL_LOW
    if passing == len(reports):
        return SIGNAL_HIGH
    return "mixed"
