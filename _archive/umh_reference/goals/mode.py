"""
GoalMode — goal-conditioned intelligence for EOS.

Defines behavioral modes that adapt strategy selection, directive filtering,
and control sensitivity based on the type of objective, not just response
quality.

Mode resolution priority:
    1. Explicit input (if caller provides a mode)
    2. Heuristic inference from message text (deterministic)
    3. Fallback → DEFAULT

No LLM calls. No randomness. Deterministic inference.

Usage::

    from umh.goals.mode import GoalMode, resolve_mode, infer_mode

    # Explicit
    mode = resolve_mode(explicit="fast")  # → GoalMode.FAST

    # Inferred
    mode = resolve_mode(message="brainstorm ideas for outreach")  # → GoalMode.CREATIVE

    # Fallback
    mode = resolve_mode()  # → GoalMode.DEFAULT
"""

from __future__ import annotations

import enum
import logging
import re

_log = logging.getLogger(__name__)


class GoalMode(enum.Enum):
    """Behavioral mode that conditions the intelligence pipeline."""

    DEFAULT = "default"
    FAST = "fast"
    ACCURATE = "accurate"
    CREATIVE = "creative"
    STRUCTURED = "structured"


# ─── Mode-Specific Strategy Preferences ──────────────────────────────────────
# Maps each mode to an ordered list of preferred strategy names.
# pick_strategies() uses this to bias selection without overriding memory.

MODE_STRATEGY_PREFERENCES: dict[GoalMode, list[str]] = {
    GoalMode.DEFAULT: [],
    GoalMode.FAST: ["concise", "baseline"],
    GoalMode.ACCURATE: ["clarity", "structured"],
    GoalMode.CREATIVE: ["baseline", "clarity"],
    GoalMode.STRUCTURED: ["structured", "clarity"],
}

# ─── Mode-Specific Directive Suppression ─────────────────────────────────────
# Directives to suppress per mode (on top of normal DirectiveMemory suppression).

MODE_SUPPRESSED_DIRECTIVES: dict[GoalMode, frozenset[str]] = {
    GoalMode.DEFAULT: frozenset(),
    GoalMode.FAST: frozenset({"structured"}),
    GoalMode.ACCURATE: frozenset(),
    GoalMode.CREATIVE: frozenset(),
    GoalMode.STRUCTURED: frozenset({"concise"}),
}

# ─── Mode-Specific Control Sensitivity Multipliers ───────────────────────────
# Multipliers applied to control thresholds per mode.
# > 1.0 = more tolerant (higher thresholds → less intervention)
# < 1.0 = stricter (lower thresholds → more intervention)

MODE_CONTROL_SENSITIVITY: dict[GoalMode, dict[str, float]] = {
    GoalMode.DEFAULT: {},
    GoalMode.FAST: {
        "hallucination_confidence": 0.75,
        "low_quality": 0.8,
        "block_confidence": 0.65,
    },
    GoalMode.ACCURATE: {
        "hallucination_confidence": 1.25,
        "low_quality": 1.2,
        "block_confidence": 1.4,
    },
    GoalMode.CREATIVE: {
        "hallucination_confidence": 0.7,
        "low_quality": 0.85,
        "block_confidence": 0.75,
    },
    GoalMode.STRUCTURED: {
        "hallucination_confidence": 1.0,
        "low_quality": 1.15,
        "block_confidence": 1.0,
    },
}


# ─── Inference Patterns ──────────────────────────────────────────────────────
# Ordered list of (compiled_regex, mode). First match wins.
# Patterns are case-insensitive and match against the full message.

_INFERENCE_RULES: list[tuple[re.Pattern, GoalMode]] = [
    # FAST: short queries, urgency signals
    (
        re.compile(r"\b(quick|fast|brief|tldr|tl;dr|one[- ]?liner|short answer)\b", re.I),
        GoalMode.FAST,
    ),
    # ACCURATE: analysis, verification, depth
    (
        re.compile(
            r"\b(analyze|explain deeply|verify|prove|validate|check carefully|be precise|double[- ]?check|thorough)\b",
            re.I,
        ),
        GoalMode.ACCURATE,
    ),
    # CREATIVE: ideation, exploration (multi-word anchors to avoid false positives)
    (
        re.compile(
            r"\b(brainstorm\s+\w+|creative\s+\w+|imagine\s+\w+|innovate|explore\s+(?:ideas|options|possibilities|ways))\b",
            re.I,
        ),
        GoalMode.CREATIVE,
    ),
    # STRUCTURED: formatting, organization (anchored to avoid "format the disk" etc.)
    (
        re.compile(
            r"\b(organize|outline|list out|break down|categorize|format\s+(?:as|into|like|with)|create\s+a\s+table)\b",
            re.I,
        ),
        GoalMode.STRUCTURED,
    ),
]

# Short messages (at or below this word count) default to FAST
_SHORT_MESSAGE_THRESHOLD = 3


def infer_mode(message: str) -> GoalMode:
    """Infer goal mode from message text using deterministic heuristics.

    Rules checked in priority order — first match wins.
    Falls back to DEFAULT if no pattern matches.
    """
    if not message or not message.strip():
        return GoalMode.DEFAULT

    stripped = message.strip()

    # Very short messages → FAST
    if len(stripped.split()) <= _SHORT_MESSAGE_THRESHOLD and not any(
        p.search(stripped) for p, m in _INFERENCE_RULES if m != GoalMode.FAST
    ):
        return GoalMode.FAST

    # Pattern matching
    for pattern, mode in _INFERENCE_RULES:
        if pattern.search(stripped):
            return mode

    return GoalMode.DEFAULT


def resolve_mode(
    explicit: str | None = None,
    message: str | None = None,
) -> GoalMode:
    """Resolve goal mode with priority: explicit > inferred > DEFAULT.

    Args:
        explicit: Mode string from caller (e.g. "fast", "ACCURATE").
                  If invalid, falls through to inference.
        message: Message text for heuristic inference.

    Returns:
        Resolved GoalMode enum value.
    """
    if explicit is not None:
        try:
            return GoalMode(explicit.lower().strip())
        except ValueError:
            _log.debug("Invalid explicit goal_mode '%s', falling back to inference", explicit)

    if message is not None:
        return infer_mode(message)

    return GoalMode.DEFAULT
