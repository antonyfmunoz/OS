"""CreatorOS signal emitter — builds SignalEnvelopes from polled CreatorOS database rows."""

from __future__ import annotations

import logging
from uuid import uuid4

from services.umh.protocols.signal import SignalUrgency
from services.umh.sockets.envelopes import SignalEnvelope
from services.umh.sockets.protocols import SignalDescriptor

from .correlation import CreatorOSWritebackTarget
from .manifest import INTEGRATION_ID, SIGNAL_DESCRIPTORS
from .tables import PostRow, ProductRow, RevenueRow

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

    def build_post_signal(
        self,
        row: PostRow,
    ) -> tuple[SignalEnvelope, CreatorOSWritebackTarget]:
        """Build a SignalEnvelope from a post row."""
        correlation_id = uuid4()
        content = (
            f"[post] {row.media_type}: "
            f"{row.content[:80] if row.content else '(empty)'} "
            f"(likes:{row.likes} comments:{row.comments})"
        )

        envelope = SignalEnvelope(
            integration_id=INTEGRATION_ID,
            content_type="creatoros_post_created",
            payload={
                "table_name": "posts",
                "row_id": str(row.id),
                "user_id": str(row.user_id),
                "content": row.content,
                "media_type": row.media_type,
                "likes": row.likes,
                "comments": row.comments,
                "created_at": row.created_at.isoformat(),
                "adapter_name": "creatoros",
                "operation": "noop",
            },
            raw_content=content,
            source_identifier=f"creatoros:posts:{row.id}",
            correlation_id=correlation_id,
            urgency=SignalUrgency.NORMAL,
            metadata={"user_id": str(row.user_id), "table_name": "posts"},
        )

        target = CreatorOSWritebackTarget(
            user_id=row.user_id,
            table_name="posts",
            row_id=str(row.id),
        )

        return envelope, target

    def build_product_signal(
        self,
        row: ProductRow,
    ) -> tuple[SignalEnvelope, CreatorOSWritebackTarget]:
        """Build a SignalEnvelope from a product row."""
        correlation_id = uuid4()
        content = f"[product] {row.title} — ${row.price:.2f} ({row.category}) rating:{row.rating}"

        envelope = SignalEnvelope(
            integration_id=INTEGRATION_ID,
            content_type="creatoros_product_listed",
            payload={
                "table_name": "products",
                "row_id": str(row.id),
                "user_id": str(row.user_id),
                "title": row.title,
                "description": row.description,
                "price": row.price,
                "category": row.category,
                "rating": row.rating,
                "review_count": row.review_count,
                "created_at": row.created_at.isoformat(),
                "adapter_name": "creatoros",
                "operation": "noop",
            },
            raw_content=content,
            source_identifier=f"creatoros:products:{row.id}",
            correlation_id=correlation_id,
            urgency=SignalUrgency.NORMAL,
            metadata={"user_id": str(row.user_id), "table_name": "products"},
        )

        target = CreatorOSWritebackTarget(
            user_id=row.user_id,
            table_name="products",
            row_id=str(row.id),
        )

        return envelope, target

    def build_revenue_signal(
        self,
        row: RevenueRow,
    ) -> tuple[SignalEnvelope, CreatorOSWritebackTarget]:
        """Build a SignalEnvelope from a revenue row."""
        correlation_id = uuid4()
        content = f"[revenue] ${row.amount:.2f} from {row.source or 'unknown'}"

        envelope = SignalEnvelope(
            integration_id=INTEGRATION_ID,
            content_type="creatoros_revenue_recorded",
            payload={
                "table_name": "revenue",
                "row_id": str(row.id),
                "user_id": str(row.user_id),
                "amount": row.amount,
                "source": row.source,
                "date": row.date.isoformat(),
                "adapter_name": "creatoros",
                "operation": "noop",
            },
            raw_content=content,
            source_identifier=f"creatoros:revenue:{row.id}",
            correlation_id=correlation_id,
            urgency=SignalUrgency.HIGH,
            metadata={"user_id": str(row.user_id), "table_name": "revenue"},
        )

        target = CreatorOSWritebackTarget(
            user_id=row.user_id,
            table_name="revenue",
            row_id=str(row.id),
        )

        return envelope, target
