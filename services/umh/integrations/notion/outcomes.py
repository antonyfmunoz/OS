"""Notion outcome receiver — writes pipeline outcomes back to Notion pages."""

from __future__ import annotations

import logging
import time
from typing import Any

from notion_client import APIResponseError, Client

from services.umh.sockets.envelopes import OutcomeEnvelope

from .correlation import CorrelationMap
from .manifest import INTEGRATION_ID

logger = logging.getLogger(__name__)

_RETRY_STATUS = 429
_RETRY_BACKOFF_SECONDS = 2.0

_STATUS_MAP: dict[str, str] = {
    "success": "Success",
    "failure": "Error",
    "error": "Error",
    "governance_denied": "Blocked",
    "timeout": "Timeout",
}


class NotionOutcomeReceiver:
    """Receives pipeline outcomes and writes status back to Notion pages.

    Satisfies OutcomeReceiver Protocol structurally.
    Uses Notion SDK directly — writebacks are outcome side-effects,
    not new signals, so they bypass governance reentry.
    """

    def __init__(
        self,
        client: Client,
        correlation_map: CorrelationMap,
    ) -> None:
        self._client = client
        self._correlation_map = correlation_map

    @property
    def integration_id(self) -> str:
        return INTEGRATION_ID

    def on_outcome(self, envelope: OutcomeEnvelope) -> None:
        if envelope.correlation_id is None:
            logger.debug("notion outcome: no correlation_id, skipping writeback")
            return

        target = self._correlation_map.lookup(envelope.correlation_id)
        if target is None:
            logger.debug(
                "notion outcome: correlation_id %s not in map",
                envelope.correlation_id,
            )
            return

        if target.integration != "notion":
            logger.debug(
                "notion outcome: target integration is %s, not notion",
                target.integration,
            )
            return

        try:
            self._writeback(target.page_id, envelope)
            self._correlation_map.remove(envelope.correlation_id)
        except APIResponseError as exc:
            if exc.status == _RETRY_STATUS:
                self._retry_writeback(target.page_id, envelope)
            else:
                logger.error(
                    "notion writeback failed: %s %s for page %s",
                    exc.status,
                    exc.code,
                    target.page_id,
                )
        except Exception as exc:
            logger.error(
                "notion writeback failed: %s: %s for page %s",
                type(exc).__name__,
                exc,
                target.page_id,
            )

    def accepts_outcomes(self) -> list[str]:
        return []

    def _writeback(self, page_id: str, envelope: OutcomeEnvelope) -> None:
        status_label = _STATUS_MAP.get(envelope.outcome_type, "Unknown")

        self._client.pages.update(
            page_id=page_id,
            properties={
                "UMH Status": {"select": {"name": status_label}},
            },
        )

        callout_text = (
            f"[UMH] {envelope.outcome_type}: {envelope.summary[:200]}\ntrace: {envelope.trace_id}"
        )

        self._client.blocks.children.append(
            block_id=page_id,
            children=[
                {
                    "callout": {
                        "rich_text": [{"text": {"content": callout_text}}],
                        "icon": {"emoji": "🔔" if status_label == "Success" else "⚠️"},
                    }
                }
            ],
        )

        logger.info(
            "notion writeback: page=%s status=%s outcome=%s",
            page_id,
            status_label,
            envelope.outcome_type,
        )

    def _retry_writeback(self, page_id: str, envelope: OutcomeEnvelope) -> None:
        logger.warning("notion writeback 429 — retrying in %.1fs", _RETRY_BACKOFF_SECONDS)
        time.sleep(_RETRY_BACKOFF_SECONDS)
        try:
            self._writeback(page_id, envelope)
            self._correlation_map.remove(envelope.correlation_id)
        except Exception as exc:
            logger.error(
                "notion writeback failed after retry: %s: %s for page %s",
                type(exc).__name__,
                exc,
                page_id,
            )
