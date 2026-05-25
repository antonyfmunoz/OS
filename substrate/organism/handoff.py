"""Agent handoff protocol — structured agent-to-agent task transfer.

When an agent determines a task belongs to a different agent's domain,
it creates a HandoffRequest with its partial work and reasoning.
The coordinator routes the handoff, and the receiving agent picks up
with full context of what the sender already did.

Three handoff types:
  ESCALATION  — sending up the hierarchy (e.g., agent → CEO)
  DELEGATION  — sending down (e.g., CEO → department agent)
  LATERAL     — peer transfer (e.g., researcher → builder)
"""

from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from substrate.organism.protocols import AgentMessage, AgentStatus, Deliverable

logger = logging.getLogger(__name__)


class HandoffType(str, Enum):
    ESCALATION = "escalation"
    DELEGATION = "delegation"
    LATERAL = "lateral"


class HandoffStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"


class HandoffRequest(BaseModel):
    """A structured request to transfer a task between agents."""

    id: UUID = Field(default_factory=uuid4)
    handoff_type: HandoffType
    source_agent: str
    target_agent: str
    task: str = Field(max_length=2000)
    context: str = Field(default="", max_length=5000)
    partial_work: str = Field(default="", max_length=5000)
    reason: str = Field(default="", max_length=500)
    priority: str = Field(default="normal")
    status: HandoffStatus = HandoffStatus.PENDING
    source_deliverable_id: UUID | None = None
    created_at: float = Field(default_factory=time.time)
    resolved_at: float | None = None


class HandoffResult(BaseModel):
    """The outcome of a handoff attempt."""

    handoff_id: UUID
    accepted: bool
    target_agent: str
    deliverable: Deliverable | None = None
    rejection_reason: str = ""


class HandoffRouter:
    """Routes handoff requests between agents in the organism.

    Uses AgentHierarchy to validate handoff direction and find
    the correct target when the caller specifies a role instead
    of a specific agent_id.
    """

    def __init__(self) -> None:
        self._pending: dict[UUID, HandoffRequest] = {}
        self._history: list[HandoffRequest] = []
        self._hierarchy: Any = None

    def _get_hierarchy(self) -> Any:
        if self._hierarchy is None:
            try:
                from substrate.control_plane.agents.agent_hierarchy import AgentHierarchy

                self._hierarchy = AgentHierarchy()
            except ImportError:
                pass
        return self._hierarchy

    def _resolve_target(self, source: str, handoff_type: HandoffType, target_hint: str) -> str:
        """Resolve a target agent from a hint, using hierarchy if available."""
        hierarchy = self._get_hierarchy()
        if not hierarchy:
            return target_hint

        if handoff_type == HandoffType.ESCALATION:
            agent_config = hierarchy.get_agent(source)
            reports_to = agent_config.get("reports_to")
            if reports_to:
                return reports_to

        return target_hint

    def submit(self, request: HandoffRequest) -> HandoffRequest:
        """Submit a handoff request for routing."""
        resolved = self._resolve_target(
            request.source_agent,
            request.handoff_type,
            request.target_agent,
        )
        request.target_agent = resolved
        self._pending[request.id] = request
        logger.info(
            "handoff submitted: %s → %s (%s) task='%s'",
            request.source_agent,
            request.target_agent,
            request.handoff_type.value,
            request.task[:80],
        )
        return request

    def to_agent_message(self, request: HandoffRequest) -> AgentMessage:
        """Convert a handoff request into an AgentMessage for the target agent."""
        return AgentMessage(
            sender=request.source_agent,
            recipient=request.target_agent,
            intent="delegate_task",
            payload={
                "task": request.task,
                "handoff_id": str(request.id),
                "handoff_type": request.handoff_type.value,
                "context": request.context,
                "partial_work": request.partial_work,
                "reason": request.reason,
                "priority": request.priority,
                "risk_class": "READ_ONLY",
            },
        )

    def resolve(
        self,
        handoff_id: UUID,
        accepted: bool,
        deliverable: Deliverable | None = None,
        rejection_reason: str = "",
    ) -> HandoffResult:
        """Resolve a pending handoff."""
        request = self._pending.pop(handoff_id, None)
        if not request:
            return HandoffResult(
                handoff_id=handoff_id,
                accepted=False,
                target_agent="unknown",
                rejection_reason="handoff not found",
            )

        request.status = HandoffStatus.COMPLETED if accepted else HandoffStatus.REJECTED
        request.resolved_at = time.time()
        self._history.append(request)

        logger.info(
            "handoff resolved: %s → %s = %s",
            request.source_agent,
            request.target_agent,
            "accepted" if accepted else f"rejected: {rejection_reason}",
        )

        return HandoffResult(
            handoff_id=handoff_id,
            accepted=accepted,
            target_agent=request.target_agent,
            deliverable=deliverable,
            rejection_reason=rejection_reason,
        )

    def check_timeouts(self, timeout_seconds: float = 300.0) -> list[HandoffRequest]:
        """Find and mark timed-out handoffs."""
        now = time.time()
        timed_out: list[HandoffRequest] = []
        expired_ids: list[UUID] = []

        for hid, req in self._pending.items():
            if now - req.created_at > timeout_seconds:
                req.status = HandoffStatus.TIMED_OUT
                req.resolved_at = now
                timed_out.append(req)
                expired_ids.append(hid)

        for hid in expired_ids:
            req = self._pending.pop(hid)
            self._history.append(req)
            logger.warning(
                "handoff timed out: %s → %s (%.0fs)",
                req.source_agent,
                req.target_agent,
                now - req.created_at,
            )

        return timed_out

    def pending_for(self, agent_id: str) -> list[HandoffRequest]:
        """Get pending handoffs targeted at a specific agent."""
        return [r for r in self._pending.values() if r.target_agent == agent_id]

    def stats(self) -> dict[str, Any]:
        type_counts: dict[str, int] = {}
        for req in self._history:
            key = req.handoff_type.value
            type_counts[key] = type_counts.get(key, 0) + 1

        completed = sum(1 for r in self._history if r.status == HandoffStatus.COMPLETED)
        rejected = sum(1 for r in self._history if r.status == HandoffStatus.REJECTED)
        timed_out = sum(1 for r in self._history if r.status == HandoffStatus.TIMED_OUT)

        return {
            "pending": len(self._pending),
            "total_processed": len(self._history),
            "completed": completed,
            "rejected": rejected,
            "timed_out": timed_out,
            "by_type": type_counts,
        }
