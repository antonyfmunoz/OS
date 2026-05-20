"""Notion signal emitter — builds SignalEnvelopes from polled Notion pages."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from services.umh.protocols.signal import SignalUrgency
from services.umh.sockets.envelopes import SignalEnvelope
from services.umh.sockets.protocols import SignalDescriptor

from .manifest import INTEGRATION_ID, SIGNAL_DESCRIPTORS

logger = logging.getLogger(__name__)


class NotionSignalEmitter:
    """Declares signal types and builds envelopes from polled Notion pages.

    Satisfies SignalEmitter Protocol structurally.
    """

    @property
    def integration_id(self) -> str:
        return INTEGRATION_ID

    def describe_signals(self) -> list[SignalDescriptor]:
        return list(SIGNAL_DESCRIPTORS)

    def build_signal(
        self,
        page: dict[str, Any],
        signal_source_config: dict[str, Any],
    ) -> tuple[SignalEnvelope, dict[str, Any]]:
        """Build a SignalEnvelope + writeback_to dict from a polled Notion page.

        Returns (envelope, writeback_to) where writeback_to is
        {"page_id": ..., "integration": "notion"} for outcome routing.
        """
        page_id = page["id"]
        database_id = signal_source_config.get("database_id", "")
        operation = signal_source_config.get("operation", "noop")

        title = _extract_title(page)
        last_edited = page.get("last_edited_time", "")

        correlation_id = uuid4()

        envelope = SignalEnvelope(
            integration_id=INTEGRATION_ID,
            content_type="page_updated",
            payload={
                "page_id": page_id,
                "database_id": database_id,
                "title": title,
                "last_edited_time": last_edited,
                "adapter_name": "notion",
                "operation": operation,
                "page_properties": _extract_properties(page),
            },
            raw_content=title,
            source_identifier=f"notion:page:{page_id}",
            correlation_id=correlation_id,
            urgency=SignalUrgency.NORMAL,
            metadata={
                "poll_source": signal_source_config.get("logical_name", ""),
            },
        )

        writeback_to = {"page_id": page_id, "integration": "notion"}

        return envelope, writeback_to


def _extract_title(page: dict[str, Any]) -> str:
    """Best-effort title extraction from Notion page properties."""
    props = page.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            title_parts = prop.get("title", [])
            if title_parts:
                return "".join(t.get("plain_text", "") for t in title_parts)
    return "Untitled"


def _extract_properties(page: dict[str, Any]) -> dict[str, Any]:
    """Extract a simplified properties dict from a Notion page."""
    result: dict[str, Any] = {}
    for name, prop in page.get("properties", {}).items():
        prop_type = prop.get("type", "unknown")
        if prop_type == "title":
            parts = prop.get("title", [])
            result[name] = "".join(t.get("plain_text", "") for t in parts)
        elif prop_type == "select":
            sel = prop.get("select")
            result[name] = sel.get("name", "") if sel else ""
        elif prop_type == "rich_text":
            parts = prop.get("rich_text", [])
            result[name] = "".join(t.get("plain_text", "") for t in parts)
        else:
            result[name] = f"<{prop_type}>"
    return result
