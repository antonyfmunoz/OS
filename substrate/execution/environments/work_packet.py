"""Work Packet contract for the Environment Bridge.

Structured, governed work packets that flow between VPS orchestrator
and local execution environments. Every packet carries its own
approval status, risk level, allowed/blocked actions, and proof
requirements. No packet executes without explicit approval.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class WorkPacketStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    DISPATCHED = "dispatched"
    CLAIMED = "claimed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class WorkPacketRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkPacketExecutionEnvironment(str, Enum):
    VPS = "vps"
    LOCAL_WSL = "local_wsl"
    LOCAL_WINDOWS_GUI = "local_windows_gui"
    LOCAL_TMUX = "local_tmux"
    LOCAL_BROWSER = "local_browser"
    REMOTE_API = "remote_api"


@dataclass
class WorkPacket:
    packet_id: str = ""
    work_order_id: str = ""
    title: str = ""
    description: str = ""
    action_type: str = ""
    target_environment: list[str] = field(default_factory=list)
    required_adapter_packages: list[str] = field(default_factory=list)
    required_tool_mastery_packs: list[str] = field(default_factory=list)
    risk_level: WorkPacketRiskLevel = WorkPacketRiskLevel.LOW
    approval_status: WorkPacketStatus = WorkPacketStatus.DRAFT
    founder_confirmation_required: bool = False
    allowed_actions: list[str] = field(default_factory=list)
    blocked_actions: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    proof_requirements: list[str] = field(default_factory=list)
    timeout_seconds: int = 3600
    created_at: str = ""
    expires_at: str = ""
    status: WorkPacketStatus = WorkPacketStatus.DRAFT
    external_interaction_id: str = ""
    adapter_boundary_required: bool = True
    required_environment_adapters: list[str] = field(default_factory=list)
    required_human_approval_adapters: list[str] = field(default_factory=list)
    required_mastery_categories: list[str] = field(default_factory=list)
    required_worker_runtime: str = ""
    proof_artifact_requirements: list[str] = field(default_factory=list)
    target_account: str = ""
    worker_mode: str = ""
    approval_routing: str = ""
    preferred_backend: str = ""
    playwright_enabled: bool = False
    screenshot_capture: bool = False
    cdp_enabled: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "work_order_id": self.work_order_id,
            "title": self.title,
            "description": self.description,
            "action_type": self.action_type,
            "target_environment": self.target_environment,
            "required_adapter_packages": self.required_adapter_packages,
            "required_tool_mastery_packs": self.required_tool_mastery_packs,
            "risk_level": self.risk_level.value,
            "approval_status": self.approval_status.value,
            "founder_confirmation_required": self.founder_confirmation_required,
            "allowed_actions": self.allowed_actions,
            "blocked_actions": self.blocked_actions,
            "expected_outputs": self.expected_outputs,
            "proof_requirements": self.proof_requirements,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status.value,
            "external_interaction_id": self.external_interaction_id,
            "adapter_boundary_required": self.adapter_boundary_required,
            "required_environment_adapters": self.required_environment_adapters,
            "required_human_approval_adapters": self.required_human_approval_adapters,
            "required_mastery_categories": self.required_mastery_categories,
            "required_worker_runtime": self.required_worker_runtime,
            "proof_artifact_requirements": self.proof_artifact_requirements,
            "target_account": self.target_account,
            "worker_mode": self.worker_mode,
            "approval_routing": self.approval_routing,
            "preferred_backend": self.preferred_backend,
            "playwright_enabled": self.playwright_enabled,
            "screenshot_capture": self.screenshot_capture,
            "cdp_enabled": self.cdp_enabled,
            "notes": self.notes,
        }


def build_work_packet(
    packet_id: str,
    work_order_id: str,
    title: str,
    description: str = "",
    action_type: str = "",
    target_environment: list[str] | None = None,
    risk_level: WorkPacketRiskLevel = WorkPacketRiskLevel.LOW,
    approval_status: WorkPacketStatus = WorkPacketStatus.DRAFT,
    founder_confirmation_required: bool = False,
    allowed_actions: list[str] | None = None,
    blocked_actions: list[str] | None = None,
    expected_outputs: list[str] | None = None,
    proof_requirements: list[str] | None = None,
    timeout_seconds: int = 3600,
) -> WorkPacket:
    return WorkPacket(
        packet_id=packet_id,
        work_order_id=work_order_id,
        title=title,
        description=description,
        action_type=action_type,
        target_environment=target_environment or [],
        risk_level=risk_level,
        approval_status=approval_status,
        founder_confirmation_required=founder_confirmation_required,
        allowed_actions=allowed_actions or [],
        blocked_actions=blocked_actions or [],
        expected_outputs=expected_outputs or [],
        proof_requirements=proof_requirements or [],
        timeout_seconds=timeout_seconds,
        created_at=datetime.now(timezone.utc).isoformat(),
        status=approval_status,
    )


def work_packet_requires_approval(packet: WorkPacket) -> bool:
    return packet.risk_level in (
        WorkPacketRiskLevel.HIGH,
        WorkPacketRiskLevel.CRITICAL,
    )


def work_packet_is_executable(packet: WorkPacket) -> bool:
    if packet.approval_status != WorkPacketStatus.APPROVED:
        return False
    if not packet.blocked_actions:
        return False
    return True


def work_packet_targets_local_gui(packet: WorkPacket) -> bool:
    gui_envs = {
        WorkPacketExecutionEnvironment.LOCAL_WINDOWS_GUI.value,
        WorkPacketExecutionEnvironment.LOCAL_BROWSER.value,
    }
    return bool(set(packet.target_environment) & gui_envs)


def work_packet_blocks_if_unapproved(packet: WorkPacket) -> bool:
    if packet.risk_level in (
        WorkPacketRiskLevel.HIGH,
        WorkPacketRiskLevel.CRITICAL,
    ):
        return packet.approval_status != WorkPacketStatus.APPROVED
    return False


def summarize_work_packet(packet: WorkPacket) -> dict[str, Any]:
    return {
        "packet_id": packet.packet_id,
        "title": packet.title,
        "action_type": packet.action_type,
        "risk_level": packet.risk_level.value,
        "approval_status": packet.approval_status.value,
        "status": packet.status.value,
        "target_environment": packet.target_environment,
        "targets_local_gui": work_packet_targets_local_gui(packet),
        "is_executable": work_packet_is_executable(packet),
        "requires_approval": work_packet_requires_approval(packet),
        "blocked_if_unapproved": work_packet_blocks_if_unapproved(packet),
        "founder_confirmation_required": packet.founder_confirmation_required,
    }
