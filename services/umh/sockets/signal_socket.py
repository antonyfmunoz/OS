"""Signal socket — inbound intake for external integrations."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from services.umh.sockets.envelopes import SignalEnvelope, SignalReceipt
from services.umh.sockets.protocols import SignalDescriptor, SignalEmitter

logger = logging.getLogger(__name__)


class SignalSocket:
    """UMH's inbound socket for external signals.

    Integrations register as emitters, then push signals via emit().
    The socket validates the envelope against the emitter's declared
    signal catalog, converts to the internal Signal protocol, and
    submits to the pipeline.
    """

    def __init__(self) -> None:
        self._emitters: dict[str, SignalEmitter] = {}
        self._catalogs: dict[str, list[SignalDescriptor]] = {}

    def register_emitter(self, emitter: SignalEmitter) -> None:
        """Register an integration's signal emitter.

        Raises ValueError if integration_id is already registered.
        """
        iid = emitter.integration_id
        if iid in self._emitters:
            raise ValueError(f"integration '{iid}' already registered as signal emitter")
        self._emitters[iid] = emitter
        self._catalogs[iid] = emitter.describe_signals()
        logger.info(
            "signal emitter registered: %s (%d signal types)",
            iid,
            len(self._catalogs[iid]),
        )

    def emit(self, envelope: SignalEnvelope) -> SignalReceipt:
        """Accept a signal from a registered integration.

        Validates the envelope against the emitter's catalog, then
        returns a receipt. Pipeline submission is wired externally —
        this method handles validation and receipt generation only.
        Callers attach the pipeline dispatch via on_signal callback.
        """
        now = datetime.now(timezone.utc)

        if envelope.integration_id not in self._emitters:
            return SignalReceipt(
                signal_id=UUID(int=0),
                trace_id=UUID(int=0),
                accepted=False,
                accepted_at=now,
                rejection_reason=f"integration '{envelope.integration_id}' not registered",
            )

        known_types = {d.content_type for d in self._catalogs[envelope.integration_id]}
        if envelope.content_type not in known_types:
            return SignalReceipt(
                signal_id=UUID(int=0),
                trace_id=UUID(int=0),
                accepted=False,
                accepted_at=now,
                rejection_reason=(
                    f"content_type '{envelope.content_type}' not in catalog "
                    f"for '{envelope.integration_id}'"
                ),
            )

        signal_id = self._dispatch(envelope)
        return SignalReceipt(
            signal_id=signal_id,
            trace_id=UUID(int=0),
            accepted=True,
            accepted_at=now,
        )

    def _dispatch(self, envelope: SignalEnvelope) -> UUID:
        """Convert envelope and submit to pipeline.

        Returns signal_id. Override point for Phase 2+ wiring.
        Default implementation returns a generated UUID without
        pipeline submission — the pipeline wire is added when a
        concrete consumer exists.
        """
        from uuid import uuid4

        return uuid4()

    def registered_integrations(self) -> list[str]:
        return list(self._emitters.keys())

    def signal_catalog(self) -> dict[str, list[SignalDescriptor]]:
        return dict(self._catalogs)
