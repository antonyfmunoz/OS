"""
AdaptivePromptLayer — shapes prompts using past outcome signals.

Reads evaluation history from SessionRuntime and high-confidence patterns
from WorldModel. Prepends behavioral directives to the system prompt so
the LLM is biased toward higher-performing response patterns.

No LLM calls. Pure signal reading + deterministic rule application.

Usage::

    from umh.reasoning.adaptive_prompt import adapt_prompt

    adapted = adapt_prompt(
        base_prompt="...",
        context={"agent_type": "executive_assistant", "venture_id": "lyfe_institute"},
        session_runtime=session,
        world_model=wm,
    )
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from umh.world.calibration import CalibratedThresholds
    from umh.runtime_engine.session_runtime import SessionRuntime
    from umh.world.model import WorldModel

LOW_QUALITY_THRESHOLD = 0.45
STREAK_LENGTH = 3
HIGH_CONFIDENCE_THRESHOLD = 0.6
MAX_DIRECTIVES = 3
MAX_SESSION_HISTORY = 10

PRIORITY_UNIFIED_INFLUENCE = -2
PRIORITY_GOAL = -1
PRIORITY_CRITICAL = 0
PRIORITY_LOW_QUALITY = 1
PRIORITY_WORLD_MODEL = 2


def adapt_prompt(
    base_prompt: str,
    context: dict | None = None,
    session_runtime: "SessionRuntime | None" = None,
    world_model: "WorldModel | None" = None,
    thresholds: "CalibratedThresholds | None" = None,
) -> str:
    """Apply adaptive directives based on past outcome signals.

    Returns the original prompt with zero or more directive blocks prepended.
    If no signals warrant adaptation, returns ``base_prompt`` unchanged.

    When ``thresholds`` is provided, uses calibrated values for quality
    and confidence gates. Otherwise falls back to module-level constants.

    Directives are prioritized and capped at MAX_DIRECTIVES to prevent
    prompt over-steering. Priority order:
        0: critical failure signals (hallucination, errors)
        1: low-quality streak signals
        2: world model reinforcement
    """
    context = context or {}
    prioritized: list[tuple[int, str]] = []

    lq_thresh = (
        thresholds.low_quality_threshold if thresholds else LOW_QUALITY_THRESHOLD
    )
    hc_thresh = (
        thresholds.high_confidence_threshold
        if thresholds
        else HIGH_CONFIDENCE_THRESHOLD
    )

    if session_runtime is not None:
        _apply_goal_directives(session_runtime, prioritized)
        _apply_unified_influence(session_runtime, prioritized)
        _apply_session_signals(session_runtime, prioritized, lq_thresh)

    if world_model is not None:
        _apply_world_model_signals(world_model, context, prioritized, hc_thresh)

    if not prioritized:
        return base_prompt

    prioritized.sort(key=lambda x: x[0])
    seen: set[str] = set()
    deduped: list[str] = []
    for _, directive in prioritized:
        if directive not in seen:
            seen.add(directive)
            deduped.append(directive)

    capped = deduped[:MAX_DIRECTIVES]

    block = "## Adaptive Response Guidance\n" + "\n".join(f"- {d}" for d in capped)
    return f"{block}\n\n{base_prompt}"


def _get_prompt_flags(evaluation: dict) -> dict:
    """Extract prompt-relevant flags from an evaluation dict.

    Prefers the attributed ``signals.prompt.flags`` path when available,
    falling back to the flat ``flags`` dict for backward compatibility.
    """
    signals = evaluation.get("signals")
    if signals and isinstance(signals, dict):
        prompt_sig = signals.get("prompt")
        if prompt_sig and isinstance(prompt_sig, dict):
            return prompt_sig.get("flags", {})
    return evaluation.get("flags", {})


def _apply_goal_directives(
    session_runtime: "SessionRuntime",
    prioritized: list[tuple[int, str]],
) -> None:
    """Inject goal-conditioned directives from the unified influence.

    Goal directives travel separately from control/convergence directives
    and slot between unified influence (highest) and critical signals.
    Empty goal_directives (no active goal) adds nothing.
    """
    try:
        influence = session_runtime.get_unified_influence()
        for directive in influence.goal_directives:
            prioritized.append((PRIORITY_GOAL, directive))
    except Exception:
        pass


def _apply_unified_influence(
    session_runtime: "SessionRuntime",
    prioritized: list[tuple[int, str]],
) -> None:
    """Inject directives from the unified influence orchestrator.

    These come pre-sorted by priority (control first, then convergence)
    and pre-deduplicated, so they are added at the highest adaptive
    priority to ensure they are never displaced by session signals.
    """
    try:
        influence = session_runtime.get_unified_influence()
        for directive in influence.directives:
            prioritized.append((PRIORITY_UNIFIED_INFLUENCE, directive))
    except Exception:
        pass


def _apply_session_signals(
    session_runtime: "SessionRuntime",
    prioritized: list[tuple[int, str]],
    lq_threshold: float = LOW_QUALITY_THRESHOLD,
) -> None:
    """Read recent evaluations and inject corrective directives with priority.

    Reads only the last MAX_SESSION_HISTORY evaluations to keep the
    session horizon bounded. Streak detection uses the most recent
    STREAK_LENGTH entries within that window.
    """
    evaluations = session_runtime.stats.evaluations
    if not evaluations:
        return

    capped = evaluations[-MAX_SESSION_HISTORY:]
    recent = capped[-STREAK_LENGTH:]

    prompt_flags_list = [_get_prompt_flags(e) for e in recent]

    # Hallucination streak — CRITICAL priority
    halluc_count = sum(1 for f in prompt_flags_list if f.get("hallucination_risk"))
    if halluc_count >= 2:
        prioritized.append(
            (
                PRIORITY_CRITICAL,
                "Recent responses showed hallucination risk. "
                "Only state facts you are confident about. "
                "If uncertain, say so explicitly.",
            )
        )

    # Incomplete streak — CRITICAL priority
    incomplete_count = sum(1 for f in prompt_flags_list if f.get("incomplete"))
    if incomplete_count >= 2:
        prioritized.append(
            (
                PRIORITY_CRITICAL,
                "Recent responses appeared incomplete. "
                "Ensure your response has a clear conclusion.",
            )
        )

    # Low-quality streak — uses flag presence, not raw score
    low_quality_count = sum(1 for f in prompt_flags_list if f.get("low_information"))
    scores = [e.get("quality_score", 0.5) for e in recent]
    avg_score = sum(scores) / len(scores)
    if len(recent) >= STREAK_LENGTH and avg_score < lq_threshold:
        prioritized.append(
            (
                PRIORITY_LOW_QUALITY,
                "Recent responses scored low on quality. "
                "Be more precise, reduce verbosity, and ensure a direct answer.",
            )
        )

    # Low-information streak — LOW_QUALITY priority
    if low_quality_count >= 2:
        prioritized.append(
            (
                PRIORITY_LOW_QUALITY,
                "Recent responses lacked substance. "
                "Provide specific, actionable information.",
            )
        )


def _apply_world_model_signals(
    world_model: "WorldModel",
    context: dict,
    prioritized: list[tuple[int, str]],
    hc_threshold: float = HIGH_CONFIDENCE_THRESHOLD,
) -> None:
    """Read high-confidence success patterns and inject them as guidance."""
    try:
        from umh.analytics.pattern_engine import (
            extract_success_patterns,
            filter_redundant_patterns,
        )

        patterns = extract_success_patterns(
            world_model,
            limit=5,
            confidence_threshold=hc_threshold,
        )

        if not patterns:
            return

        existing_text = " ".join(d for _, d in prioritized)
        patterns = filter_redundant_patterns(patterns, existing_text)

        if not patterns:
            return

        prioritized.append(
            (
                PRIORITY_WORLD_MODEL,
                "High-performing response patterns to follow:\n"
                + "\n".join(f"  • {p}" for p in patterns[:5]),
            )
        )
    except Exception:
        pass
