"""EOS signal emitter — builds SignalEnvelopes from polled EOS database rows."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from services.umh.protocols.signal import SignalUrgency
from services.umh.sockets.envelopes import SignalEnvelope
from services.umh.sockets.protocols import SignalDescriptor

from .correlation import EOSWritebackTarget
from .manifest import INTEGRATION_ID, SIGNAL_DESCRIPTORS
from .tables import EventRow

logger = logging.getLogger(__name__)


class EOSSignalEmitter:
    """Declares signal types and builds envelopes from polled EOS rows.

    Satisfies SignalEmitter Protocol structurally.
    """

    @property
    def integration_id(self) -> str:
        return INTEGRATION_ID

    def describe_signals(self) -> list[SignalDescriptor]:
        return list(SIGNAL_DESCRIPTORS)

    def build_signal(
        self,
        row: EventRow,
        table_name: str,
    ) -> tuple[SignalEnvelope, EOSWritebackTarget]:
        """Build a SignalEnvelope + writeback target from an EOS row.

        Returns (envelope, writeback_target) where writeback_target contains
        org_id + table + row_id for future Phase 4 outcome routing.
        """
        correlation_id = uuid4()

        content = f"[{table_name}] {row.event_type}: {_summarize_payload(row.payload_json)}"

        envelope = SignalEnvelope(
            integration_id=INTEGRATION_ID,
            content_type=f"eos_{table_name}_created",
            payload={
                "table_name": table_name,
                "row_id": row.id,
                "org_id": row.org_id,
                "event_type": row.event_type,
                "payload_json": row.payload_json,
                "handled_by": row.handled_by,
                "created_at": row.created_at.isoformat(),
                "adapter_name": "eos",
                "operation": "noop",
            },
            raw_content=content,
            source_identifier=f"eos:{table_name}:{row.id}",
            correlation_id=correlation_id,
            urgency=SignalUrgency.NORMAL,
            metadata={
                "org_id": row.org_id,
                "table_name": table_name,
            },
        )

        writeback_target = EOSWritebackTarget(
            org_id=row.org_id,
            table_name=table_name,
            row_id=row.id,
        )

        return envelope, writeback_target


def _summarize_payload(payload: dict[str, Any]) -> str:
    """Best-effort one-line summary from event payload."""
    for key in ("description", "summary", "title", "name", "message"):
        if key in payload and isinstance(payload[key], str):
            return payload[key][:120]
    return str(payload)[:120]
