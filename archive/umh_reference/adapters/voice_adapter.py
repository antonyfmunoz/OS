"""Voice adapter — speaks lifecycle event summaries via TTS.

Subscribes to completion events (ritual_completed, action_completed)
and speaks a short summary. Does NOT speak on every step event —
voice output is summary-level, not step-level.

Design rules:
- Short responses only — no full logs or payloads
- Non-blocking — delegates to TTSEngine (threaded)
- Never raises — adapter contract requires fail-safe behavior
- No substrate imports beyond SchedulerEvent for type reading
"""

from __future__ import annotations

import logging
from typing import Any

from umh.adapters.contracts import AdapterContext
from umh.adapters.tts_engine import TTSEngine

logger = logging.getLogger(__name__)

# ── Event types this adapter handles ─────────────────────────────────

_SUPPORTED_EVENTS = frozenset({
    "ritual_completed",
    "action_completed",
    "open_day_started",
    "close_day_started",
})


# ── Summary extractors ──────────────────────────────────────────────


def _summarize_ritual_completed(event: Any) -> str:
    """Extract spoken summary from ritual_completed event."""
    payload = getattr(event, "payload", {}) or {}
    result = payload.get("result", {})
    ritual_kind = getattr(event, "metadata", {}).get("ritual_kind", "ritual")

    if ritual_kind == "open_day":
        mode = result.get("mode_after", "")
        if mode:
            return f"Day opened. Mode: {mode}."
        return "Day opened. Ready."
    elif ritual_kind == "close_day":
        return "Day closed. Goodnight."
    return "Ritual complete."


def _summarize_action_completed(event: Any) -> str:
    """Extract spoken summary from action_completed event."""
    payload = getattr(event, "payload", {}) or {}
    result = payload.get("result", {})
    intent = result.get("intent_text", "")

    if intent:
        # Truncate long intents for speech
        short = intent[:80] + ("..." if len(intent) > 80 else "")
        return f"Done: {short}"
    return "Action complete."


def _summarize_day_started(event: Any) -> str:
    """Extract spoken summary from open/close_day_started event."""
    event_type = getattr(event, "event_type", "")
    if event_type == "open_day_started":
        return "Opening day."
    elif event_type == "close_day_started":
        return "Closing day."
    return ""


_SUMMARIZERS = {
    "ritual_completed": _summarize_ritual_completed,
    "action_completed": _summarize_action_completed,
    "open_day_started": _summarize_day_started,
    "close_day_started": _summarize_day_started,
}


# ── Adapter ──────────────────────────────────────────────────────────


class VoiceAdapter:
    """Adapter that speaks lifecycle event summaries via TTS.

    Satisfies the Adapter protocol (supports + handle).

    Args:
        tts: A TTSEngine instance to use for speech output.
    """

    def __init__(self, tts: TTSEngine) -> None:
        self._tts = tts

    def supports(self, event_type: str) -> bool:
        """Return True for completion and start events."""
        return event_type in _SUPPORTED_EVENTS

    def handle(self, event: Any, context: AdapterContext) -> None:
        """Extract summary from event and speak it.

        Never raises — logs and returns on failure.
        """
        event_type = getattr(event, "event_type", "")
        summarizer = _SUMMARIZERS.get(event_type)

        if summarizer is None:
            return

        try:
            text = summarizer(event)
            if text:
                logger.info(
                    "[VoiceAdapter] Speaking: %s (session=%s)",
                    text[:60],
                    context.runtime_session_id,
                )
                self._tts.speak(text)
        except Exception as exc:
            logger.warning("[VoiceAdapter] Failed to speak: %s", exc)
