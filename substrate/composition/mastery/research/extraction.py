"""Structured knowledge extraction for the Tool Mastery Research Agent.

The extraction layer of the research agent. Where earlier stages focused on *access* (find,
fetch, render, filter), this stage focuses on *understanding*: converting
raw prose and rendered docs into structured, reusable mastery knowledge.

Two responsibilities live here:

1. **Content-based source type classification.** Not URL-based. We look
   at the actual sanitised body of a capture and decide whether it is
   docs prose, rendered docs prose (headless pass), an API reference,
   a code example, or unrecognised content. This lets the pipeline
   distinguish a real API reference page from a cookie-consent banner
   that happens to clear the prose gate.

2. **Pattern extraction.** Pure-Python regex scans (no LLM) that pull:
       - usage patterns (install/setup/CLI/config)
       - API / data structures (objects, fields, params, signatures)
       - workflow sequences (ordered developer flows)

   A pattern is only emitted when it meets the *repeat-signal* rule:
   either the shape occurs multiple times in the source, or it sits
   inside a clearly structured container (ordered list, heading
   sequence, table). Single isolated hits are noise and are dropped.

Design constraints:
    - No network, no LLM, no heuristics dressed up as intelligence.
    - Reuse the Author Agent's shared sanitiser + prose-block splitter
      so research and author agree on what counts as prose.
    - Every emitted pattern carries its source URL, a bounded excerpt,
      and an explicit confidence level.
    - The honesty boundary is non-negotiable: we'd rather classify a
      page ``unknown`` and extract nothing than manufacture structure.

The principle: *understand information, don't collect it*.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from html import unescape
from typing import Any, Iterable
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Code-preserving sanitiser
# ---------------------------------------------------------------------------
#
# The Author Agent's sanitize_text aggressively drops symbol-dense lines so
# that keyword matching is driven by human prose only. That's the right
# thing for prose scoring, but it actively destroys the signals pattern
# extraction needs: install commands, JSON schemas, function signatures,
# and `"field": "type"` pairs all look like "symbol-dense code lines" to
# the prose scrubber and get thrown away.
#
# Pattern extraction therefore runs on a *gentler* preprocessing pass that
# only strips scripts/styles/noscript and HTML tags, keeping the full body
# intact so the regexes can match real code shapes.

_SCRIPT_BLOCK_RE = re.compile(
    r"<script\b[^>]*>.*?</script\s*>", re.IGNORECASE | re.DOTALL
)
_STYLE_BLOCK_RE = re.compile(r"<style\b[^>]*>.*?</style\s*>", re.IGNORECASE | re.DOTALL)
_NOSCRIPT_BLOCK_RE = re.compile(
    r"<noscript\b[^>]*>.*?</noscript\s*>", re.IGNORECASE | re.DOTALL
)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_COLLAPSE_RE = re.compile(r"[ \t]+")

# Heading tags → markdown heading markers. Must run BEFORE generic tag strip
# so extractors that match `^#{1,4}\s+` can fire on HTML source content.
_HEADING_TAG_RE = re.compile(
    r"<h([1-4])\b[^>]*>(.*?)</h\1\s*>", re.IGNORECASE | re.DOTALL
)
# Block-level elements that should have newline boundaries preserved.
_BLOCK_BOUNDARY_RE = re.compile(
    r"</?(?:p|div|section|article|aside|blockquote|"
    r"ul|ol|li|dl|dt|dd|table|tr|th|td|"
    r"pre|figure|figcaption|details|summary|nav|main|footer|header)\b[^>]*>",
    re.IGNORECASE,
)


def preprocess_for_extraction(raw_text: str) -> str:
    """Code-preserving HTML → structured text pass for pattern extraction.

    Strips only the things we *never* want (scripts, styles, noscript)
    while leaving code fences, JSON blobs, install commands, and
    parameter tables fully intact.

    Converts heading tags to markdown heading markers BEFORE
    generic tag stripping so heading-dependent extractors
    (design_rationale, quickstart_flow, conceptual_explanation) can
    fire on real HTML doc content. Also preserves block-level element
    boundaries as newlines for natural content segmentation.
    """
    if not raw_text:
        return raw_text
    cleaned = _SCRIPT_BLOCK_RE.sub(" ", raw_text)
    cleaned = _STYLE_BLOCK_RE.sub(" ", cleaned)
    cleaned = _NOSCRIPT_BLOCK_RE.sub(" ", cleaned)

    # Heading preservation: <h1>…</h1> → "\n# …\n"
    # Must run before _TAG_RE strips all tags indiscriminately.
    def _heading_to_md(m: re.Match) -> str:
        level = int(m.group(1))
        # Strip any nested tags inside the heading text (e.g. <a>, <code>).
        inner = _TAG_RE.sub("", m.group(2)).strip()
        if not inner:
            return "\n"
        prefix = "#" * level
        return f"\n\n{prefix} {inner}\n\n"

    cleaned = _HEADING_TAG_RE.sub(_heading_to_md, cleaned)

    # Block boundary preservation: ensure block-level elements
    # produce line breaks so content segmentation is preserved.
    cleaned = _BLOCK_BOUNDARY_RE.sub("\n", cleaned)

    # Strip remaining tags.
    cleaned = _TAG_RE.sub("\n", cleaned)
    cleaned = unescape(cleaned)

    # Collapse intra-line whitespace but keep newlines for line-based regexes.
    # Collapse runs of >2 blank lines to exactly 2 (paragraph boundary).
    lines = [_WS_COLLAPSE_RE.sub(" ", line).strip() for line in cleaned.splitlines()]
    result: list[str] = []
    blank_run = 0
    for line in lines:
        if not line:
            blank_run += 1
            if blank_run <= 2:
                result.append("")
        else:
            blank_run = 0
            result.append(line)
    return "\n".join(result)


# ---------------------------------------------------------------------------
# Source type
# ---------------------------------------------------------------------------


class SourceType(str, Enum):
    """Content-based classification of a fetched source body."""

    DOCS_PROSE = "docs_prose"
    RENDERED_DOCS_PROSE = "rendered_docs_prose"
    CODE_EXAMPLE = "code_example"
    API_REFERENCE = "api_reference"
    UNKNOWN = "unknown"


# Technical vocabulary — words that, per 1000 prose chars, indicate real
# developer documentation rather than marketing / consent boilerplate.
# Deliberately conservative and generic (no vendor-specific tokens).
_TECH_VOCAB: tuple[str, ...] = (
    "api",
    "endpoint",
    "parameter",
    "parameters",
    "argument",
    "arguments",
    "request",
    "response",
    "header",
    "payload",
    "function",
    "method",
    "class",
    "module",
    "library",
    "package",
    "install",
    "configure",
    "config",
    "authentication",
    "token",
    "oauth",
    "json",
    "schema",
    "field",
    "object",
    "property",
    "return",
    "returns",
    "callback",
    "webhook",
    "error",
    "status code",
    "rate limit",
    "pagination",
    "sdk",
    "client",
    "cli",
    "command",
    "import",
    "export",
    "initialize",
    "instance",
    "usage",
    "example",
    "syntax",
    "signature",
    "deprecated",
    "version",
)

# Markers that distinguish an API reference page from generic prose.
_API_MARKERS: tuple[str, ...] = (
    "get ",
    "post ",
    "put ",
    "patch ",
    "delete ",
    "endpoint",
    "request body",
    "response body",
    "status code",
    "query parameter",
    "path parameter",
    "request header",
    "returns ",
    "returns:",
    "param ",
    "parameters:",
    "arguments:",
)

# HTTP-method tokens used in a stricter "this is a REST reference" check.
_HTTP_METHOD_RE = re.compile(
    r"\b(GET|POST|PUT|PATCH|DELETE)\s+(?:/|https?://)",
)

# Lines that look like CLI commands (leading $ or prompt markers, or
# well-known package managers at the start of a line).
_CLI_RE = re.compile(
    r"(?m)^\s*(?:\$\s+|>\s+|#\s+)?(?:pip|pip3|npm|npx|yarn|pnpm|bun|brew|"
    r"cargo|go|gem|poetry|uv)\s+(?:install|add|run|init|create)\s+\S+",
)

# Fenced or inline code signals.
_CODE_FENCE_RE = re.compile(r"```[a-zA-Z0-9_+-]*\n")
_PRE_TAG_RE = re.compile(r"<pre\b[^>]*>", re.IGNORECASE)
_CODE_TAG_RE = re.compile(r"<code\b[^>]*>", re.IGNORECASE)

# Python/JS function-like signatures.
_FUNC_SIG_RE = re.compile(
    r"(?m)^\s*(?:def|function|async\s+function)\s+[A-Za-z_][\w.]*\s*\("
)

# "name (type) — description" style parameter tables.
_PARAM_DEF_RE = re.compile(
    r"(?m)^\s*[`\"']?([a-z_][\w]*)[`\"']?\s*\(\s*([a-zA-Z_][\w<>\[\],\s]*)\s*\)"
    r"\s*[-–—:]\s+(.+)$"
)

# JSON/YAML-ish "field": "type" pattern repeatedly used by API docs.
_JSON_FIELD_RE = re.compile(r'"([a-z_][\w]*)"\s*:\s*"([a-zA-Z_][\w<>\[\]]*)"')


@dataclass
class SourceTypeReport:
    """Per-source content classification result."""

    url: str
    source_type: SourceType
    tech_vocab_hits: int
    api_marker_hits: int
    code_block_count: int
    prose_chars: int
    confidence: str  # high | medium | low
    reason: str
    rendered_by_headless: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["source_type"] = self.source_type.value
        return d


def _count_vocab_hits(text_lower: str, vocab: Iterable[str]) -> int:
    """Count whole-word vocab hits (generous on plural/punctuation)."""
    total = 0
    for term in vocab:
        if " " in term:
            if term in text_lower:
                total += text_lower.count(term)
        else:
            # word boundary match
            pattern = rf"\b{re.escape(term)}\b"
            total += len(re.findall(pattern, text_lower))
    return total


def classify_source_type(
    *,
    url: str,
    sanitized_text: str,
    plain_text: str,
    prose_chars: int,
    rendered_by_headless: bool = False,
) -> SourceTypeReport:
    """Classify a fetched body into one of five Phase-5 source types.

    ``sanitized_text`` is the Author-Agent-style scrubbed HTML (still
    contains tags). ``plain_text`` is the tag-stripped form used for
    vocabulary density. ``prose_chars`` is the already-measured prose
    total from the signal gate so we don't re-chunk here.

    The classifier is deliberately ordered: API reference is the
    strongest positive signal, then code example, then docs prose, then
    unknown. We never upgrade unknown — if a page doesn't have enough
    technical vocabulary to be recognised, we drop it honestly.
    """

    lower = plain_text.lower()
    tech_hits = _count_vocab_hits(lower, _TECH_VOCAB)
    api_hits = _count_vocab_hits(lower, _API_MARKERS)

    http_method_hits = len(_HTTP_METHOD_RE.findall(plain_text))

    code_block_count = (
        len(_CODE_FENCE_RE.findall(sanitized_text))
        + len(_PRE_TAG_RE.findall(sanitized_text))
        + len(_CODE_TAG_RE.findall(sanitized_text))
    )

    # Density per 1000 prose chars (guarded against zero).
    denom = max(prose_chars, 1)
    vocab_density = (tech_hits * 1000) / denom

    # --- API reference ---------------------------------------------------
    if http_method_hits >= 3 or (api_hits >= 6 and tech_hits >= 10):
        conf = "high" if http_method_hits >= 5 or api_hits >= 10 else "medium"
        return SourceTypeReport(
            url=url,
            source_type=SourceType.API_REFERENCE,
            tech_vocab_hits=tech_hits,
            api_marker_hits=api_hits,
            code_block_count=code_block_count,
            prose_chars=prose_chars,
            confidence=conf,
            reason=(
                f"api reference: http_methods={http_method_hits}, "
                f"api_markers={api_hits}, tech_vocab={tech_hits}"
            ),
            rendered_by_headless=rendered_by_headless,
        )

    # --- Code example ----------------------------------------------------
    # A code-example-heavy page has many code blocks but thin prose.
    if code_block_count >= 5 and prose_chars < 2500 and tech_hits >= 4:
        return SourceTypeReport(
            url=url,
            source_type=SourceType.CODE_EXAMPLE,
            tech_vocab_hits=tech_hits,
            api_marker_hits=api_hits,
            code_block_count=code_block_count,
            prose_chars=prose_chars,
            confidence="medium",
            reason=(
                f"code example: code_blocks={code_block_count}, "
                f"prose_chars={prose_chars}, tech_vocab={tech_hits}"
            ),
            rendered_by_headless=rendered_by_headless,
        )

    # --- Docs prose ------------------------------------------------------
    # Require real technical vocabulary density — this is the filter that
    # rejects cookie-consent banners and marketing pages that happen to
    # clear the plain prose gate.
    if tech_hits >= 8 and vocab_density >= 3.0:
        stype = (
            SourceType.RENDERED_DOCS_PROSE
            if rendered_by_headless
            else SourceType.DOCS_PROSE
        )
        conf = "high" if tech_hits >= 20 and vocab_density >= 6.0 else "medium"
        return SourceTypeReport(
            url=url,
            source_type=stype,
            tech_vocab_hits=tech_hits,
            api_marker_hits=api_hits,
            code_block_count=code_block_count,
            prose_chars=prose_chars,
            confidence=conf,
            reason=(
                f"docs prose: tech_vocab={tech_hits}, "
                f"density={vocab_density:.1f}/1k, "
                f"code_blocks={code_block_count}"
            ),
            rendered_by_headless=rendered_by_headless,
        )

    # --- Unknown ---------------------------------------------------------
    return SourceTypeReport(
        url=url,
        source_type=SourceType.UNKNOWN,
        tech_vocab_hits=tech_hits,
        api_marker_hits=api_hits,
        code_block_count=code_block_count,
        prose_chars=prose_chars,
        confidence="low",
        reason=(
            f"unrecognised content: tech_vocab={tech_hits} "
            f"(density={vocab_density:.1f}/1k), "
            f"api_markers={api_hits}, http_methods={http_method_hits}"
        ),
        rendered_by_headless=rendered_by_headless,
    )


# ---------------------------------------------------------------------------
# Extracted patterns
# ---------------------------------------------------------------------------


_MAX_EXCERPT_CHARS = 500


def _heading_with_body(plain: str, match: re.Match, max_chars: int = 400) -> str:
    """Extract a heading line plus its following body content.

    Headings converted from HTML now sit between double-newline
    boundaries. A naive ``split("\\n\\n", 1)[0]`` only captures the heading
    itself. This helper skips past blank lines after the heading to grab
    up to two non-empty paragraphs of body text.
    """
    start = match.start()
    end = min(len(plain), start + max_chars)
    region = plain[start:end]
    # Split on double-newline — heading is parts[0], body starts at parts[1+].
    parts = re.split(r"\n{2,}", region, maxsplit=5)
    # Reassemble: heading + up to 2 non-empty body chunks.
    chunks = [parts[0]]
    body_count = 0
    for part in parts[1:]:
        stripped = part.strip()
        if stripped:
            chunks.append(stripped)
            body_count += 1
            if body_count >= 2:
                break
    return "\n\n".join(chunks).strip()


def _bounded(text: str) -> str:
    text = text.strip()
    if len(text) <= _MAX_EXCERPT_CHARS:
        return text
    return text[:_MAX_EXCERPT_CHARS].rstrip() + "…"


@dataclass
class ExtractedPattern:
    """A single structured pattern pulled from a source.

    ``kind`` is free-form within the three buckets (usage/api/workflows)
    so the author agent can route more precisely than a flat list —
    e.g. a ``usage`` pattern with ``kind='install_command'`` goes to
    the SDK Idioms section.
    """

    kind: str
    excerpt: str
    url: str
    confidence: str
    occurrences: int = 1
    structured: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _confidence(occurrences: int, structured: bool) -> str:
    if occurrences >= 3 or (structured and occurrences >= 2):
        return "high"
    if occurrences >= 2 or structured:
        return "medium"
    return "low"


def _emit_if_worthy(
    *,
    kind: str,
    excerpt: str,
    url: str,
    occurrences: int,
    structured: bool,
) -> ExtractedPattern | None:
    """Apply the repeat-signal rule before emitting a pattern.

    A pattern is only emitted if it repeats (≥2) OR sits inside an
    obviously structured container. Single isolated hits are dropped.
    """
    if occurrences < 2 and not structured:
        return None
    return ExtractedPattern(
        kind=kind,
        excerpt=_bounded(excerpt),
        url=url,
        confidence=_confidence(occurrences, structured),
        occurrences=occurrences,
        structured=structured,
    )


# --- usage patterns --------------------------------------------------------


def _extract_install_commands(plain: str, url: str) -> list[ExtractedPattern]:
    hits = _CLI_RE.findall(plain)
    # Matches returned as full-line context via finditer for excerpts.
    matches = list(_CLI_RE.finditer(plain))
    if not matches:
        return []
    # Group by normalised manager+package for repeat counting.
    groups: dict[str, list[str]] = {}
    for m in matches:
        line = m.group(0).strip()
        key = re.sub(r"\s+", " ", line.lower())
        groups.setdefault(key, []).append(line)
    out: list[ExtractedPattern] = []
    # We treat the *total* number of CLI lines across the page as the
    # occurrence count for this pattern family — a docs page with three
    # different install commands is unambiguously structured.
    total = len(matches)
    for key, lines in groups.items():
        excerpt = lines[0]
        p = _emit_if_worthy(
            kind="install_command",
            excerpt=excerpt,
            url=url,
            occurrences=max(len(lines), 1),
            structured=total >= 2,
        )
        if p:
            out.append(p)
    return out


_SETUP_STEP_RE = re.compile(r"(?m)^\s*(?:\d+[.)]|[-*])\s+(.{10,200}?)(?:$|\n)")
_SETUP_KEYWORDS = (
    "install",
    "configure",
    "create",
    "initialize",
    "initialise",
    "sign up",
    "generate",
    "obtain",
    "add",
    "run",
    "set up",
    "import",
)


def _extract_setup_flows(plain: str, url: str) -> list[ExtractedPattern]:
    steps = [m.group(1).strip() for m in _SETUP_STEP_RE.finditer(plain)]
    # A "setup flow" is 3+ consecutive-ish list items mentioning setup keywords.
    setup_steps = [s for s in steps if any(kw in s.lower() for kw in _SETUP_KEYWORDS)]
    if len(setup_steps) < 3:
        return []
    excerpt = "\n".join(f"- {s}" for s in setup_steps[:6])
    p = _emit_if_worthy(
        kind="setup_flow",
        excerpt=excerpt,
        url=url,
        occurrences=len(setup_steps),
        structured=True,
    )
    return [p] if p else []


_CONFIG_LINE_RE = re.compile(
    r"(?m)^\s*([A-Z][A-Z0-9_]{3,})\s*=\s*(\S+)"  # env-style config
)


def _extract_config_blocks(plain: str, url: str) -> list[ExtractedPattern]:
    cfg = _CONFIG_LINE_RE.findall(plain)
    if len(cfg) < 2:
        return []
    excerpt = "\n".join(f"{k}={v}" for k, v in cfg[:6])
    p = _emit_if_worthy(
        kind="config_block",
        excerpt=excerpt,
        url=url,
        occurrences=len(cfg),
        structured=True,
    )
    return [p] if p else []


# --- api structures --------------------------------------------------------


def _extract_function_signatures(plain: str, url: str) -> list[ExtractedPattern]:
    matches = list(_FUNC_SIG_RE.finditer(plain))
    if not matches:
        return []
    # Take the first 3 as exemplar excerpts (with a little trailing context).
    excerpts: list[str] = []
    for m in matches[:3]:
        start = m.start()
        end = min(len(plain), start + 180)
        excerpts.append(plain[start:end].split("\n\n", 1)[0])
    joined = "\n".join(excerpts)
    p = _emit_if_worthy(
        kind="function_signature",
        excerpt=joined,
        url=url,
        occurrences=len(matches),
        structured=True,
    )
    return [p] if p else []


def _extract_param_defs(plain: str, url: str) -> list[ExtractedPattern]:
    matches = list(_PARAM_DEF_RE.finditer(plain))
    if len(matches) < 2:
        return []
    excerpt_lines: list[str] = []
    for m in matches[:6]:
        excerpt_lines.append(
            f"- `{m.group(1)}` ({m.group(2).strip()}) — {m.group(3).strip()[:120]}"
        )
    p = _emit_if_worthy(
        kind="parameter_definitions",
        excerpt="\n".join(excerpt_lines),
        url=url,
        occurrences=len(matches),
        structured=True,
    )
    return [p] if p else []


def _extract_json_schemas(plain: str, url: str) -> list[ExtractedPattern]:
    matches = _JSON_FIELD_RE.findall(plain)
    if len(matches) < 3:
        return []
    excerpt_lines = [f'"{k}": "{t}"' for k, t in matches[:8]]
    p = _emit_if_worthy(
        kind="json_schema_fields",
        excerpt="{\n  " + ",\n  ".join(excerpt_lines) + "\n}",
        url=url,
        occurrences=len(matches),
        structured=True,
    )
    return [p] if p else []


# --- workflow sequences ----------------------------------------------------


_STEP_HEADER_RE = re.compile(r"(?im)^\s*#{1,6}\s+step\s+(\d+)\b.*$")
_ORDERED_LIST_RE = re.compile(r"(?m)^\s*(\d+)[.)]\s+(.{10,200}?)(?:$|\n)")
_WORKFLOW_VERBS = (
    "create",
    "send",
    "request",
    "fetch",
    "call",
    "receive",
    "configure",
    "install",
    "initialize",
    "return",
    "handle",
    "authenticate",
    "upload",
    "download",
    "deploy",
)


def _extract_workflow_sequences(plain: str, url: str) -> list[ExtractedPattern]:
    headers = _STEP_HEADER_RE.findall(plain)
    if len(headers) >= 3:
        excerpt_lines: list[str] = []
        for m in _STEP_HEADER_RE.finditer(plain):
            line = plain[m.start() : m.start() + 120].split("\n", 1)[0]
            excerpt_lines.append(line.strip())
            if len(excerpt_lines) >= 6:
                break
        p = _emit_if_worthy(
            kind="stepwise_workflow",
            excerpt="\n".join(excerpt_lines),
            url=url,
            occurrences=len(headers),
            structured=True,
        )
        if p:
            return [p]

    ordered = [m.group(2).strip() for m in _ORDERED_LIST_RE.finditer(plain)]
    action_steps = [s for s in ordered if any(v in s.lower() for v in _WORKFLOW_VERBS)]
    if len(action_steps) >= 3:
        excerpt = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(action_steps[:6]))
        p = _emit_if_worthy(
            kind="ordered_workflow",
            excerpt=excerpt,
            url=url,
            occurrences=len(action_steps),
            structured=True,
        )
        if p:
            return [p]
    return []


# --- version pinning -------------------------------------------------------

# Version header patterns in HTTP-style docs and SDK configs.
_VERSION_HEADER_RE = re.compile(
    r"(?im)^[\"']?(?:Notion-Version|X-API-Version|Api-Version|"
    r"Stripe-Version|OpenAI-Beta|Anthropic-Version|"
    r"Accept-Version|API-Version)[\"']?\s*[:=]\s*[\"']?"
    r"(\d{4}-\d{2}-\d{2}|\d+\.\d+(?:\.\d+)?)[\"']?"
)
# Semver in config/package context (e.g. `"version": "3.2.1"`).
_SEMVER_CONFIG_RE = re.compile(
    r'(?m)["\'](?:version|apiVersion|api_version)["\']'
    r"\s*[:=]\s*[\"'](\d+\.\d+(?:\.\d+)?(?:-[\w.]+)?)[\"']"
)
# Pinned dependency versions (e.g. `"@notionhq/client": "^2.2.15"`).
_PINNED_DEP_RE = re.compile(
    r'(?m)["\'](@?[\w./-]+)["\']'
    r"\s*:\s*[\"']([~^]?\d+\.\d+(?:\.\d+)?)[\"']"
)
# Explicit version pinning prose markers — "pin to", "lock version", etc.
_VERSION_PIN_PROSE_RE = re.compile(
    r"(?im)\b(?:pin(?:ned|ning)?(?:\s+to)?|lock(?:ed)?(?:\s+to)?|"
    r"requires?\s+version|minimum\s+version|"
    r"compatible\s+with\s+v?|supported\s+versions?)\b"
)


def _extract_version_pins(plain: str, url: str) -> list[ExtractedPattern]:
    """Extract version pinning signals from code, configs, and headers.

    Targets the Version Pinning TME section which is 0/8 under
    prose-only extraction because version constraints live in code
    and config, not developer prose.
    """
    out: list[ExtractedPattern] = []

    # Version headers (API versioning pattern).
    header_matches = list(_VERSION_HEADER_RE.finditer(plain))
    if header_matches:
        excerpts = []
        for m in header_matches[:4]:
            start = max(0, m.start() - 20)
            end = min(len(plain), m.end() + 20)
            excerpts.append(plain[start:end].strip())
        p = _emit_if_worthy(
            kind="version_header",
            excerpt="\n".join(excerpts),
            url=url,
            occurrences=len(header_matches),
            structured=True,
        )
        if p:
            out.append(p)

    # Semver in config context.
    semver_matches = list(_SEMVER_CONFIG_RE.finditer(plain))
    if semver_matches:
        excerpts = []
        for m in semver_matches[:4]:
            start = max(0, m.start() - 10)
            end = min(len(plain), m.end() + 10)
            excerpts.append(plain[start:end].strip())
        p = _emit_if_worthy(
            kind="version_constraint",
            excerpt="\n".join(excerpts),
            url=url,
            occurrences=len(semver_matches),
            structured=True,
        )
        if p:
            out.append(p)

    # Pinned dependency versions — only emit if ≥3 (a real manifest, not noise).
    dep_matches = list(_PINNED_DEP_RE.finditer(plain))
    if len(dep_matches) >= 3:
        dep_lines = [f'"{m.group(1)}": "{m.group(2)}"' for m in dep_matches[:6]]
        p = _emit_if_worthy(
            kind="pinned_dependencies",
            excerpt="{\n  " + ",\n  ".join(dep_lines) + "\n}",
            url=url,
            occurrences=len(dep_matches),
            structured=True,
        )
        if p:
            out.append(p)

    # Version pin prose markers combined with nearby semver.
    pin_prose = list(_VERSION_PIN_PROSE_RE.finditer(plain))
    if len(pin_prose) >= 2:
        excerpts = []
        for m in pin_prose[:3]:
            start = max(0, m.start() - 40)
            end = min(len(plain), m.end() + 60)
            excerpts.append(plain[start:end].strip())
        p = _emit_if_worthy(
            kind="version_pin_guidance",
            excerpt="\n".join(excerpts),
            url=url,
            occurrences=len(pin_prose),
            structured=False,
        )
        if p:
            out.append(p)

    return out


# --- design intent and tradeoffs -------------------------------------------

# Structural markers for "why" explanations and design rationale.
_DESIGN_HEADING_RE = re.compile(
    r"(?im)^#{1,4}\s+(?:why|design|philosophy|architecture|"
    r"trade-?offs?|rationale|principles?|motivation|approach)\b.*$"
)
# Comparison table rows (| option | pro | con |) style.
_COMPARISON_ROW_RE = re.compile(r"(?m)^\|[^|]+\|[^|]+\|[^|]+\|")
# "We chose X over Y" / "instead of" / "trade-off" reasoning patterns.
_TRADEOFF_RE = re.compile(
    r"(?im)\b(?:we\s+chose|instead\s+of|trade-?off|"
    r"at\s+the\s+(?:cost|expense)\s+of|"
    r"designed?\s+(?:to|for)|"
    r"optimized?\s+for|"
    r"prioriti[sz]e[sd]?\s+\w+\s+over|"
    r"the\s+reason\s+(?:is|was|for)|"
    r"this\s+(?:means|ensures|allows|enables))\b"
)


def _extract_design_intent(plain: str, url: str) -> list[ExtractedPattern]:
    """Extract design rationale, philosophy, and trade-off signals.

    Targets the Design Intent and Tradeoffs TME section. These signals
    typically live in README philosophy sections, architecture docs, and
    comparison tables — not in prose that keyword scanning reaches.
    """
    out: list[ExtractedPattern] = []

    # Design-related headings with following content.
    headings = list(_DESIGN_HEADING_RE.finditer(plain))
    if headings:
        excerpts = []
        for m in headings[:3]:
            # Use heading+body extractor that bridges blank lines.
            chunk = _heading_with_body(plain, m, max_chars=350)
            if len(chunk) > 40:
                excerpts.append(chunk)
        if excerpts:
            p = _emit_if_worthy(
                kind="design_rationale",
                excerpt="\n\n".join(excerpts),
                url=url,
                occurrences=len(headings),
                structured=True,
            )
            if p:
                out.append(p)

    # Comparison tables (≥3 rows suggest a real comparison).
    comp_rows = list(_COMPARISON_ROW_RE.finditer(plain))
    if len(comp_rows) >= 3:
        table_lines = []
        for m in comp_rows[:8]:
            table_lines.append(m.group(0).strip())
        p = _emit_if_worthy(
            kind="comparison_table",
            excerpt="\n".join(table_lines),
            url=url,
            occurrences=len(comp_rows),
            structured=True,
        )
        if p:
            out.append(p)

    # Trade-off reasoning language in sufficient density.
    tradeoff_matches = list(_TRADEOFF_RE.finditer(plain))
    if len(tradeoff_matches) >= 2:
        excerpts = []
        for m in tradeoff_matches[:3]:
            start = max(0, m.start() - 60)
            end = min(len(plain), m.end() + 100)
            excerpts.append(plain[start:end].strip())
        p = _emit_if_worthy(
            kind="tradeoff_reasoning",
            excerpt="\n".join(excerpts),
            url=url,
            occurrences=len(tradeoff_matches),
            structured=False,
        )
        if p:
            out.append(p)

    return out


# --- operational behavior and edge cases -----------------------------------

# Warning / caution / note admonition blocks common in docs.
_ADMONITION_RE = re.compile(
    r"(?im)^(?:>{1,2}\s*)?(?:\*{0,2}|_{0,2})"
    r"(?:warning|caution|note|important|danger|tip|caveat|gotcha)"
    r"(?:\*{0,2}|_{0,2})\s*[:!]?\s*(.{10,300}?)(?:$|\n)"
)
# Error-handling code patterns (try/catch, error codes, HTTP status checks).
_ERROR_HANDLING_RE = re.compile(
    r"(?m)(?:catch\s*\(|except\s+\w|\.on\s*\(['\"]error|"
    r"if\s*\(\s*(?:err|error|res(?:ponse)?\.status)|"
    r"status\s*[=!]==?\s*[45]\d{2}|"
    r"throw\s+new\s+\w*Error)"
)
# Rate limit / retry / backoff patterns in code and docs.
_RETRY_PATTERN_RE = re.compile(
    r"(?im)\b(?:retry[-_]?after|back[-_]?off|exponential[-_]?backoff|"
    r"max[-_]?retries?|retry[-_]?count|jitter|"
    r"rate[-_]?limit(?:ed|ing)?|throttl(?:e|ing|ed)|"
    r"429|too\s+many\s+requests|"
    r"circuit[-_]?breaker|timeout[-_]?ms)\b"
)
# Explicit edge case / limitation / caveat documentation.
_EDGE_CASE_RE = re.compile(
    r"(?im)\b(?:edge\s+case|corner\s+case|known\s+(?:issue|limitation|bug)|"
    r"does\s+not\s+(?:support|work)|not\s+supported|"
    r"caveat|gotcha|pitfall|"
    r"undefined\s+behavior|unexpected(?:ly)?|"
    r"will\s+(?:fail|throw|error)|may\s+(?:fail|timeout|hang))\b"
)


def _extract_operational_behavior(plain: str, url: str) -> list[ExtractedPattern]:
    """Extract operational constraints, edge cases, and failure modes.

    Targets the Operational Behavior and Edge Cases TME section. Signal
    lives in admonition blocks, error-handling code, retry patterns, and
    explicit caveat documentation — all structural, not prose.
    """
    out: list[ExtractedPattern] = []

    # Admonition / warning blocks.
    admonitions = list(_ADMONITION_RE.finditer(plain))
    if len(admonitions) >= 2:
        excerpts = [m.group(0).strip() for m in admonitions[:5]]
        p = _emit_if_worthy(
            kind="warning_admonition",
            excerpt="\n".join(excerpts),
            url=url,
            occurrences=len(admonitions),
            structured=True,
        )
        if p:
            out.append(p)

    # Error-handling code patterns.
    error_matches = list(_ERROR_HANDLING_RE.finditer(plain))
    if len(error_matches) >= 2:
        excerpts = []
        for m in error_matches[:3]:
            start = max(0, m.start() - 20)
            end = min(len(plain), m.end() + 80)
            excerpts.append(plain[start:end].strip())
        p = _emit_if_worthy(
            kind="error_handling_pattern",
            excerpt="\n".join(excerpts),
            url=url,
            occurrences=len(error_matches),
            structured=True,
        )
        if p:
            out.append(p)

    # Retry / backoff / rate limit patterns.
    retry_matches = list(_RETRY_PATTERN_RE.finditer(plain))
    if len(retry_matches) >= 2:
        excerpts = []
        for m in retry_matches[:4]:
            start = max(0, m.start() - 30)
            end = min(len(plain), m.end() + 60)
            excerpts.append(plain[start:end].strip())
        p = _emit_if_worthy(
            kind="retry_backoff_pattern",
            excerpt="\n".join(excerpts),
            url=url,
            occurrences=len(retry_matches),
            structured=False,
        )
        if p:
            out.append(p)

    # Explicit edge case / limitation mentions.
    edge_matches = list(_EDGE_CASE_RE.finditer(plain))
    if len(edge_matches) >= 2:
        excerpts = []
        for m in edge_matches[:4]:
            start = max(0, m.start() - 40)
            end = min(len(plain), m.end() + 80)
            excerpts.append(plain[start:end].strip())
        p = _emit_if_worthy(
            kind="edge_case_documentation",
            excerpt="\n".join(excerpts),
            url=url,
            occurrences=len(edge_matches),
            structured=False,
        )
        if p:
            out.append(p)

    return out


# --- conceptual model (tutorial flow extractor) ----------------------------

# Getting-started / quickstart heading patterns.
_QUICKSTART_HEADING_RE = re.compile(
    r"(?im)^#{1,4}\s+(?:getting\s+started|quickstart|quick\s+start|"
    r"tutorial|overview|introduction|how\s+it\s+works|"
    r"concepts?|fundamentals?|basics?)\b.*$"
)
# Mental-model / conceptual language.
_CONCEPTUAL_RE = re.compile(
    r"(?im)\b(?:under\s+the\s+hood|mental\s+model|"
    r"think\s+of\s+(?:it\s+)?as|conceptually|"
    r"at\s+a\s+high\s+level|the\s+key\s+(?:idea|concept|insight)|"
    r"in\s+(?:simple|other)\s+terms|analogous\s+to|"
    r"the\s+(?:basic|core|fundamental)\s+(?:idea|concept|model))\b"
)
# Multi-step tutorial flow: "Step 1: …" or "1. First, …" style.
_TUTORIAL_STEP_RE = re.compile(
    r"(?im)^(?:\s*#{1,4}\s+)?(?:step\s+\d+|phase\s+\d+|\d+[.)]\s+(?:first|next|then|finally))\b"
)


def _extract_conceptual_model(plain: str, url: str) -> list[ExtractedPattern]:
    """Extract conceptual model, mental model, and tutorial flow signals.

    Supplements the existing workflow extractors (which require action
    verbs) with broader conceptual signals: getting-started headings,
    mental model language, and tutorial step progressions.
    """
    out: list[ExtractedPattern] = []

    # Quickstart / overview headings with body.
    qs_headings = list(_QUICKSTART_HEADING_RE.finditer(plain))
    if qs_headings:
        excerpts = []
        for m in qs_headings[:3]:
            # Use heading+body extractor that bridges blank lines.
            body = _heading_with_body(plain, m, max_chars=400)
            if len(body) > 40:
                excerpts.append(body)
        if len(excerpts) >= 1:
            p = _emit_if_worthy(
                kind="quickstart_flow",
                excerpt="\n\n".join(excerpts),
                url=url,
                occurrences=len(qs_headings),
                structured=True,
            )
            if p:
                out.append(p)

    # Mental model / conceptual language.
    concept_matches = list(_CONCEPTUAL_RE.finditer(plain))
    if len(concept_matches) >= 2:
        excerpts = []
        for m in concept_matches[:3]:
            start = max(0, m.start() - 40)
            end = min(len(plain), m.end() + 120)
            excerpts.append(plain[start:end].strip())
        p = _emit_if_worthy(
            kind="conceptual_explanation",
            excerpt="\n".join(excerpts),
            url=url,
            occurrences=len(concept_matches),
            structured=False,
        )
        if p:
            out.append(p)

    # Tutorial step progressions (broader than _WORKFLOW_VERBS filter).
    tutorial_steps = list(_TUTORIAL_STEP_RE.finditer(plain))
    if len(tutorial_steps) >= 3:
        excerpt_lines = []
        for m in tutorial_steps[:6]:
            line = plain[m.start() : m.start() + 120].split("\n", 1)[0]
            excerpt_lines.append(line.strip())
        p = _emit_if_worthy(
            kind="tutorial_progression",
            excerpt="\n".join(excerpt_lines),
            url=url,
            occurrences=len(tutorial_steps),
            structured=True,
        )
        if p:
            out.append(p)

    return out


# ---------------------------------------------------------------------------
# Top-level extraction
# ---------------------------------------------------------------------------


@dataclass
class SourceExtraction:
    """All Phase-5 output for one OK source."""

    url: str
    source_type: SourceType
    type_report: SourceTypeReport
    usage: list[ExtractedPattern] = field(default_factory=list)
    api: list[ExtractedPattern] = field(default_factory=list)
    workflows: list[ExtractedPattern] = field(default_factory=list)

    def total_patterns(self) -> int:
        return len(self.usage) + len(self.api) + len(self.workflows)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "source_type": self.source_type.value,
            "type_report": self.type_report.to_dict(),
            "usage": [p.to_dict() for p in self.usage],
            "api": [p.to_dict() for p in self.api],
            "workflows": [p.to_dict() for p in self.workflows],
        }


def extract_from_source(
    *,
    url: str,
    raw_text: str,
    sanitized_text: str,
    plain_text: str,
    prose_chars: int,
    rendered_by_headless: bool = False,
) -> SourceExtraction:
    """Run classification + pattern extraction on one fetched body.

    ``raw_text`` is the undecoded capture body (pre-sanitiser). We run a
    code-preserving preprocessing pass over it for pattern extraction so
    install commands, JSON schemas, and function signatures survive.

    ``sanitized_text`` and ``plain_text`` are the Author-Agent-aligned
    prose views — used only for classification and density measurement.
    """

    type_report = classify_source_type(
        url=url,
        sanitized_text=sanitized_text,
        plain_text=plain_text,
        prose_chars=prose_chars,
        rendered_by_headless=rendered_by_headless,
    )

    extraction = SourceExtraction(
        url=url,
        source_type=type_report.source_type,
        type_report=type_report,
    )

    # Honesty boundary: do not extract patterns from unknown content.
    if type_report.source_type is SourceType.UNKNOWN:
        return extraction

    code_preserved = preprocess_for_extraction(raw_text)

    extraction.usage.extend(_extract_install_commands(code_preserved, url))
    extraction.usage.extend(_extract_setup_flows(code_preserved, url))
    extraction.usage.extend(_extract_config_blocks(code_preserved, url))
    extraction.usage.extend(_extract_version_pins(code_preserved, url))

    extraction.api.extend(_extract_function_signatures(code_preserved, url))
    extraction.api.extend(_extract_param_defs(code_preserved, url))
    extraction.api.extend(_extract_json_schemas(code_preserved, url))

    extraction.workflows.extend(_extract_workflow_sequences(code_preserved, url))
    extraction.workflows.extend(_extract_design_intent(code_preserved, url))
    extraction.workflows.extend(_extract_operational_behavior(code_preserved, url))
    extraction.workflows.extend(_extract_conceptual_model(code_preserved, url))

    return extraction


def merge_extractions(
    extractions: list[SourceExtraction],
) -> dict[str, list[dict[str, Any]]]:
    """Fold per-source extractions into the artifact's flat bucket layout.

    Output shape matches the artifact contract:
        {
            "usage":    [{...}, ...],
            "api":      [{...}, ...],
            "workflows":[{...}, ...],
        }
    """
    buckets: dict[str, list[dict[str, Any]]] = {
        "usage": [],
        "api": [],
        "workflows": [],
    }
    for ex in extractions:
        for p in ex.usage:
            buckets["usage"].append(p.to_dict())
        for p in ex.api:
            buckets["api"].append(p.to_dict())
        for p in ex.workflows:
            buckets["workflows"].append(p.to_dict())
    return buckets


# ---------------------------------------------------------------------------
# Convenience: pattern → TME section routing
# ---------------------------------------------------------------------------


# Map each pattern ``kind`` to the TME section it is valid evidence for.
# The Author Agent uses this to route extracted patterns without any
# keyword matching on the pattern content itself.
PATTERN_SECTION_MAP: dict[str, str] = {
    # SDK Idioms ← install + setup flows
    "install_command": "SDK Idioms",
    "setup_flow": "SDK Idioms",
    "config_block": "SDK Idioms",
    # Core Operations ← API signatures / endpoints
    "function_signature": "Core Operations with Exact Signatures",
    "parameter_definitions": "Core Operations with Exact Signatures",
    # Data Model ← JSON schema fields
    "json_schema_fields": "Data Model",
    # Conceptual Model ← workflows + tutorials
    "stepwise_workflow": "Conceptual Model and Solution Recipes",
    "ordered_workflow": "Conceptual Model and Solution Recipes",
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
