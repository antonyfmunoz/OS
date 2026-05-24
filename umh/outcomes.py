"""Outcome routing — receive and display substrate pipeline outcomes.

Extends WorkstationOutcomeReceiver with callback-based notification.
When the substrate pipeline completes processing a signal, the outcome
flows back here and is printed/spoken to the operator.

The outcome callback is registered at boot time. Recent outcomes are
buffered for the status display and CLI inspection.

UMH workstation subsystem.
"""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

_outcome_callback: Callable[[Any], None] | None = None
_BUFFER_MAX = 50
_recent_buffer: deque[Any] = deque(maxlen=_BUFFER_MAX)


def set_outcome_callback(callback: Callable[[Any], None]) -> None:
    """Register a callback invoked when outcomes arrive."""
    global _outcome_callback
    _outcome_callback = callback


def clear_module_state() -> None:
    """Reset module-level state between sessions in the same process."""
    global _outcome_callback
    _outcome_callback = None
    _recent_buffer.clear()


def on_outcome_received(envelope: Any) -> None:
    """Called by the WorkstationOutcomeReceiver — dispatches to callback."""
    _recent_buffer.append(envelope)

    if _outcome_callback is not None:
        try:
            _outcome_callback(envelope)
        except Exception as exc:
            logger.debug("Outcome callback failed: %s", exc)


def format_outcome(envelope: Any) -> str:
    """Format an OutcomeEnvelope for display."""
    outcome_type = getattr(envelope, "outcome_type", "unknown")
    summary = getattr(envelope, "summary", "")
    governance = getattr(envelope, "governance_decision", "")
    confidence = getattr(envelope, "confidence", 1.0)
    duration_ms = getattr(envelope, "duration_ms", 0.0)

    parts = [f"[{outcome_type}]"]
    if summary:
        parts.append(summary)
    if governance:
        parts.append(f"(governance: {governance})")
    if confidence < 1.0:
        parts.append(f"confidence={confidence:.0%}")
    if duration_ms > 0:
        parts.append(f"{duration_ms:.0f}ms")

    return " ".join(parts)


def get_recent_outcomes(receiver: Any = None, limit: int = 10) -> list[dict[str, Any]]:
    """Get recent outcomes from the module buffer or receiver."""
    if receiver is not None:
        try:
            source = list(receiver.recent_outcomes)
        except Exception as exc:
            logger.debug("Failed to read recent outcomes: %s", exc)
            source = []
    else:
        source = list(_recent_buffer)

    if not source:
        return []

    results: list[dict[str, Any]] = []
    for envelope in source[-limit:]:
        results.append(
            {
                "outcome_type": getattr(envelope, "outcome_type", "?"),
                "summary": getattr(envelope, "summary", ""),
                "governance_decision": getattr(envelope, "governance_decision", ""),
                "confidence": getattr(envelope, "confidence", 1.0),
                "duration_ms": getattr(envelope, "duration_ms", 0.0),
            }
        )
    return results


def show_outcomes(receiver: Any = None) -> int:
    """Display recent outcomes for CLI."""
    print()
    print("Pipeline Outcomes")
    print("=" * 40)

    outcomes = get_recent_outcomes(receiver)
    if not outcomes:
        print("  No recent outcomes.")
    else:
        print(f"  {len(outcomes)} recent outcome(s):")
        print()
        for o in outcomes:
            otype = o.get("outcome_type", "?")
            summary = o.get("summary", "")
            gov = o.get("governance_decision", "")
            duration = o.get("duration_ms", 0.0)
            print(f"  [{otype}] {summary}")
            if gov:
                print(f"         governance: {gov}")
            if duration > 0:
                print(f"         {duration:.0f}ms")

    print()
    return 0
