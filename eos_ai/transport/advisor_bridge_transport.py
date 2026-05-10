"""
Advisor bridge transport for Phase 94D.5.

Transport-aware helpers that bind the abstract advisor relay contracts
to the founder's current topology: VPS orchestrator ↔ local PC worker
via Tailscale + HTTP bridge + SSH + file-based inbox/outbox.

These are pure or low-side-effect helpers. They build paths, serialize
message files, and construct commands — they do not perform network I/O
themselves unless explicitly called via the execute helpers.

No computer use. No Google Drive. No browser automation.
"""

from __future__ import annotations

import os
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eos_ai.transport.message_bus_contracts import (

    MessageEnvelope,
    MessagePriority,
    MessageType,
)

_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"



def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


LOCAL_INBOX_DIR = Path.home() / "eos_inbox"
LOCAL_OUTBOX_DIR = Path.home() / "eos_outbox"
ADVISOR_MESSAGES_DIR = Path.home() / "eos_advisor_messages"

VPS_STATION_DIR = Path(_ROOT) / "eos_ai" / ".substrate_station"
VPS_ADVISOR_INBOX = VPS_STATION_DIR / "advisor_inbox"

BRIDGE_IP = os.getenv("EOS_LOCAL_BRIDGE_IP", "100.74.199.102")
BRIDGE_PORT = 8766
BRIDGE_HEALTH_URL = f"http://{BRIDGE_IP}:{BRIDGE_PORT}/health"
BRIDGE_MESSAGE_URL = f"http://{BRIDGE_IP}:{BRIDGE_PORT}/message"
BRIDGE_STATUS_URL = f"http://{BRIDGE_IP}:{BRIDGE_PORT}/status"

VPS_WEBHOOK_IP = os.getenv("EOS_VPS_TAILSCALE_IP", "100.77.233.50")
VPS_WEBHOOK_PORT = 8765
VPS_CC_REPLY_URL = f"http://{VPS_WEBHOOK_IP}:{VPS_WEBHOOK_PORT}/cc-reply"

SSH_USER = r"DESKTOP-LVGUIQ9\antonys beast pc"
SSH_HOST = os.getenv("EOS_LOCAL_BRIDGE_IP", "100.74.199.102")
SSH_KEY = "/root/.ssh/id_ed25519"


def build_local_inbox_path(session_name: str = "umh_core") -> str:
    return str(LOCAL_INBOX_DIR / f"{session_name}.txt")


def build_local_outbox_path(work_order_id: str = "") -> str:
    filename = f"advisor_request_{work_order_id}.json" if work_order_id else "advisor_request.json"
    return str(LOCAL_OUTBOX_DIR / filename)


def build_advisor_message_dir() -> str:
    return str(ADVISOR_MESSAGES_DIR)


@dataclass
class AdvisorMessageFile:
    message_id: str = field(default_factory=_new_id)
    message_type: str = ""
    work_order_id: str = ""
    sender: str = ""
    recipient: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    priority: str = "HIGH"
    timestamp: str = field(default_factory=_now_iso)
    correlation_id: str | None = None
    requires_response: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "message_type": self.message_type,
            "work_order_id": self.work_order_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "payload": self.payload,
            "priority": self.priority,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "requires_response": self.requires_response,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdvisorMessageFile:
        return cls(
            message_id=data.get("message_id", _new_id()),
            message_type=data.get("message_type", ""),
            work_order_id=data.get("work_order_id", ""),
            sender=data.get("sender", ""),
            recipient=data.get("recipient", ""),
            payload=data.get("payload", {}),
            priority=data.get("priority", "HIGH"),
            timestamp=data.get("timestamp", _now_iso()),
            correlation_id=data.get("correlation_id"),
            requires_response=data.get("requires_response", False),
        )

    @classmethod
    def from_json(cls, text: str) -> AdvisorMessageFile:
        return cls.from_dict(json.loads(text))

    @classmethod
    def from_envelope(cls, envelope: MessageEnvelope) -> AdvisorMessageFile:
        return cls(
            message_id=envelope.message_id,
            message_type=envelope.message_type.value,
            work_order_id=envelope.work_order_id or "",
            sender=envelope.sender,
            recipient=envelope.recipient,
            payload=envelope.payload,
            priority=envelope.priority.value
            if isinstance(envelope.priority, MessagePriority)
            else str(envelope.priority),
            timestamp=envelope.timestamp,
            correlation_id=envelope.correlation_id,
            requires_response=envelope.requires_response,
        )


def create_worker_approval_request_file(
    work_order_id: str,
    action: str,
    target: str,
    description: str,
    risk_level: str = "MEDIUM",
    worker_id: str = "local_pc_worker",
    backend: str = "GUI_COMPUTER_USE",
) -> AdvisorMessageFile:
    return AdvisorMessageFile(
        message_type="APPROVAL_NEEDED",
        work_order_id=work_order_id,
        sender=f"node:{worker_id}",
        recipient="advisor",
        payload={
            "approval_request_id": f"apr_{_new_id()}",
            "work_order_id": work_order_id,
            "node_id": worker_id,
            "action": action,
            "target": target,
            "description": description,
            "risk_level": risk_level,
            "backend": backend,
            "blocked_until_approved": True,
        },
        priority="HIGH",
        requires_response=True,
    )


def create_advisor_response_file(
    approval_request_id: str,
    decision: str,
    work_order_id: str,
    reason: str | None = None,
    correlation_id: str | None = None,
) -> AdvisorMessageFile:
    return AdvisorMessageFile(
        message_type="APPROVAL_RESPONSE",
        work_order_id=work_order_id,
        sender="founder",
        recipient="advisor",
        payload={
            "approval_request_id": approval_request_id,
            "decision": decision,
            "reason": reason,
        },
        correlation_id=correlation_id,
    )


def build_forward_to_local_payload(
    message_file: AdvisorMessageFile,
    session_name: str = "umh_core",
) -> dict[str, Any]:
    return {
        "text": message_file.to_json(),
        "session_name": session_name,
        "work_order_id": message_file.work_order_id,
        "message_type": message_file.message_type,
        "transport": "http_bridge",
    }


def build_poll_local_outbox_command(
    work_order_id: str = "",
    outbox_dir: str = "~/eos_outbox",
) -> str:
    pattern = f"{work_order_id}*.json" if work_order_id else "*.json"
    return (
        f"ssh -i {SSH_KEY} -o IdentitiesOnly=yes -o BatchMode=yes "
        f"-o ConnectTimeout=8 "
        f"'{SSH_USER}'@{SSH_HOST} "
        f"'wsl -e bash -c \"ls {outbox_dir}/{pattern} 2>/dev/null\"'"
    )


def build_read_local_outbox_file_command(filepath: str) -> str:
    return (
        f"ssh -i {SSH_KEY} -o IdentitiesOnly=yes -o BatchMode=yes "
        f"-o ConnectTimeout=8 "
        f"'{SSH_USER}'@{SSH_HOST} "
        f"'wsl -e bash -c \"cat {filepath}\"'"
    )


def build_write_local_inbox_command(
    content: str,
    inbox_path: str,
) -> str:
    escaped = content.replace("'", "'\\''")
    return (
        f"ssh -i {SSH_KEY} -o IdentitiesOnly=yes -o BatchMode=yes "
        f"-o ConnectTimeout=8 "
        f"'{SSH_USER}'@{SSH_HOST} "
        f"'wsl -e bash -c \"mkdir -p $(dirname {inbox_path}) && "
        f"echo '\\'{escaped}'\\' > {inbox_path}\"'"
    )


def build_ssh_health_command() -> str:
    return (
        f"ssh -i {SSH_KEY} -o IdentitiesOnly=yes -o BatchMode=yes "
        f"-o ConnectTimeout=8 "
        f"'{SSH_USER}'@{SSH_HOST} 'echo SSH_OK'"
    )


def build_bridge_health_command() -> str:
    return f"curl -s --connect-timeout 5 {BRIDGE_HEALTH_URL}"


def build_bridge_status_command() -> str:
    return f"curl -s --connect-timeout 5 {BRIDGE_STATUS_URL}"


def build_mkdir_local_dirs_command() -> str:
    return (
        f"ssh -i {SSH_KEY} -o IdentitiesOnly=yes -o BatchMode=yes "
        f"-o ConnectTimeout=8 "
        f"'{SSH_USER}'@{SSH_HOST} "
        f"'wsl -e bash -c \"mkdir -p ~/eos_inbox ~/eos_outbox ~/eos_advisor_messages\"'"
    )
