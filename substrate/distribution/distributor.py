"""Distribution Layer — bridges channels to the execution pipeline.

Inbound: channels produce signals → pipeline processes them.
Outbound: pipeline produces outcomes → channels deliver them.
Governance: approval requests go out → approvals come back.

The distributor wraps ChannelRouter and Pipeline into a single
coordination point. Every signal that enters and every outcome
that leaves goes through here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Protocol, runtime_checkable
from uuid import uuid4

logger = logging.getLogger(__name__)


@runtime_checkable
class ChannelRouterProtocol(Protocol):
    def notify(self, message: str) -> None: ...
    def request_approval(self, *, title: str, body: str, request_id: str) -> None: ...
    def get_status(self) -> dict[str, bool]: ...


class _NullRouter:
    """No-op router when no channel router is provided."""
    def notify(self, message: str) -> None: pass
    def request_approval(self, *, title: str, body: str, request_id: str) -> None: pass
    def get_status(self) -> dict[str, bool]: return {}


@dataclass
class DistributionEvent:
    event_id: str = ""
    direction: str = "inbound"
    channel: str = ""
    content_preview: str = ""
    outcome: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = str(uuid4())[:8]
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class DistributionStats:
    inbound_count: int = 0
    outbound_count: int = 0
    approval_requests: int = 0
    approvals_received: int = 0
    denials_received: int = 0
    delivery_failures: int = 0


class DistributionLayer:
    """Coordinates signal intake and outcome delivery across channels."""

    def __init__(
        self,
        channel_router: ChannelRouterProtocol | None = None,
        pipeline_submit_fn: Callable[..., Any] | None = None,
    ) -> None:
        self._router: ChannelRouterProtocol = channel_router or _NullRouter()
        self._submit = pipeline_submit_fn
        self._stats = DistributionStats()
        self._event_log: list[DistributionEvent] = []
        self._pending_approvals: dict[str, dict[str, Any]] = {}

    def set_pipeline(self, submit_fn: Callable[..., Any]) -> None:
        self._submit = submit_fn

    def ingest(
        self,
        content: str,
        source_channel: str = "api",
        metadata: dict[str, Any] | None = None,
        **pipeline_kwargs: Any,
    ) -> dict[str, Any]:
        """Accept a signal from any channel and route to pipeline."""
        self._stats.inbound_count += 1
        self._event_log.append(DistributionEvent(
            direction="inbound",
            channel=source_channel,
            content_preview=content[:100],
        ))

        if self._submit is None:
            return {"error": "pipeline not configured", "queued": True}

        result = self._submit(
            content,
            metadata={**(metadata or {}), "source_channel": source_channel},
            **pipeline_kwargs,
        )

        outcome_type = getattr(result, "outcome_type", None) or "unknown"
        success = getattr(result, "success", None)

        if success and outcome_type not in ("governance_denied", "mastery_blocked", "council_rejected"):
            self._deliver_outcome(
                source_channel,
                outcome_type,
                content[:200],
                result,
            )

        return {
            "trace_id": str(getattr(result, "trace_id", "")),
            "signal_id": str(getattr(result, "signal_id", "")),
            "outcome_type": outcome_type,
            "success": success,
            "distributed": True,
        }

    def _deliver_outcome(
        self,
        channel: str,
        outcome_type: str,
        content_preview: str,
        result: Any,
    ) -> None:
        """Deliver outcome notification through channels."""
        self._stats.outbound_count += 1
        self._event_log.append(DistributionEvent(
            direction="outbound",
            channel=channel,
            content_preview=content_preview,
            outcome=outcome_type,
        ))

        message = f"[{outcome_type}] {content_preview}"
        try:
            self._router.notify(message)
        except Exception as e:
            self._stats.delivery_failures += 1
            logger.warning("outcome delivery failed: %s", e)

    def request_approval(
        self,
        title: str,
        body: str,
        request_id: str | None = None,
        callback: Callable[[bool], None] | None = None,
    ) -> str:
        """Send an approval request through channels."""
        approval_id = request_id or str(uuid4())[:12]
        self._stats.approval_requests += 1
        self._pending_approvals[approval_id] = {
            "title": title,
            "body": body,
            "callback": callback,
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }

        self._router.request_approval(
            title=title,
            body=body,
            request_id=approval_id,
        )

        return approval_id

    def receive_approval(self, approval_id: str, approved: bool) -> bool:
        """Process an approval/denial response."""
        pending = self._pending_approvals.pop(approval_id, None)
        if not pending:
            return False

        if approved:
            self._stats.approvals_received += 1
        else:
            self._stats.denials_received += 1

        callback = pending.get("callback")
        if callback:
            try:
                callback(approved)
            except Exception as e:
                logger.warning("approval callback failed: %s", e)

        return True

    def channel_status(self) -> dict[str, bool]:
        """Get status of all configured channels."""
        return self._router.get_status()

    def stats(self) -> dict[str, Any]:
        return {
            "inbound_count": self._stats.inbound_count,
            "outbound_count": self._stats.outbound_count,
            "approval_requests": self._stats.approval_requests,
            "approvals_received": self._stats.approvals_received,
            "denials_received": self._stats.denials_received,
            "delivery_failures": self._stats.delivery_failures,
            "pending_approvals": len(self._pending_approvals),
            "channels": self.channel_status(),
        }

    def recent_events(self, limit: int = 20) -> list[dict[str, str]]:
        return [
            {
                "event_id": e.event_id,
                "direction": e.direction,
                "channel": e.channel,
                "content_preview": e.content_preview,
                "outcome": e.outcome,
                "timestamp": e.timestamp,
            }
            for e in self._event_log[-limit:]
        ]
