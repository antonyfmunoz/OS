"""
Local worker relay packets for Phase 94D.5.

Generates the auto-mode worker instruction packet for W0-001 and
other work orders dispatched to the local PC worker.

The packet instructs the local worker how to behave:
- Run in AUTO mode
- Route approvals through advisor relay (not local terminal)
- Verify GUI backend before executing
- Respect governance gates
- Stop at first gate if relay unavailable

No computer use. No Google Drive. No browser automation.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from runtime.transport.computer_use_backend_contracts import ComputerUseBackend
from runtime.transport.governance_gate_contracts import (
    ALWAYS_BLOCKED_ACTIONS,
)
from runtime.transport.worker_node_contracts import WorkerMode


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


WO_001_ID = "WO-LOCAL-PILOT-GDRIVE-GDOCS-001"
WO_001_ACCOUNT = "antonyfm@empyreanstudios.co"
WO_001_SOURCE_CLASS = "Google Drive / Google Docs"


@dataclass
class WorkerRelayPacket:
    packet_id: str = field(default_factory=_new_id)
    work_order_id: str = ""
    worker_mode: str = WorkerMode.AUTO.value
    approval_routing: str = "advisor_relay"
    local_manual_approval_enabled: bool = False
    playwright_enabled: bool = False
    preferred_backend: str = ComputerUseBackend.GUI_COMPUTER_USE.value
    require_gui_healthcheck: bool = True
    stop_at_first_gate_if_relay_unavailable: bool = True
    target_account: str = ""
    source_class: str = ""
    blocked_actions: list[str] = field(default_factory=list)
    blocked_targets: list[str] = field(default_factory=list)
    first_approval_prompt: str = ""
    first_approval_action: str = ""
    first_approval_risk_level: str = "MEDIUM"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "work_order_id": self.work_order_id,
            "worker_mode": self.worker_mode,
            "approval_routing": self.approval_routing,
            "local_manual_approval_enabled": self.local_manual_approval_enabled,
            "playwright_enabled": self.playwright_enabled,
            "preferred_backend": self.preferred_backend,
            "require_gui_healthcheck": self.require_gui_healthcheck,
            "stop_at_first_gate_if_relay_unavailable": self.stop_at_first_gate_if_relay_unavailable,
            "target_account": self.target_account,
            "source_class": self.source_class,
            "blocked_actions": self.blocked_actions,
            "blocked_targets": self.blocked_targets,
            "first_approval_prompt": self.first_approval_prompt,
            "first_approval_action": self.first_approval_action,
            "first_approval_risk_level": self.first_approval_risk_level,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkerRelayPacket:
        return cls(
            packet_id=data.get("packet_id", _new_id()),
            work_order_id=data.get("work_order_id", ""),
            worker_mode=data.get("worker_mode", WorkerMode.AUTO.value),
            approval_routing=data.get("approval_routing", "advisor_relay"),
            local_manual_approval_enabled=data.get("local_manual_approval_enabled", False),
            playwright_enabled=data.get("playwright_enabled", False),
            preferred_backend=data.get(
                "preferred_backend", ComputerUseBackend.GUI_COMPUTER_USE.value
            ),
            require_gui_healthcheck=data.get("require_gui_healthcheck", True),
            stop_at_first_gate_if_relay_unavailable=data.get(
                "stop_at_first_gate_if_relay_unavailable", True
            ),
            target_account=data.get("target_account", ""),
            source_class=data.get("source_class", ""),
            blocked_actions=data.get("blocked_actions", []),
            blocked_targets=data.get("blocked_targets", []),
            first_approval_prompt=data.get("first_approval_prompt", ""),
            first_approval_action=data.get("first_approval_action", ""),
            first_approval_risk_level=data.get("first_approval_risk_level", "MEDIUM"),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", _now_iso()),
        )

    @classmethod
    def from_json(cls, text: str) -> WorkerRelayPacket:
        return cls.from_dict(json.loads(text))


def build_wo_001_relay_packet() -> WorkerRelayPacket:
    """Build the corrected W0-001 auto-mode relay packet."""
    return WorkerRelayPacket(
        work_order_id=WO_001_ID,
        worker_mode=WorkerMode.AUTO.value,
        approval_routing="advisor_relay",
        local_manual_approval_enabled=False,
        playwright_enabled=False,
        preferred_backend=ComputerUseBackend.GUI_COMPUTER_USE.value,
        require_gui_healthcheck=True,
        stop_at_first_gate_if_relay_unavailable=True,
        target_account=WO_001_ACCOUNT,
        source_class=WO_001_SOURCE_CLASS,
        blocked_actions=sorted(ALWAYS_BLOCKED_ACTIONS),
        blocked_targets=[
            "gmail",
            "account_switching",
            "google_calendar",
            "google_contacts",
            "google_photos",
            "youtube",
        ],
        first_approval_prompt=(
            f"Approve opening Google Drive for {WO_001_ACCOUNT} using visible GUI computer-use?"
        ),
        first_approval_action="OPEN_GOOGLE_DRIVE",
        first_approval_risk_level="MEDIUM",
        metadata={
            "phase": "94D.5",
            "test_version": "v1",
            "backend_required": "GUI_COMPUTER_USE",
            "playwright_status": "disabled_by_default",
        },
    )


def validate_relay_packet(packet: WorkerRelayPacket) -> list[str]:
    """Validate a relay packet for safety and completeness."""
    errors: list[str] = []

    if packet.worker_mode != WorkerMode.AUTO.value:
        errors.append(f"Worker mode must be AUTO, got {packet.worker_mode}")

    if packet.approval_routing != "advisor_relay":
        errors.append(f"Approval routing must be advisor_relay, got {packet.approval_routing}")

    if packet.playwright_enabled:
        errors.append("Playwright must be disabled by default")

    if packet.preferred_backend != ComputerUseBackend.GUI_COMPUTER_USE.value:
        errors.append(f"Preferred backend must be GUI_COMPUTER_USE, got {packet.preferred_backend}")

    if not packet.require_gui_healthcheck:
        errors.append("GUI healthcheck must be required")

    required_blocked = {
        "send_emails",
        "send_dms",
        "post_content",
        "edit_documents",
        "delete_files",
        "change_permissions",
        "change_account_settings",
        "capture_credentials",
        "process_payments",
    }
    missing_blocked = required_blocked - set(packet.blocked_actions)
    if missing_blocked:
        errors.append(f"Missing blocked actions: {sorted(missing_blocked)}")

    if not packet.work_order_id:
        errors.append("Work order ID is required")

    if not packet.target_account:
        errors.append("Target account is required")

    return errors
