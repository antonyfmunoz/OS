"""
Operator presence — tiny deterministic hybrid intro/outro templates.

This is the ENTIRE "cinematic EA presence" layer. On purpose.

There is no LLM here. There is no prompt template engine. There is no
randomness beyond a tiny deterministic rotation. The premise of the
operator state engine is that the *state machine* is the experience, and
this module just gives that state machine a small, premium, intentional
voice when it crosses a meaningful threshold.

Hybrid tone rules:
  - Short. Under 80 characters.
  - Declarative. No questions, no hedging.
  - Operator-aware. Mention what just happened, not generic greetings.
  - Premium. Sparse, intentional. No emoji. No exclamation marks.

Use:
    from eos_ai.substrate.operator_presence import intro_for_transition

    line = intro_for_transition(decision)
    if line:
        propose_speak_text(node_id, line, issued_by="operator_presence")

The caller decides whether to actually speak the line — this module never
proposes actions itself, so it stays additive and free of trust concerns.
"""

from __future__ import annotations

from typing import Optional

from eos_ai.substrate.operator_state import OperatorMode

# Bounded template table. Keyed by (from_mode_or_None, to_mode). Tiny.
# When more than one line exists, callers can rotate by index — but the
# default behavior is "always pick the first" so the experience stays
# deterministic and the tests are stable.
_TEMPLATES: dict[tuple[Optional[str], str], list[str]] = {
    # Cold start: idle → starting (someone just woke EOS)
    (OperatorMode.IDLE.value, OperatorMode.STARTING.value): [
        "Operator mode loading. Stand by.",
    ],
    (None, OperatorMode.STARTING.value): [
        "Operator mode loading. Stand by.",
    ],
    # Warm start: starting → active (voice session live)
    (OperatorMode.STARTING.value, OperatorMode.ACTIVE.value): [
        "Operator mode live. Ready.",
    ],
    # Cold direct → active (rare; wake straight into existing session)
    (OperatorMode.IDLE.value, OperatorMode.ACTIVE.value): [
        "Back online. Operator mode is live.",
    ],
    # Resume: any → active from active itself is filtered out by the
    # transition recorder (no mode change), so this only fires on real
    # transitions.
    # Focused: entering a scoped scene
    (OperatorMode.ACTIVE.value, OperatorMode.FOCUSED.value): [
        "Focused scene engaged.",
    ],
    (OperatorMode.STARTING.value, OperatorMode.FOCUSED.value): [
        "Focused scene engaged. Ready.",
    ],
    # Closing
    (OperatorMode.ACTIVE.value, OperatorMode.CLOSING.value): [
        "Closing out. Overnight processes remain active.",
    ],
    (OperatorMode.FOCUSED.value, OperatorMode.CLOSING.value): [
        "Closing out. Overnight processes remain active.",
    ],
    # Closed
    (OperatorMode.CLOSING.value, OperatorMode.IDLE.value): [
        "Closed. Standing down.",
    ],
    # Voice ended without close
    (OperatorMode.ACTIVE.value, OperatorMode.IDLE.value): [
        "Session released.",
    ],
    (OperatorMode.FOCUSED.value, OperatorMode.IDLE.value): [
        "Focused scene released.",
    ],
    # Unavailable
    (OperatorMode.ACTIVE.value, OperatorMode.UNAVAILABLE.value): [
        "Workstation unavailable. Holding state.",
    ],
}


def line_for_transition(
    from_mode: Optional[str], to_mode: str, *, index: int = 0
) -> Optional[str]:
    """Return a deterministic hybrid line for a (from_mode, to_mode) pair.

    Returns None if no template is registered. Callers must treat None as
    "stay silent" — that is the correct premium default.
    """
    options = _TEMPLATES.get((from_mode, to_mode))
    if not options:
        # Try a wildcard fallback that ignores the from_mode.
        options = _TEMPLATES.get((None, to_mode))
    if not options:
        return None
    if index < 0:
        index = 0
    return options[index % len(options)]


def intro_for_transition(transition) -> Optional[str]:
    """Convenience: pull the line for an OperatorTransition record."""
    if transition is None:
        return None
    try:
        return line_for_transition(transition.from_mode, transition.to_mode)
    except Exception:
        return None


__all__ = ["line_for_transition", "intro_for_transition"]
