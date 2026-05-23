"""EOS signal emitter — builds SignalEnvelopes from polled EOS database rows."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from substrate.types import SignalUrgency
from substrate.sockets.envelopes import SignalEnvelope
from substrate.sockets.protocols import SignalDescriptor

from .correlation import EOSWritebackTarget
from .manifest import INTEGRATION_ID, SIGNAL_DESCRIPTORS
from .tables import CrmActivityRow, CrmContactRow, CrmDealRow

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

    def build_contact_signal(
        self,
        row: CrmContactRow,
    ) -> tuple[SignalEnvelope, EOSWritebackTarget]:
        """Build a SignalEnvelope from a CRM contact row."""
        correlation_id = uuid4()
        content = f"[crm_contacts] {row.name} ({row.email}): {row.status}"
        if row.company:
            content += f" @ {row.company}"

        envelope = SignalEnvelope(
            integration_id=INTEGRATION_ID,
            content_type="eos_contact_created",
            payload={
                "table_name": "crm_contacts",
                "row_id": row.id,
                "user_id": row.user_id,
                "name": row.name,
                "email": row.email,
                "status": row.status,
                "company": row.company,
                "title": row.title,
                "created_at": row.created_at.isoformat(),
                "adapter_name": "eos",
                "operation": "noop",
            },
            raw_content=content,
            source_identifier=f"eos:crm_contacts:{row.id}",
            correlation_id=correlation_id,
            urgency=SignalUrgency.NORMAL,
            metadata={"user_id": row.user_id, "table_name": "crm_contacts"},
        )

        target = EOSWritebackTarget(
            user_id=row.user_id,
            table_name="crm_contacts",
            row_id=row.id,
        )

        return envelope, target

    def build_deal_signal(
        self,
        row: CrmDealRow,
    ) -> tuple[SignalEnvelope, EOSWritebackTarget]:
        """Build a SignalEnvelope from a CRM deal row."""
        correlation_id = uuid4()
        content = (
            f"[crm_deals] {row.title} @ {row.company}: "
            f"${row.value} ({row.stage}, {row.probability}%)"
        )

        envelope = SignalEnvelope(
            integration_id=INTEGRATION_ID,
            content_type="eos_deal_created",
            payload={
                "table_name": "crm_deals",
                "row_id": row.id,
                "user_id": row.user_id,
                "title": row.title,
                "company": row.company,
                "value": row.value,
                "stage": row.stage,
                "probability": row.probability,
                "contact_id": row.contact_id,
                "created_at": row.created_at.isoformat(),
                "adapter_name": "eos",
                "operation": "noop",
            },
            raw_content=content,
            source_identifier=f"eos:crm_deals:{row.id}",
            correlation_id=correlation_id,
            urgency=SignalUrgency.HIGH,
            metadata={"user_id": row.user_id, "table_name": "crm_deals"},
        )

        target = EOSWritebackTarget(
            user_id=row.user_id,
            table_name="crm_deals",
            row_id=row.id,
        )

        return envelope, target

    def build_activity_signal(
        self,
        row: CrmActivityRow,
    ) -> tuple[SignalEnvelope, EOSWritebackTarget]:
        """Build a SignalEnvelope from a CRM activity row."""
        correlation_id = uuid4()
        status_str = "done" if row.completed else "pending"
        content = (
            f"[crm_activities] {row.type}: {row.subject} "
            f"({status_str}, {row.related_to_type}:{row.related_to_id[:8]})"
        )

        envelope = SignalEnvelope(
            integration_id=INTEGRATION_ID,
            content_type="eos_activity_logged",
            payload={
                "table_name": "crm_activities",
                "row_id": row.id,
                "user_id": row.user_id,
                "type": row.type,
                "subject": row.subject,
                "date": row.date.isoformat(),
                "related_to_type": row.related_to_type,
                "related_to_id": row.related_to_id,
                "completed": row.completed,
                "created_at": row.created_at.isoformat(),
                "adapter_name": "eos",
                "operation": "noop",
            },
            raw_content=content,
            source_identifier=f"eos:crm_activities:{row.id}",
            correlation_id=correlation_id,
            urgency=SignalUrgency.LOW,
            metadata={"user_id": row.user_id, "table_name": "crm_activities"},
        )

        target = EOSWritebackTarget(
            user_id=row.user_id,
            table_name="crm_activities",
            row_id=row.id,
        )

        return envelope, target
