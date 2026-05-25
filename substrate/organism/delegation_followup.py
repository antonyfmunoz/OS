"""Automated delegation follow-up — checks overdue delegations and acts.

Wires the existing DelegationTracker into an automated loop that:
  1. Checks for overdue delegations
  2. Generates context-aware follow-up messages
  3. Escalates to the appropriate agent if still unresolved
  4. Uses LLM for nuanced follow-up when heuristic is insufficient
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

FOLLOWUP_CHECK_INTERVAL_S = 3600
MAX_FOLLOWUPS_PER_DELEGATION = 3


@dataclass
class FollowupAction:
    """A follow-up action generated from an overdue delegation."""

    delegation_id: str
    task: str
    delegated_to: str
    hours_overdue: float
    followup_number: int
    message: str
    escalated: bool = False
    escalation_target: str = ""


@dataclass
class FollowupReport:
    """Summary of a follow-up check cycle."""

    checked_at: float = 0.0
    overdue_count: int = 0
    followups_sent: int = 0
    escalations: int = 0
    actions: list[FollowupAction] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class DelegationFollowup:
    """Automated follow-up for overdue delegations."""

    def __init__(self) -> None:
        self._followup_counts: dict[str, int] = {}
        self._last_check: float = 0.0
        self._reports: list[FollowupReport] = []

    def check_and_followup(self) -> FollowupReport:
        """Check for overdue delegations and generate follow-up actions."""
        report = FollowupReport(checked_at=time.time())

        try:
            from substrate.control_plane.delegation.delegation_tracker import (
                get_overdue_delegations,
            )

            overdue = get_overdue_delegations()
        except Exception as e:
            report.errors.append(f"Failed to get overdue delegations: {e}")
            self._reports.append(report)
            return report

        report.overdue_count = len(overdue)

        for delegation in overdue:
            event_id = delegation.get("event_id", "")
            task = delegation.get("task", "")
            delegated_to = delegation.get("delegated_to", "")
            due_at = delegation.get("due_at", "")

            followup_num = self._followup_counts.get(event_id, 0) + 1
            self._followup_counts[event_id] = followup_num

            if followup_num > MAX_FOLLOWUPS_PER_DELEGATION:
                continue

            hours_overdue = self._calc_hours_overdue(due_at)

            should_escalate = followup_num >= 3 or hours_overdue > 48

            message = self._generate_followup(task, delegated_to, followup_num, hours_overdue)

            action = FollowupAction(
                delegation_id=event_id,
                task=task[:200],
                delegated_to=delegated_to,
                hours_overdue=round(hours_overdue, 1),
                followup_number=followup_num,
                message=message,
                escalated=should_escalate,
            )

            if should_escalate:
                action.escalation_target = self._get_escalation_target(delegated_to)
                report.escalations += 1

            report.actions.append(action)
            report.followups_sent += 1
            self._send_followup(action)

        self._last_check = time.time()
        self._reports.append(report)
        if len(self._reports) > 100:
            self._reports = self._reports[-100:]

        return report

    def _calc_hours_overdue(self, due_at: str) -> float:
        """Calculate hours since the due time."""
        try:
            from datetime import datetime, timezone

            if due_at.endswith("Z"):
                due_at = due_at[:-1] + "+00:00"
            due_dt = datetime.fromisoformat(due_at)
            if due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - due_dt
            return max(0, delta.total_seconds() / 3600)
        except (ValueError, TypeError):
            return 0.0

    def _generate_followup(
        self,
        task: str,
        delegated_to: str,
        followup_num: int,
        hours_overdue: float,
    ) -> str:
        """Generate a follow-up message. Heuristic first, LLM if nuanced."""
        if followup_num == 1:
            base = f"Checking in: '{task[:100]}' assigned to {delegated_to} is {hours_overdue:.0f}h overdue."
        elif followup_num == 2:
            base = (
                f"Second follow-up: '{task[:100]}' is now {hours_overdue:.0f}h overdue. "
                f"Please provide a status update or flag blockers."
            )
        else:
            base = (
                f"Escalation: '{task[:100]}' has been overdue for {hours_overdue:.0f}h "
                f"with {followup_num} follow-ups. Escalating for resolution."
            )

        if followup_num >= 2 and hours_overdue > 24:
            ai_msg = self._ai_followup(task, delegated_to, followup_num, hours_overdue)
            if ai_msg:
                return ai_msg

        return base

    def _ai_followup(
        self,
        task: str,
        delegated_to: str,
        followup_num: int,
        hours_overdue: float,
    ) -> str | None:
        """Use LLM for nuanced follow-up messages."""
        try:
            from adapters.models.model_router import call_with_fallback

            result = call_with_fallback(
                prompt=(
                    f"Task: {task[:300]}\n"
                    f"Assigned to: {delegated_to}\n"
                    f"Hours overdue: {hours_overdue:.0f}\n"
                    f"Follow-up number: {followup_num}\n\n"
                    f"Write a concise follow-up message (2-3 sentences max)."
                ),
                system=(
                    "You write professional delegation follow-up messages. "
                    "Be direct but not aggressive. Focus on unblocking, not blame. "
                    "If this is follow-up #3+, suggest escalation options. "
                    "Return ONLY the message text, no JSON."
                ),
                task_type="fast_response",
            )
            if result.output and len(result.output.strip()) > 10:
                return result.output.strip()[:500]
        except Exception as e:
            logger.debug("AI follow-up generation failed: %s", e)
        return None

    def _get_escalation_target(self, delegated_to: str) -> str:
        """Determine who to escalate to based on the delegatee."""
        try:
            from substrate.control_plane.agents.agent_hierarchy import AgentHierarchy

            hierarchy = AgentHierarchy()
            agent_config = hierarchy.get_agent(delegated_to)
            reports_to = agent_config.get("reports_to", "")
            if reports_to:
                return reports_to
        except Exception:
            pass
        return "executive_assistant"

    def _send_followup(self, action: FollowupAction) -> None:
        """Dispatch a follow-up notification."""
        try:
            from substrate.sockets.channel_port import get_channel_router

            router = get_channel_router()
            if router:
                prefix = "[ESCALATION] " if action.escalated else "[FOLLOW-UP] "
                router.notify(f"{prefix}{action.message}")
        except Exception as e:
            logger.debug("Follow-up notification failed: %s", e)

    def stats(self) -> dict[str, Any]:
        total_followups = sum(r.followups_sent for r in self._reports)
        total_escalations = sum(r.escalations for r in self._reports)
        return {
            "checks_run": len(self._reports),
            "total_followups_sent": total_followups,
            "total_escalations": total_escalations,
            "active_tracking": len(self._followup_counts),
            "last_check": self._last_check,
        }
