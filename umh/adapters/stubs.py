"""Stub adapters — minimal implementations for initial integration testing.

Each stub logs symbolic behavior without making real API calls.
Replace with real implementations when integrations are wired up.
"""

from __future__ import annotations

import logging
from typing import Any

from umh.adapters.contracts import AdapterContext

logger = logging.getLogger(__name__)

# ─── Event type → symbolic action maps ────────────────────────────────

_DISCORD_ACTIONS: dict[str, str] = {
    "open_day_started": "send greeting",
    "ritual_step_executed": "update status",
    "close_day_started": "send summary",
    "ritual_completed": "attach artifact",
}

_NOTION_ACTIONS: dict[str, str] = {
    "open_day_started": "create day page",
    "ritual_step_executed": "log step to page",
    "close_day_started": "update day summary",
    "ritual_completed": "mark day complete",
}

_WORKSTATION_ACTIONS: dict[str, str] = {
    "open_day_started": "open workspace",
    "ritual_step_executed": "focus window",
    "close_day_started": "save workspace state",
    "ritual_completed": "close workspace",
}


# ─── Stub implementations ─────────────────────────────────────────────


class DiscordAdapter:
    """Stub: logs Discord-like actions without calling the API."""

    def supports(self, event_type: str) -> bool:
        return event_type in _DISCORD_ACTIONS

    def handle(self, event: Any, context: AdapterContext) -> None:
        action = _DISCORD_ACTIONS[event.event_type]
        logger.info(
            "[DiscordAdapter] %s → %s (session=%s, correlation=%s)",
            event.event_type,
            action,
            context.runtime_session_id,
            context.correlation_id,
        )


class NotionAdapter:
    """Stub: logs Notion-like actions without calling the API."""

    def supports(self, event_type: str) -> bool:
        return event_type in _NOTION_ACTIONS

    def handle(self, event: Any, context: AdapterContext) -> None:
        action = _NOTION_ACTIONS[event.event_type]
        logger.info(
            "[NotionAdapter] %s → %s (session=%s, correlation=%s)",
            event.event_type,
            action,
            context.runtime_session_id,
            context.correlation_id,
        )


class WorkstationAdapter:
    """Stub: logs workstation-like actions without calling the API."""

    def supports(self, event_type: str) -> bool:
        return event_type in _WORKSTATION_ACTIONS

    def handle(self, event: Any, context: AdapterContext) -> None:
        action = _WORKSTATION_ACTIONS[event.event_type]
        logger.info(
            "[WorkstationAdapter] %s → %s (session=%s, correlation=%s)",
            event.event_type,
            action,
            context.runtime_session_id,
            context.correlation_id,
        )
