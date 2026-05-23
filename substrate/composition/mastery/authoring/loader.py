"""Research artifact loader.

Reads a research_artifact.json + its on-disk raw captures into
normalised in-memory structures the mapper can reason about.

Does NOT parse or score content — that is the mapper's job. This
module's only responsibility is honest I/O with clear errors.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Raw capture sanitisation
# ---------------------------------------------------------------------------
#
# The Author Agent must only treat human-readable prose as sourcing material.
# SPA shells (Next.js, React) and GitHub's search page stuff massive amounts
# of JavaScript, JSON flight data, and inline style into the initial HTML
# body — that content contains thousands of keyword-like tokens that, under a
# naïve keyword scan, falsely promote sections to "sourced".
#
# This sanitiser runs at load time so every downstream consumer (mapping,
# drafting, excerpt selection) sees the same scrubbed text. It is deliberately
# aggressive: we would rather drop real prose than admit minified JavaScript.

_SCRIPT_BLOCK_RE = re.compile(
    r"<script\b[^>]*>.*?</script\s*>", re.IGNORECASE | re.DOTALL
)
_STYLE_BLOCK_RE = re.compile(r"<style\b[^>]*>.*?</style\s*>", re.IGNORECASE | re.DOTALL)
_NOSCRIPT_BLOCK_RE = re.compile(
    r"<noscript\b[^>]*>.*?</noscript\s*>", re.IGNORECASE | re.DOTALL
)
# Next.js flight-data push calls — `self.__next_f.push([...])` — routinely
# appear OUTSIDE <script> tags in captured HTML (e.g. when the body is parsed
# as text). Nuke them by line.
_NEXT_FLIGHT_RE = re.compile(r"self\.__next_f\.push\([^\n]*", re.IGNORECASE)
# Long base64-looking blobs.
_BASE64_RE = re.compile(r"[A-Za-z0-9+/]{80,}={0,2}")
# Long hex / hash blobs (chunk names etc.).
_HEX_RE = re.compile(r"[a-f0-9]{32,}")


def sanitize_text(text: str) -> str:
    """Remove non-prose noise from a raw HTTP capture.

    Strips scripts, styles, Next.js flight payloads, base64/hex blobs, and
    JSON-looking lines before returning the residue. The result is NOT a
    rendered DOM — it is "HTML minus obvious garbage", still containing
    tags. The mapping layer will apply its own prose detection on top.
    """
    if not text:
        return text
    cleaned = _SCRIPT_BLOCK_RE.sub(" ", text)
    cleaned = _STYLE_BLOCK_RE.sub(" ", cleaned)
    cleaned = _NOSCRIPT_BLOCK_RE.sub(" ", cleaned)
    cleaned = _NEXT_FLIGHT_RE.sub(" ", cleaned)
    cleaned = _BASE64_RE.sub(" ", cleaned)
    cleaned = _HEX_RE.sub(" ", cleaned)

    # Per-line filter: drop lines that look like minified JS, JSON blobs,
    # or feature-flag arrays. A line is kept only if it has enough letters
    # relative to symbols.
    kept: list[str] = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if len(stripped) > 400 and _symbol_density(stripped) > 0.15:
            # Very long symbol-dense line — almost certainly code/JSON.
            continue
        if _symbol_density(stripped) > 0.30:
            # Heavy code/JSON syntax.
            continue
        kept.append(line)
    return "\n".join(kept)


_SYMBOL_CHARS = set("{}[]();=<>/\\|`~*&^%$#@+")


def _symbol_density(s: str) -> float:
    """Fraction of characters that look like code punctuation."""
    if not s:
        return 0.0
    hits = sum(1 for c in s if c in _SYMBOL_CHARS)
    return hits / len(s)


@dataclass
class RawCapture:
    """One successfully fetched source, loaded from disk."""

    url: str
    tier: str
    label: str
    raw_path: str  # absolute
    text: str
    http_status: int | None = None
    bytes: int = 0
    error: str | None = None  # load error, not fetch error


@dataclass
class LoadedArtifact:
    """Normalised research artifact + raw bodies."""

    tool_slug: str
    mode: str
    generated_at: str
    run_dir: Path
    artifact_path: Path
    raw_captures: list[RawCapture] = field(default_factory=list)
    planned_sources: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    load_errors: list[str] = field(default_factory=list)
    # Structured patterns extracted by the research agent.
    # Flat dict with three buckets (usage / api / workflows). Each entry
    # matches extraction.ExtractedPattern.to_dict().
    extracted_patterns: dict[str, list[dict[str, Any]]] = field(
        default_factory=lambda: {"usage": [], "api": [], "workflows": []}
    )

    @property
    def has_any_source(self) -> bool:
        return any(c.text for c in self.raw_captures)

    @property
    def total_raw_bytes(self) -> int:
        return sum(len(c.text) for c in self.raw_captures)


def _read_text_safely(path: Path, max_bytes: int = 2_000_000) -> tuple[str, str | None]:
    """Read a raw capture off disk.

    Bounded at 2MB per file — the research agent captures bounded
    HTML dumps; anything bigger than 2MB is almost certainly a
    mis-fetch and would hurt keyword scanning more than it helps.
    """
    try:
        raw = path.read_bytes()[:max_bytes]
    except OSError as e:
        return "", f"read error: {e}"
    try:
        decoded = raw.decode("utf-8", errors="replace")
    except Exception as e:  # defensive — decode('replace') should never raise
        return "", f"decode error: {e}"
    return sanitize_text(decoded), None


def load_artifact(artifact_path: Path) -> LoadedArtifact:
    """Load research_artifact.json and all OK raw captures.

    Raises nothing on per-file failures — load_errors accumulates.
    """

    if not artifact_path.is_file():
        raise FileNotFoundError(f"research artifact not found: {artifact_path}")

    data = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact = data.get("artifact") or {}
    plan = data.get("plan") or {}

    run_dir = artifact_path.parent
    loaded = LoadedArtifact(
        tool_slug=str(artifact.get("tool_slug", "")),
        mode=str(artifact.get("mode", "")),
        generated_at=str(artifact.get("generated_at", "")),
        run_dir=run_dir,
        artifact_path=artifact_path,
        planned_sources=list(plan.get("sources") or []),
        notes=list(artifact.get("notes") or []),
    )
    if not loaded.tool_slug:
        loaded.load_errors.append("artifact has no tool_slug")
        return loaded

    # Research agent may have emitted structured patterns.
    # Accept older artifacts that don't carry this key.
    raw_patterns = artifact.get("extracted_patterns") or {}
    if isinstance(raw_patterns, dict):
        loaded.extracted_patterns = {
            "usage": list(raw_patterns.get("usage") or []),
            "api": list(raw_patterns.get("api") or []),
            "workflows": list(raw_patterns.get("workflows") or []),
        }

    for entry in artifact.get("sources") or []:
        if entry.get("status") != "ok":
            continue
        ref = entry.get("ref") or {}
        raw_rel = entry.get("raw_path")
        if not raw_rel:
            loaded.load_errors.append(f"ok source {ref.get('url')!r} has no raw_path")
            continue
        raw_abs = run_dir / raw_rel
        text, err = _read_text_safely(raw_abs)
        if err:
            loaded.load_errors.append(f"{ref.get('url')!r}: {err}")
            continue
        loaded.raw_captures.append(
            RawCapture(
                url=str(ref.get("url", "")),
                tier=str(ref.get("tier", "")),
                label=str(ref.get("label", "")),
                raw_path=str(raw_abs),
                text=text,
                http_status=entry.get("http_status"),
                bytes=entry.get("bytes") or 0,
            )
        )

    return loaded
