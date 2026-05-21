"""Brain signals — append-only inter-brain coordination messages.

BrainSignals are lightweight, typed messages that brains emit to
coordinate without direct coupling. They flow through the event bus
but are also stored in a dedicated per-brain log for replay.

Signals are append-only — once emitted, they cannot be modified or deleted.
This mirrors the substrate's event stream contract.

Usage:
    from umh.brains.signals import emit_signal, list_signals

    emit_signal("system", "startup", {"stage": "ambient"})
    recent = list_signals("system", limit=10)
"""

from __future__ import annotations

import threading
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now


_MAX_SIGNALS_PER_BRAIN = 500


@dataclass(frozen=True)
class BrainSignal:
    """Immutable signal emitted by a brain.

    signal_type: categorizes the signal (e.g. "correction", "startup",
                 "delegation", "observation", "escalation").
    """

    signal_id: str
    brain_id: str
    signal_type: str
    payload: dict[str, Any]
    timestamp: str
    target_brain_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "brain_id": self.brain_id,
            "signal_type": self.signal_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "target_brain_id": self.target_brain_id,
        }


# ─── Signal store ──────────────────────────────────────────────────────

_lock = threading.Lock()
_signals: dict[str, deque[BrainSignal]] = defaultdict(lambda: deque(maxlen=_MAX_SIGNALS_PER_BRAIN))
_all_signals: deque[BrainSignal] = deque(maxlen=_MAX_SIGNALS_PER_BRAIN * 10)


def _publish(event_type: str, payload: dict[str, Any]) -> None:
    """Best-effort event publishing — never crashes."""
    try:
        from umh.events.stream import publish

        publish(event_type, payload=payload, actor_id="brain_signals")
    except Exception:
        pass


# ─── Public API ────────────────────────────────────────────────────────


def emit_signal(
    brain_id: str,
    signal_type: str,
    payload: dict[str, Any] | None = None,
    *,
    target_brain_id: str = "",
) -> BrainSignal:
    """Emit a brain signal. Append-only — cannot be modified after creation."""
    signal = BrainSignal(
        signal_id=f"bsig_{uuid.uuid4().hex[:12]}",
        brain_id=brain_id,
        signal_type=signal_type,
        payload=payload or {},
        timestamp=_iso_now(),
        target_brain_id=target_brain_id,
    )

    with _lock:
        _signals[brain_id].append(signal)
        _all_signals.append(signal)

    _publish(
        "brain.signal_emitted",
        {
            "signal_id": signal.signal_id,
            "brain_id": brain_id,
            "signal_type": signal_type,
            "target": target_brain_id,
        },
    )
    return signal


def list_signals(
    brain_id: str,
    *,
    signal_type: str | None = None,
    limit: int = 50,
) -> list[BrainSignal]:
    """List signals emitted by a specific brain, newest first."""
    with _lock:
        signals = list(_signals.get(brain_id, []))

    if signal_type:
        signals = [s for s in signals if s.signal_type == signal_type]

    return list(reversed(signals[-limit:]))


def list_signals_for_target(
    target_brain_id: str,
    *,
    signal_type: str | None = None,
    limit: int = 50,
) -> list[BrainSignal]:
    """List signals targeted at a specific brain, newest first."""
    with _lock:
        signals = [s for s in _all_signals if s.target_brain_id == target_brain_id]

    if signal_type:
        signals = [s for s in signals if s.signal_type == signal_type]

    return list(reversed(signals[-limit:]))


def list_all_signals(
    *,
    signal_type: str | None = None,
    limit: int = 100,
) -> list[BrainSignal]:
    """List all signals across all brains, newest first."""
    with _lock:
        signals = list(_all_signals)

    if signal_type:
        signals = [s for s in signals if s.signal_type == signal_type]

    return list(reversed(signals[-limit:]))


def get_signal(signal_id: str) -> BrainSignal | None:
    """Retrieve a signal by ID. O(n) scan — use for debugging only."""
    with _lock:
        for s in reversed(_all_signals):
            if s.signal_id == signal_id:
                return s
    return None


def signal_count(brain_id: str | None = None) -> int:
    """Count signals for a brain, or all signals if brain_id is None."""
    with _lock:
        if brain_id:
            return len(_signals.get(brain_id, []))
        return len(_all_signals)


def clear() -> None:
    """Reset all signals — for testing only."""
    with _lock:
        _signals.clear()
        _all_signals.clear()
