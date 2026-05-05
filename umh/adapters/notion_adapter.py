"""Notion adapter — real side-effect implementation.

Routes lifecycle events to Notion as daily log pages. This is the ONLY
file in the adapter layer that imports Notion utilities.

Strategy:
- open_day_started  → create a new daily log page
- ritual_step_executed → append step entry to active page
- close_day_started → append summary section
- ritual_completed  → mark page complete with status property

Uses the existing notion_publisher infrastructure — never builds
custom Notion API calls.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from umh.adapters.contracts import AdapterContext

load_dotenv("/opt/OS/umh/.env")

logger = logging.getLogger(__name__)

PDT = ZoneInfo("America/Los_Angeles")

_SUPPORTED_EVENTS = frozenset(
    {
        "open_day_started",
        "ritual_step_executed",
        "close_day_started",
        "ritual_completed",
    }
)


def _get_activity_db_id() -> str:
    """Resolve the Notion activity log database ID."""
    return os.getenv("NOTION_ACTIVITY_ID", "")


def _today_title() -> str:
    now = datetime.now(PDT)
    return f"Daily Log — {now.strftime('%Y-%m-%d')}"


class NotionAdapter:
    """Appends lifecycle events to a Notion daily log page.

    Creates the page on open_day_started, appends to it for subsequent
    events. Page URL is cached in the adapter instance for the session.
    """

    def __init__(self, activity_db_id: str = "") -> None:
        self._activity_db_id = activity_db_id or _get_activity_db_id()
        self._active_page_id: str = ""

    def supports(self, event_type: str) -> bool:
        return event_type in _SUPPORTED_EVENTS

    def handle(self, event: Any, context: AdapterContext) -> None:
        """Route event to the appropriate Notion action. Never raises."""
        try:
            etype = event.event_type

            if etype == "open_day_started":
                self._create_day_page(event, context)
            elif etype == "ritual_step_executed":
                self._append_step(event, context)
            elif etype == "close_day_started":
                self._append_summary(event, context)
            elif etype == "ritual_completed":
                self._mark_complete(event, context)

            logger.info(
                "[NotionAdapter] %s handled (correlation=%s)",
                etype,
                context.correlation_id,
            )
        except Exception:
            logger.exception(
                "[NotionAdapter] Failed on %s (correlation=%s)",
                event.event_type,
                context.correlation_id,
            )

    def _create_day_page(self, event: Any, context: AdapterContext) -> None:
        """Create a new daily log page in the activity database."""
        from umh.runtime_engine.notion_publisher import _create_page, _heading, _paragraph

        if not self._activity_db_id:
            logger.warning("[NotionAdapter] No NOTION_ACTIVITY_ID configured")
            return

        title = _today_title()
        payload = event.payload if hasattr(event, "payload") else {}
        summary = payload.get("summary", "Session opened")

        blocks = [
            _heading("Session Start", level=2),
            _paragraph(summary),
            _paragraph(
                f"Transport: {context.state_snapshot.get('entry_transport', 'unknown')}"
            ),
            _paragraph(f"Correlation: {context.correlation_id}"),
        ]

        url = _create_page(self._activity_db_id, title, blocks)
        if url:
            # Extract page_id from URL for subsequent appends
            self._active_page_id = url.split("/")[-1] if "/" in url else ""
            logger.info("[NotionAdapter] Day page created: %s", url)
        else:
            logger.warning("[NotionAdapter] Day page creation failed")

    def _append_step(self, event: Any, context: AdapterContext) -> None:
        """Append a ritual step entry to the active page."""
        if not self._active_page_id:
            logger.debug("[NotionAdapter] No active page for step append")
            return

        from umh.runtime_engine.notion_publisher import _api_call, _bulleted

        payload = event.payload if hasattr(event, "payload") else {}
        metadata = event.metadata if hasattr(event, "metadata") else {}
        step_name = payload.get("step_name", metadata.get("step_name", "step"))

        block = _bulleted(f"Step: {step_name}")
        _api_call(
            "PATCH",
            f"/blocks/{self._active_page_id}/children",
            {"children": [block]},
        )

    def _append_summary(self, event: Any, context: AdapterContext) -> None:
        """Append a closing summary section to the active page."""
        if not self._active_page_id:
            logger.debug("[NotionAdapter] No active page for summary append")
            return

        from umh.runtime_engine.notion_publisher import _api_call, _divider, _heading, _paragraph

        payload = event.payload if hasattr(event, "payload") else {}
        summary = payload.get("summary", "Session closing")

        blocks = [
            _divider(),
            _heading("Session Close", level=2),
            _paragraph(summary),
        ]
        _api_call(
            "PATCH",
            f"/blocks/{self._active_page_id}/children",
            {"children": blocks},
        )

    def _mark_complete(self, event: Any, context: AdapterContext) -> None:
        """Append completion marker to the active page."""
        if not self._active_page_id:
            logger.debug("[NotionAdapter] No active page for completion")
            return

        from umh.runtime_engine.notion_publisher import _api_call, _divider, _paragraph

        payload = event.payload if hasattr(event, "payload") else {}
        steps = payload.get("steps_executed", [])
        presence = payload.get("presence_after", "")

        blocks = [
            _divider(),
            _paragraph(
                f"Session complete — {len(steps)} steps executed, "
                f"presence → {presence or 'unknown'}"
            ),
        ]
        _api_call(
            "PATCH",
            f"/blocks/{self._active_page_id}/children",
            {"children": blocks},
        )
        self._active_page_id = ""  # Reset for next session
