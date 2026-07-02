"""Slack workflow — governed messaging with outbox-based delivery.

No Slack adapter exists yet. Messages are queued to an outbox JSONL file
for later delivery. When a Slack adapter is built, the send step will
try the adapter first and fall back to the outbox.

Step-sets:
- send_message: validate_message → send_message → confirm_delivery
- notify: format_notification → send_notification
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from projections.eos.workflows.types import WorkflowStep

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_OUTBOX_DIR = os.path.join(_REPO_ROOT, "data", "umh", "slack")
_OUTBOX_FILE = os.path.join(_OUTBOX_DIR, "outbox.jsonl")

_NOTIFICATION_TEMPLATES: dict[str, str] = {
    "workflow_complete": "Workflow **{name}** completed: {status}",
    "task_assigned": "Task assigned: **{description}**",
    "approval_needed": "Approval needed: **{description}**",
    "error": "Error in **{source}**: {message}",
    "alert": "Alert: **{message}**",
}


class SlackWorkflow:
    """Slack messaging workflow through governed mutation."""

    def __init__(self, org_id: str = "", venture_id: str = "") -> None:
        self._org_id = org_id
        self._venture_id = venture_id
        self._validated_message: str = ""
        self._validated_channel: str = ""
        self._delivery_id: str = ""

    def send_message_steps(
        self, channel: str, message: str
    ) -> list[WorkflowStep]:
        """Steps for sending a Slack message."""
        return [
            WorkflowStep(
                name="validate_message",
                mutation_name="command_submit",
                intent=f"Validate Slack message for #{channel}",
                execute_fn=lambda: self._validate_message(channel, message),
            ),
            WorkflowStep(
                name="send_message",
                mutation_name="channel_message_send",
                intent=f"Send message to #{channel}",
                execute_fn=self._send_message,
            ),
            WorkflowStep(
                name="confirm_delivery",
                mutation_name="command_submit",
                intent=f"Confirm delivery to #{channel}",
                execute_fn=self._confirm_delivery,
                skip_on_failure=True,
            ),
        ]

    def notify_steps(
        self,
        channel: str,
        event_type: str,
        details: dict[str, Any] | None = None,
    ) -> list[WorkflowStep]:
        """Steps for sending a system notification."""
        return [
            WorkflowStep(
                name="format_notification",
                mutation_name="command_submit",
                intent=f"Format {event_type} notification for #{channel}",
                execute_fn=lambda: self._format_notification(
                    channel, event_type, details or {}
                ),
            ),
            WorkflowStep(
                name="send_notification",
                mutation_name="channel_message_send",
                intent=f"Send {event_type} notification to #{channel}",
                execute_fn=self._send_message,
            ),
        ]

    def _validate_message(
        self, channel: str, message: str
    ) -> tuple[str, bool]:
        if not channel or not channel.strip():
            return ("channel is required", False)
        if not message or not message.strip():
            return ("message is required", False)
        if len(message) > 4000:
            return ("message exceeds 4000 character limit", False)

        self._validated_channel = channel.strip().lstrip("#")
        self._validated_message = message.strip()
        return (
            f"Validated: {len(self._validated_message)} chars for "
            f"#{self._validated_channel}",
            True,
        )

    def _format_notification(
        self,
        channel: str,
        event_type: str,
        details: dict[str, Any],
    ) -> tuple[str, bool]:
        self._validated_channel = channel.strip().lstrip("#")

        template = _NOTIFICATION_TEMPLATES.get(event_type)
        if template:
            try:
                self._validated_message = template.format(**details)
            except KeyError as exc:
                self._validated_message = (
                    f"[{event_type}] {json.dumps(details, default=str)}"
                )
                logger.debug("template key missing: %s", exc)
        else:
            self._validated_message = (
                f"[{event_type}] {json.dumps(details, default=str)}"
            )

        return (
            f"Formatted {event_type} notification: "
            f"{self._validated_message[:100]}",
            True,
        )

    def _send_message(self) -> tuple[str, bool]:
        if not self._validated_message or not self._validated_channel:
            return ("no validated message to send", False)

        now = datetime.now(timezone.utc)
        entry = {
            "ts": now.isoformat(),
            "channel": self._validated_channel,
            "message": self._validated_message,
            "org_id": self._org_id,
            "status": "queued",
        }

        # Future: try real Slack adapter first
        # try:
        #     from adapters.slack.connector import send_message
        #     result = send_message(self._validated_channel, self._validated_message)
        #     if result:
        #         entry["status"] = "delivered"
        #         ...
        # except ImportError:
        #     pass  # fall through to outbox

        os.makedirs(_OUTBOX_DIR, exist_ok=True)
        try:
            with open(_OUTBOX_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError as exc:
            logger.debug("outbox write failed: %s", exc)
            return (f"failed to queue message: {exc}", False)

        self._delivery_id = f"slack-{now.strftime('%Y%m%d-%H%M%S')}"
        return (
            f"Queued to outbox: #{self._validated_channel} "
            f"({len(self._validated_message)} chars) [{self._delivery_id}]",
            True,
        )

    def _confirm_delivery(self) -> tuple[str, bool]:
        if not self._delivery_id:
            return ("no delivery to confirm", False)
        return (
            f"Delivery confirmed (outbox): {self._delivery_id}",
            True,
        )
