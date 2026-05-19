"""Outcome socket — outbound result notifications to integrations."""

from __future__ import annotations

import logging

from services.umh.sockets.envelopes import OutcomeEnvelope
from services.umh.sockets.protocols import OutcomeReceiver

logger = logging.getLogger(__name__)


class OutcomeSocket:
    """Delivers outcome notifications to registered integrations.

    Two delivery modes:
    - notify(): sends to the originating integration only
    - notify_all(): broadcasts to all registered receivers

    Receivers must not block. on_outcome() is fire-and-forget from
    UMH's perspective — the socket catches and logs exceptions but
    does not retry. Long-running receivers should defer work to a
    background task (e.g., threading.Thread or asyncio.create_task)
    rather than blocking the notification path. UMH does not enforce
    this — it's a contract between the integration and its own
    runtime.
    """

    def __init__(self) -> None:
        self._receivers: dict[str, OutcomeReceiver] = {}

    def register_receiver(self, receiver: OutcomeReceiver) -> None:
        """Register an integration's outcome receiver.

        Raises ValueError if integration_id is already registered.
        """
        iid = receiver.integration_id
        if iid in self._receivers:
            raise ValueError(f"integration '{iid}' already registered as outcome receiver")
        self._receivers[iid] = receiver
        logger.info("outcome receiver registered: %s", iid)

    def notify(self, envelope: OutcomeEnvelope) -> None:
        """Send outcome to the originating integration only."""
        receiver = self._receivers.get(envelope.integration_id)
        if receiver is None:
            logger.debug(
                "no outcome receiver for integration '%s'",
                envelope.integration_id,
            )
            return
        self._deliver(receiver, envelope)

    def notify_all(self, envelope: OutcomeEnvelope) -> None:
        """Broadcast outcome to all registered receivers."""
        for receiver in self._receivers.values():
            self._deliver(receiver, envelope)

    def _deliver(self, receiver: OutcomeReceiver, envelope: OutcomeEnvelope) -> None:
        accepted = receiver.accepts_outcomes()
        if accepted and envelope.outcome_type not in accepted:
            return
        try:
            receiver.on_outcome(envelope)
        except Exception as exc:
            logger.error(
                "outcome receiver '%s' raised %s: %s",
                receiver.integration_id,
                type(exc).__name__,
                exc,
            )

    def registered_receivers(self) -> list[str]:
        return list(self._receivers.keys())
