"""EOS outcome receiver — Phase 1 stub, logs only."""

from __future__ import annotations

import logging

from services.umh.sockets.envelopes import OutcomeEnvelope

from .correlation import EOSCorrelationMap
from .manifest import INTEGRATION_ID

logger = logging.getLogger(__name__)


class EOSOutcomeReceiver:
    """Receives pipeline outcomes for EOS signals. Phase 1: log only.

    Satisfies OutcomeReceiver Protocol structurally.
    Phase 4 will add writeback to EOS tables.
    """

    def __init__(self, correlation_map: EOSCorrelationMap) -> None:
        self._correlation_map = correlation_map

    @property
    def integration_id(self) -> str:
        return INTEGRATION_ID

    def on_outcome(self, envelope: OutcomeEnvelope) -> None:
        if envelope.correlation_id is None:
            return

        target = self._correlation_map.lookup(envelope.correlation_id)
        if target is None:
            return

        logger.info(
            "eos outcome received: org=%s table=%s row=%s type=%s (writeback not implemented — Phase 4)",
            target.org_id,
            target.table_name,
            target.row_id,
            envelope.outcome_type,
        )

        self._correlation_map.remove(envelope.correlation_id)

    def accepts_outcomes(self) -> list[str]:
        return []
