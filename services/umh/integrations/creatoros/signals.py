"""CreatorOS signal emitter — builds SignalEnvelopes from polled CreatorOS database rows."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from services.umh.protocols.signal import SignalUrgency
from services.umh.sockets.envelopes import SignalEnvelope
from services.umh.sockets.protocols import SignalDescriptor

from .correlation import CreatorOSWritebackTarget
from .manifest import INTEGRATION_ID, SIGNAL_DESCRIPTORS
from .tables import AnalyticsRow, AudienceMetricRow, ContentRow

logger = logging.getLogger(__name__)


class CreatorOSSignalEmitter:
    """Declares signal types and builds envelopes from polled CreatorOS rows.

    Satisfies SignalEmitter Protocol structurally.
    """

    @property
    def integration_id(self) -> str:
        return INTEGRATION_ID

    def describe_signals(self) -> list[SignalDescriptor]:
        return list(SIGNAL_DESCRIPTORS)

    def build_content_signal(
        self,
        row: ContentRow,
    ) -> tuple[SignalEnvelope, CreatorOSWritebackTarget]:
        """Build a SignalEnvelope from a content row."""
        correlation_id = uuid4()
        content = f"[content] {row.platform}/{row.content_type}: {row.title} ({row.status})"

        envelope = SignalEnvelope(
            integration_id=INTEGRATION_ID,
            content_type="creatoros_content_published",
            payload={
                "table_name": "content",
                "row_id": row.id,
                "creator_id": row.creator_id,
                "platform": row.platform,
                "content_type": row.content_type,
                "title": row.title,
                "status": row.status,
                "published_at": row.published_at.isoformat() if row.published_at else None,
                "created_at": row.created_at.isoformat(),
                "adapter_name": "creatoros",
                "operation": "noop",
            },
            raw_content=content,
            source_identifier=f"creatoros:content:{row.id}",
            correlation_id=correlation_id,
            urgency=SignalUrgency.NORMAL,
            metadata={"creator_id": row.creator_id, "table_name": "content"},
        )

        target = CreatorOSWritebackTarget(
            creator_id=row.creator_id,
            table_name="content",
            row_id=row.id,
        )

        return envelope, target

    def build_analytics_signal(
        self,
        row: AnalyticsRow,
    ) -> tuple[SignalEnvelope, CreatorOSWritebackTarget]:
        """Build a SignalEnvelope from an analytics row."""
        correlation_id = uuid4()
        content = (
            f"[analytics] content:{row.content_id} — "
            f"views:{row.views} likes:{row.likes} comments:{row.comments} shares:{row.shares}"
        )

        envelope = SignalEnvelope(
            integration_id=INTEGRATION_ID,
            content_type="creatoros_analytics_updated",
            payload={
                "table_name": "analytics",
                "row_id": row.id,
                "creator_id": row.creator_id,
                "content_id": row.content_id,
                "views": row.views,
                "likes": row.likes,
                "comments": row.comments,
                "shares": row.shares,
                "updated_at": row.updated_at.isoformat(),
                "adapter_name": "creatoros",
                "operation": "noop",
            },
            raw_content=content,
            source_identifier=f"creatoros:analytics:{row.id}",
            correlation_id=correlation_id,
            urgency=SignalUrgency.LOW,
            metadata={"creator_id": row.creator_id, "table_name": "analytics"},
        )

        target = CreatorOSWritebackTarget(
            creator_id=row.creator_id,
            table_name="analytics",
            row_id=row.id,
        )

        return envelope, target

    def build_audience_signal(
        self,
        row: AudienceMetricRow,
    ) -> tuple[SignalEnvelope, CreatorOSWritebackTarget]:
        """Build a SignalEnvelope from an audience metric row."""
        correlation_id = uuid4()
        content = f"[audience_metrics] {row.platform} {row.metric_type}: {row.value}"

        envelope = SignalEnvelope(
            integration_id=INTEGRATION_ID,
            content_type="creatoros_audience_milestone",
            payload={
                "table_name": "audience_metrics",
                "row_id": row.id,
                "creator_id": row.creator_id,
                "platform": row.platform,
                "metric_type": row.metric_type,
                "value": row.value,
                "recorded_at": row.recorded_at.isoformat(),
                "adapter_name": "creatoros",
                "operation": "noop",
            },
            raw_content=content,
            source_identifier=f"creatoros:audience_metrics:{row.id}",
            correlation_id=correlation_id,
            urgency=SignalUrgency.HIGH,
            metadata={"creator_id": row.creator_id, "table_name": "audience_metrics"},
        )

        target = CreatorOSWritebackTarget(
            creator_id=row.creator_id,
            table_name="audience_metrics",
            row_id=row.id,
        )

        return envelope, target
