"""Discord adapter — real side-effect implementation.

Routes lifecycle events to Discord via webhook. This is the ONLY file
in the adapter layer that imports Discord utilities.

All calls are wrapped in try/except — adapter failures are logged,
never raised. The lifecycle always completes.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv

from umh.adapters.contracts import AdapterContext

load_dotenv("/opt/OS/umh/.env")

logger = logging.getLogger(__name__)

_SUPPORTED_EVENTS = frozenset(
    {
        "open_day_started",
        "ritual_step_executed",
        "close_day_started",
        "ritual_completed",
    }
)

# ─── Message templates ────────────────────────────────────────────────

_OPEN_MSG = "Session started — {transport}"
_STEP_MSG = "• {step_name}"
_CLOSE_MSG = "Closing session"
_COMPLETE_MSG = "Session complete — {steps} steps, presence → {presence}"


def _format_message(event: Any, context: AdapterContext) -> str:
    """Build a concise Discord message from a lifecycle event."""
    etype = event.event_type
    payload = event.payload if hasattr(event, "payload") else {}
    metadata = event.metadata if hasattr(event, "metadata") else {}

    if etype == "open_day_started":
        transport = context.state_snapshot.get("entry_transport", "unknown")
        plan_summary = payload.get("summary", "")
        msg = _OPEN_MSG.format(transport=transport)
        if plan_summary:
            msg += f"\n{plan_summary}"
        return msg

    if etype == "ritual_step_executed":
        step_name = payload.get("step_name", metadata.get("step_name", "step"))
        return _STEP_MSG.format(step_name=step_name)

    if etype == "close_day_started":
        return _CLOSE_MSG

    if etype == "ritual_completed":
        steps = payload.get("steps_executed", [])
        presence = payload.get("presence_after", "")
        return _COMPLETE_MSG.format(
            steps=len(steps) if isinstance(steps, (list, tuple)) else "?",
            presence=presence or "unknown",
        )

    return f"[{etype}]"


class DiscordAdapter:
    """Posts lifecycle events to Discord via webhook.

    Uses the existing post_to_webhook() from discord_utils — never
    builds custom HTTP calls.
    """

    def __init__(self, webhook_url: str = "") -> None:
        self._webhook_url = webhook_url or os.getenv("DISCORD_BRIEF_WEBHOOK", "")

    def supports(self, event_type: str) -> bool:
        return event_type in _SUPPORTED_EVENTS

    def handle(self, event: Any, context: AdapterContext) -> None:
        """Post a concise message to Discord. Never raises."""
        try:
            from umh.runtime_engine.discord_utils import post_to_webhook

            message = _format_message(event, context)
            post_to_webhook(
                content=message,
                username="EOS",
                webhook_url=self._webhook_url,
            )
            logger.info(
                "[DiscordAdapter] Sent %s (correlation=%s)",
                event.event_type,
                context.correlation_id,
            )
        except Exception:
            logger.exception(
                "[DiscordAdapter] Failed on %s (correlation=%s)",
                event.event_type,
                context.correlation_id,
            )
