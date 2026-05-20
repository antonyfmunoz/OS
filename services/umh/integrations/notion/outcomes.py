"""Notion outcome receiver — implements OutcomeReceiver Protocol."""

from __future__ import annotations

import logging

from services.umh.sockets.envelopes import OutcomeEnvelope

from .manifest import INTEGRATION_ID

logger = logging.getLogger(__name__)


class NotionOutcomeReceiver:
    """Receives pipeline outcomes for Notion-originated signals.

    Phase 1: logs outcomes only — no Notion writeback.
    """

    @property
    def integration_id(self) -> str:
        return INTEGRATION_ID

    def on_outcome(self, envelope: OutcomeEnvelope) -> None:
        logger.info(
            "notion outcome: type=%s summary=%s",
            envelope.outcome_type,
            envelope.summary[:120] if envelope.summary else "",
        )

    def accepts_outcomes(self) -> list[str]:
        return []
