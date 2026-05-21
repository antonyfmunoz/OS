"""
Workload Classification Policy v1 — deterministic execution weight.

Purpose
-------
Classifies incoming requests by execution weight — lightweight, standard,
or heavyweight — using deterministic rules only (no LLM).  Feeds into
resource guard and routing decisions downstream.

Design rules
------------
- Rule-based keyword matching only (no LLM, no fuzzy).
- Bounded workload classes: lightweight | standard | heavyweight.
- Priority-ordered rules — first match wins.
- Pure function, thread-safe, no mutable globals.
- Imports NOTHING from the hot path (gateway, cognitive_loop,
  model_router, agent_runtime, primitives).
"""

from __future__ import annotations

from typing import Any, Optional

__all__ = [
    "classify_workload",
    "workload_weight_order",
]

_WORKLOAD_VERSION = "1.0"

# ── workload classes ────────────────────────────────────────────────────────

WC_LIGHTWEIGHT = "lightweight"
WC_STANDARD = "standard"
WC_HEAVYWEIGHT = "heavyweight"

_VALID_WORKLOAD_CLASSES = frozenset({WC_LIGHTWEIGHT, WC_STANDARD, WC_HEAVYWEIGHT})

# ── heavyweight keyword triggers ────────────────────────────────────────────

_HEAVYWEIGHT_KEYWORDS: tuple[str, ...] = (
    "analyze",
    "fix",
    "debug",
    "refactor",
    "implement",
    "build",
    "migrate",
    "deploy",
    "scrape",
    "playwright",
    "browser",
    "crawl",
    "deep dive",
    "rewrite",
    "audit",
    "overhaul",
)

# ── lightweight keyword triggers ────────────────────────────────────────────

_LIGHTWEIGHT_KEYWORDS: tuple[str, ...] = (
    "what",
    "which",
    "who",
    "when",
    "where",
    "how many",
    "status",
    "help",
    "hello",
    "hi",
    "hey",
    "thanks",
    "thank you",
    "ok",
    "yes",
    "no",
    "clear",
    "reset",
)

# ── heavyweight workflow kinds ──────────────────────────────────────────────

_HEAVYWEIGHT_WORKFLOW_KINDS = frozenset({"builder_dev", "system_ops"})

# ── short text threshold ────────────────────────────────────────────────────

_SHORT_TEXT_THRESHOLD = 30


# ── public API ──────────────────────────────────────────────────────────────


def classify_workload(
    text: str,
    mode: str,
    workflow_kind: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Classify a request into a workload weight class.

    Returns::

        {
          "workload_class": "lightweight" | "standard" | "heavyweight",
          "reason": str,
          "matched_rule": str,
          "workload_version": "1.0",
        }

    Classification priority:
      1. workflow_kind in heavyweight set → heavyweight.
      2. metadata["force_workload"] override → that value.
      3. Keyword-based heavyweight triggers.
      4. Keyword-based lightweight triggers.
      5. Short text (<30 chars) with no heavyweight keywords → lightweight.
      6. Default → standard.
    """
    clean = (text or "").strip()
    lower = clean.lower()

    # Rule 1: heavyweight workflow kinds
    if workflow_kind in _HEAVYWEIGHT_WORKFLOW_KINDS:
        return _result(
            WC_HEAVYWEIGHT,
            f"workflow_kind '{workflow_kind}' is heavyweight",
            "workflow_kind_heavyweight",
        )

    # Rule 2: metadata force override
    if metadata and "force_workload" in metadata:
        forced = str(metadata["force_workload"]).strip().lower()
        if forced in _VALID_WORKLOAD_CLASSES:
            return _result(
                forced,
                f"forced via metadata to '{forced}'",
                "metadata_force_workload",
            )

    # Rule 3: heavyweight keywords
    for kw in _HEAVYWEIGHT_KEYWORDS:
        if kw in lower:
            return _result(
                WC_HEAVYWEIGHT,
                f"keyword '{kw}' triggers heavyweight",
                f"keyword_heavyweight:{kw}",
            )

    # Rule 4: lightweight keywords
    for kw in _LIGHTWEIGHT_KEYWORDS:
        if kw in lower:
            return _result(
                WC_LIGHTWEIGHT,
                f"keyword '{kw}' triggers lightweight",
                f"keyword_lightweight:{kw}",
            )

    # Rule 5: short text with no heavyweight keywords → lightweight
    if len(clean) < _SHORT_TEXT_THRESHOLD:
        return _result(
            WC_LIGHTWEIGHT,
            f"short text ({len(clean)} chars, < {_SHORT_TEXT_THRESHOLD})",
            "short_text",
        )

    # Rule 6: default
    return _result(WC_STANDARD, "no rule matched", "default_standard")


def workload_weight_order(wc: str) -> int:
    """Return numeric weight for comparison: 0=lightweight, 1=standard, 2=heavyweight."""
    if wc == WC_LIGHTWEIGHT:
        return 0
    if wc == WC_STANDARD:
        return 1
    if wc == WC_HEAVYWEIGHT:
        return 2
    raise ValueError(f"unknown workload class: {wc!r}")


# ── internal ────────────────────────────────────────────────────────────────


def _result(workload_class: str, reason: str, matched_rule: str) -> dict[str, Any]:
    """Build a standard classification result dict."""
    return {
        "workload_class": workload_class,
        "reason": reason,
        "matched_rule": matched_rule,
        "workload_version": _WORKLOAD_VERSION,
    }
