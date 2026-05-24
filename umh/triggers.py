"""Trigger wrapper — wake producer + local listener for the workstation.

Wraps WakeProducerRuntime and LocalListener with CLI-friendly entry
points. Provides simulation helpers for wake word and clap detection,
manual activation, and trigger history display.

Real audio-based wake word and clap detection plug in later as producers
that call the substrate WakeProducerRuntime.submit(). This module
provides the workstation's interface to that infrastructure.

UMH workstation subsystem.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_NODE_ID = "workstation_local"


def _get_listener() -> Any:
    """Lazy-load substrate LocalListener."""
    try:
        from substrate.execution.bridge.local_listener import LocalListener

        return LocalListener()
    except ImportError:
        logger.debug("LocalListener not available")
        return None


def _get_wake_producer() -> Any:
    """Lazy-load substrate WakeProducerRuntime."""
    try:
        from substrate.execution.bridge.wake_producer import WakeProducerRuntime

        return WakeProducerRuntime()
    except ImportError:
        logger.debug("WakeProducerRuntime not available")
        return None


def manual_activate(
    node_id: str = _NODE_ID,
    requested_mode: str | None = None,
) -> dict[str, Any]:
    """Emit a manual activation trigger."""
    listener = _get_listener()
    if listener is None:
        return {"status": "skipped", "reason": "listener_unavailable"}

    try:
        trigger = listener.manual_activate(
            node_id=node_id,
            requested_mode=requested_mode,
        )
        return {
            "status": trigger.status.value,
            "trigger_id": trigger.trigger_id,
            "decision_reason": trigger.decision_reason,
            "ritual_id": trigger.ritual_id,
        }
    except Exception as exc:
        logger.debug("Manual activation failed: %s", exc)
        return {"status": "error", "reason": str(exc)}


def simulate_wake(
    phrase: str | None = None,
    node_id: str = _NODE_ID,
    confidence: float = 1.0,
) -> dict[str, Any]:
    """Simulate a wake word detection."""
    producer = _get_wake_producer()
    if producer is None:
        return {"action": "skipped", "reason": "wake_producer_unavailable"}

    try:
        event = producer.simulate_wake_word(
            node_id=node_id,
            phrase=phrase,
            confidence=confidence,
        )
        return {
            "action": event.action_taken,
            "event_id": event.event_id,
            "role_hint": event.role_hint,
            "voice_session_id": event.voice_session_id,
            "decision_reason": event.decision_reason,
        }
    except Exception as exc:
        logger.debug("Wake simulation failed: %s", exc)
        return {"action": "error", "reason": str(exc)}


def simulate_clap(
    node_id: str = _NODE_ID,
    confidence: float = 1.0,
) -> dict[str, Any]:
    """Simulate a clap detection (triggers open_day ritual)."""
    producer = _get_wake_producer()
    if producer is None:
        return {"action": "skipped", "reason": "wake_producer_unavailable"}

    try:
        event = producer.simulate_clap(
            node_id=node_id,
            confidence=confidence,
        )
        return {
            "action": event.action_taken,
            "event_id": event.event_id,
            "local_trigger_id": event.local_trigger_id,
            "decision_reason": event.decision_reason,
        }
    except Exception as exc:
        logger.debug("Clap simulation failed: %s", exc)
        return {"action": "error", "reason": str(exc)}


def get_trigger_history(
    limit: int = 10,
    node_id: str | None = None,
) -> list[dict[str, Any]]:
    """Get recent trigger history."""
    try:
        from substrate.execution.bridge.local_listener import get_trigger_history

        history = get_trigger_history()
        return history.latest(limit=limit, node_id=node_id)
    except ImportError:
        return []


def get_wake_history(
    limit: int = 10,
    node_id: str | None = None,
) -> list[dict[str, Any]]:
    """Get recent wake producer history."""
    try:
        from substrate.execution.bridge.wake_producer import get_wake_producer_history

        history = get_wake_producer_history()
        return history.latest(limit=limit, node_id=node_id)
    except ImportError:
        return []


def show_triggers() -> int:
    """Display trigger status and history for CLI."""
    print()
    print("Trigger History")
    print("=" * 40)

    triggers = get_trigger_history(limit=10)
    if not triggers:
        print("  No recent triggers.")
    else:
        for t in triggers:
            kind = t.get("kind", "?")
            status = t.get("status", "?")
            occurred = t.get("occurred_at", "?")
            if isinstance(occurred, str) and len(occurred) > 19:
                occurred = occurred[:19]
            reason = t.get("decision_reason", "")
            print(f"  [{status}] {kind} at {occurred}")
            if reason:
                print(f"         {reason[:60]}")

    print()
    print("Wake Producer History")
    print("-" * 40)

    wakes = get_wake_history(limit=5)
    if not wakes:
        print("  No recent wake events.")
    else:
        for w in wakes:
            kind = w.get("producer_kind", "?")
            action = w.get("action_taken", "?")
            phrase = w.get("detected_phrase", "")
            occurred = w.get("occurred_at", "?")
            if isinstance(occurred, str) and len(occurred) > 19:
                occurred = occurred[:19]
            label = f"{kind}"
            if phrase:
                label += f' "{phrase}"'
            print(f"  [{action}] {label} at {occurred}")

    print()
    return 0
