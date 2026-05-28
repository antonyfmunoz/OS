"""
Mode behavior shaping — post-router output shaping by substrate mode.

Purpose
-------
Applies lightweight, deterministic transformations to router output based
on the active substrate mode (builder | product). This is a SHAPING layer,
not a routing layer. It runs AFTER the router returns a reply and BEFORE
the reply reaches Discord.

Design rules
------------
- Pure functions. No state, no threads, no imports from the hot path.
- Never suppresses capability — both modes get the same router output;
  product mode just sanitizes how it's presented.
- Deterministic. No LLM calls, no randomness. Regex + string ops only.
- Safe fallback: if shaping fails, return the original text unmodified.

Modes
-----
- builder: allows system/debug language. Enforces structure (no rambling).
- product: strips internal/system language, enforces clean SaaS output.
- unknown/None: no shaping (pass-through).
"""

from __future__ import annotations

import os
import re
import sys
from typing import Optional

LAYER_NAME = "mode_behavior"
LAYER_VERSION = "v1"


def _log(msg: str) -> None:
    print(f"[substrate.mode_behavior] {msg}", file=sys.stderr)


# ─── Product mode: internal language patterns ────────────────────────────────
# These patterns match system/internal references that should not appear in
# product-facing output. Case-insensitive, bounded.

_PRODUCT_STRIP_PATTERNS: list[re.Pattern[str]] = [
    # Router/backend internals
    re.compile(r"\b(?:tmux|send[_-]keys|capture[_-]pane)\b", re.IGNORECASE),
    re.compile(r"\b(?:model[_-]router|call[_-]with[_-]fallback)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:provider[_-]chain|fallback[_-]chain|provider[_-]priority)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:cc[_-]sdk|claude[_-]cli|claude[_-]code)\b", re.IGNORECASE),
    # Substrate internals
    re.compile(
        r"\b(?:substrate|voice[_-]session|voice[_-]eos[_-]responder)\b", re.IGNORECASE
    ),
    re.compile(
        r"\b(?:cognitive[_-]loop|agent[_-]runtime|gateway\.py)\b", re.IGNORECASE
    ),
    re.compile(
        r"\b(?:" + re.escape(os.environ.get("AI_NAME", "ai").lower()) + r"[_-]\w+)\b",
        re.IGNORECASE,
    ),
    # Infrastructure
    re.compile(r"\b(?:backend\s*#?\d*|responder[_-]backend)\b", re.IGNORECASE),
    re.compile(r"\b(?:tmux[_-]session|session[_-]bridge)\b", re.IGNORECASE),
    re.compile(r"\b(?:docker|container|neon|psycopg)\b", re.IGNORECASE),
    re.compile(r"\b(?:ollama|gemma|groq|anthropic\s+api)\b", re.IGNORECASE),
]

# Lines that are purely debug/internal get removed entirely
_PRODUCT_REMOVE_LINE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\s*\[(?:debug|trace|substrate|router|backend)\]", re.IGNORECASE),
    re.compile(r"^\s*provider[=:]", re.IGNORECASE),
    re.compile(r"^\s*model[=:]", re.IGNORECASE),
    re.compile(r"^\s*target[=:]", re.IGNORECASE),
    re.compile(r"^\s*session[=:]", re.IGNORECASE),
]


def _contains_internal_language(text: str) -> bool:
    """Check if text contains internal/system language."""
    for pat in _PRODUCT_STRIP_PATTERNS:
        if pat.search(text):
            return True
    return False


def _strip_internal_lines(text: str) -> str:
    """Remove lines that are purely debug/internal markers."""
    lines = text.splitlines()
    cleaned: list[str] = []
    for line in lines:
        skip = False
        for pat in _PRODUCT_REMOVE_LINE_PATTERNS:
            if pat.search(line):
                skip = True
                break
        if not skip:
            cleaned.append(line)
    return "\n".join(cleaned)


def _mask_internal_refs(text: str) -> str:
    """Replace internal references with clean alternatives in-line.

    Only masks when the internal term appears in an explanatory context
    (not when it's part of actual code output the user asked for).
    """
    # Replace session name references
    _ai = re.escape(os.environ.get("AI_NAME", "ai").lower())
    text = re.sub(rf"\b{_ai}_\w+\b", "session", text, flags=re.IGNORECASE)
    # Replace provider chain references
    text = re.sub(
        r"\b(?:provider[_-]chain|fallback[_-]chain)\b",
        "processing pipeline",
        text,
        flags=re.IGNORECASE,
    )
    # Replace backend references
    text = re.sub(
        r"\b(?:responder[_-]backend|backend\s*#?\d+)\b",
        "service",
        text,
        flags=re.IGNORECASE,
    )
    # Replace router/infrastructure terms in prose
    text = re.sub(r"\b(?:model[_-]router)\b", "system", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\b(?:call[_-]with[_-]fallback)\b",
        "request handler",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\b(?:tmux)\b", "session", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\b(?:cc[_-]sdk|claude[_-]cli|claude[_-]code)\b",
        "assistant",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:cognitive[_-]loop)\b", "reasoning engine", text, flags=re.IGNORECASE
    )
    text = re.sub(
        r"\b(?:agent[_-]runtime)\b", "processing engine", text, flags=re.IGNORECASE
    )
    text = re.sub(r"\b(?:substrate)\b", "system", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\b(?:voice[_-]eos[_-]responder)\b", "voice handler", text, flags=re.IGNORECASE
    )
    text = re.sub(r"\b(?:docker|container)\b", "service", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:ollama|gemma|groq)\b", "AI model", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:anthropic\s+api)\b", "AI service", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:neon|psycopg)\b", "database", text, flags=re.IGNORECASE)
    return text


# ─── Builder mode: structure enforcement ─────────────────────────────────────


def _enforce_builder_structure(text: str) -> str:
    """Trim excessive verbosity from builder output.

    Builder mode keeps all system/debug content but enforces:
    - No trailing filler paragraphs (e.g. "Let me know if...")
    - Consecutive blank lines collapsed to one
    """
    # Collapse 3+ consecutive blank lines to 2
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    # Strip common trailing filler
    filler_patterns = [
        re.compile(
            r"\n+(?:Let me know if (?:you )?(?:need|want|have).*$)",
            re.IGNORECASE | re.DOTALL,
        ),
        re.compile(
            r"\n+(?:Feel free to (?:ask|reach|let).*$)", re.IGNORECASE | re.DOTALL
        ),
        re.compile(r"\n+(?:Hope this helps.*$)", re.IGNORECASE | re.DOTALL),
        re.compile(r"\n+(?:Is there anything else.*$)", re.IGNORECASE | re.DOTALL),
    ]
    for pat in filler_patterns:
        text = pat.sub("", text)

    return text.rstrip()


# ─── Product mode: full shaping ─────────────────────────────────────────────


def _shape_product(text: str) -> str:
    """Apply product-mode shaping to router output.

    Steps:
    1. Remove purely debug/internal lines
    2. Mask remaining internal references
    3. Collapse excessive whitespace
    4. Strip trailing filler
    """
    result = _strip_internal_lines(text)
    result = _mask_internal_refs(result)
    # Collapse 3+ blank lines
    result = re.sub(r"\n{4,}", "\n\n\n", result)
    # Strip trailing filler (same as builder)
    result = _enforce_builder_structure(result)
    return result.strip()


# ─── Public API ──────────────────────────────────────────────────────────────


def shape_reply(text: str, *, mode: Optional[str] = None) -> str:
    """Apply mode-appropriate shaping to a router reply.

    Args:
        text: Raw reply text from the router/Claude session.
        mode: "builder" | "product" | "unknown" | None.

    Returns:
        Shaped text. On any error, returns the original text unmodified.
    """
    if not text or not isinstance(text, str):
        return text or ""

    clean = text.strip()
    if not clean:
        return ""

    try:
        if mode == "product":
            return _shape_product(clean)
        if mode == "builder":
            return _enforce_builder_structure(clean)
        # unknown / None — pass-through
        return clean
    except Exception as e:  # noqa: BLE001 — safe fallback
        _log(f"shape_reply failed for mode={mode}: {e}")
        return clean


def detect_internal_leakage(text: str) -> list[str]:
    """Return list of internal patterns found in text. For testing/audit."""
    found: list[str] = []
    for pat in _PRODUCT_STRIP_PATTERNS:
        match = pat.search(text)
        if match:
            found.append(match.group(0))
    return found


__all__ = [
    "LAYER_NAME",
    "LAYER_VERSION",
    "shape_reply",
    "detect_internal_leakage",
]
