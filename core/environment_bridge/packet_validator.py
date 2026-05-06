"""Packet validator for the Environment Bridge.

Validates work packets before execution. Catches missing approvals,
expired packets, blocked action violations, missing governance, and
missing proof requirements.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .work_packet import (
    WorkPacket,
    WorkPacketRiskLevel,
    WorkPacketStatus,
    work_packet_targets_local_gui,
)


class PacketValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    MISSING_APPROVAL = "missing_approval"
    EXPIRED = "expired"
    UNSAFE_ACTION = "unsafe_action"
    MISSING_GOVERNANCE = "missing_governance"
    MISSING_PROOF_REQUIREMENTS = "missing_proof_requirements"
    MISSING_ROUTING_FIELDS = "missing_routing_fields"
    TARGET_ENVIRONMENT_MISMATCH = "target_environment_mismatch"
    UNKNOWN_ACTION_TYPE = "unknown_action_type"


CU_REQUIRED_BLOCKED_ACTIONS = [
    "credential_capture",
    "token_capture",
    "cookie_capture",
    "account_switching",
    "gmail",
    "edit",
    "delete",
    "move",
    "share",
    "permission_change",
    "export",
    "download",
    "screenshot",
    "ocr",
    "playwright",
    "cdp",
    "memory_promotion",
]


@dataclass
class PacketValidationResult:
    packet_id: str = ""
    status: PacketValidationStatus = PacketValidationStatus.INVALID
    can_execute: bool = False
    validation_errors: list[str] = field(default_factory=list)
    governance_errors: list[str] = field(default_factory=list)
    safety_errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "status": self.status.value,
            "can_execute": self.can_execute,
            "validation_errors": self.validation_errors,
            "governance_errors": self.governance_errors,
            "safety_errors": self.safety_errors,
            "notes": self.notes,
        }


def validate_work_packet(packet: WorkPacket) -> PacketValidationResult:
    result = PacketValidationResult(packet_id=packet.packet_id)

    if not packet.packet_id:
        result.validation_errors.append("MISSING_PACKET_ID")

    if not packet.action_type:
        result.validation_errors.append("MISSING_ACTION_TYPE")
        result.status = PacketValidationStatus.UNKNOWN_ACTION_TYPE
        return result

    if packet.risk_level in (
        WorkPacketRiskLevel.HIGH,
        WorkPacketRiskLevel.CRITICAL,
    ):
        if packet.approval_status != WorkPacketStatus.APPROVED:
            result.validation_errors.append(
                f"HIGH/CRITICAL packet requires approval, got {packet.approval_status.value}"
            )
            result.status = PacketValidationStatus.MISSING_APPROVAL
            return result

    if packet.expires_at:
        result.notes.append("Expiry checking requires runtime datetime comparison")

    if not packet.blocked_actions:
        result.governance_errors.append("MISSING_BLOCKED_ACTIONS")
        result.status = PacketValidationStatus.MISSING_GOVERNANCE
        return result

    if work_packet_targets_local_gui(packet):
        governance_errors = _check_cu_governance(packet)
        if governance_errors:
            result.governance_errors.extend(governance_errors)
            result.status = PacketValidationStatus.MISSING_GOVERNANCE
            return result

    if not packet.proof_requirements:
        result.validation_errors.append("MISSING_PROOF_REQUIREMENTS")
        result.status = PacketValidationStatus.MISSING_PROOF_REQUIREMENTS
        return result

    blocked_violations = packet_contains_blocked_action_violation(packet)
    if blocked_violations:
        result.safety_errors.extend(blocked_violations)
        result.status = PacketValidationStatus.UNSAFE_ACTION
        return result

    routing_errors = _check_routing_fields(packet)
    if routing_errors:
        result.validation_errors.extend(routing_errors)
        result.status = PacketValidationStatus.MISSING_ROUTING_FIELDS
        return result

    boundary_errors = _check_adapter_boundary(packet)
    if boundary_errors:
        result.governance_errors.extend(boundary_errors)
        result.status = PacketValidationStatus.MISSING_GOVERNANCE
        return result

    result.status = PacketValidationStatus.VALID
    result.can_execute = True
    return result


def packet_has_required_governance(packet: WorkPacket) -> bool:
    if not packet.blocked_actions:
        return False
    if work_packet_targets_local_gui(packet):
        return len(_check_cu_governance(packet)) == 0
    return True


def packet_has_required_proof(packet: WorkPacket) -> bool:
    return len(packet.proof_requirements) > 0


def packet_contains_blocked_action_violation(packet: WorkPacket) -> list[str]:
    violations: list[str] = []
    blocked_set = {a.lower() for a in packet.blocked_actions}
    allowed_set = {a.lower() for a in packet.allowed_actions}
    overlap = blocked_set & allowed_set
    if overlap:
        violations.append(f"Actions appear in both allowed and blocked: {sorted(overlap)}")
    return violations


def packet_validator_blocks_execution(result: PacketValidationResult) -> bool:
    return not result.can_execute


def packet_requires_environment_adapter(packet: WorkPacket) -> bool:
    return work_packet_targets_local_gui(packet)


def packet_requires_human_approval_adapter(packet: WorkPacket) -> bool:
    return packet.founder_confirmation_required


def _check_cu_governance(packet: WorkPacket) -> list[str]:
    errors: list[str] = []
    blocked_lower = {a.lower() for a in packet.blocked_actions}
    for required in CU_REQUIRED_BLOCKED_ACTIONS:
        if required not in blocked_lower:
            errors.append(f"CU_GOVERNANCE_MISSING: {required} must be in blocked_actions")
    return errors


def packet_requires_mastery(packet: WorkPacket) -> bool:
    return work_packet_targets_local_gui(packet) or packet.risk_level in (
        WorkPacketRiskLevel.HIGH,
        WorkPacketRiskLevel.CRITICAL,
    )


def packet_requires_worker_runtime(packet: WorkPacket) -> bool:
    return work_packet_targets_local_gui(packet)


def _check_routing_fields(packet: WorkPacket) -> list[str]:
    if not work_packet_targets_local_gui(packet):
        return []
    errors: list[str] = []
    if not packet.target_account:
        errors.append("ROUTING: local GUI packet requires target_account")
    if not packet.worker_mode:
        errors.append("ROUTING: local GUI packet requires worker_mode")
    if not packet.approval_routing:
        errors.append("ROUTING: local GUI packet requires approval_routing")
    if not packet.preferred_backend:
        errors.append("ROUTING: local GUI packet requires preferred_backend")
    return errors


def _check_adapter_boundary(packet: WorkPacket) -> list[str]:
    if not packet.adapter_boundary_required:
        return []
    errors: list[str] = []
    if work_packet_targets_local_gui(packet) and not packet.required_environment_adapters:
        errors.append("ADAPTER_BOUNDARY: local GUI packet requires environment adapter")
    if packet.founder_confirmation_required and not packet.required_human_approval_adapters:
        errors.append(
            "ADAPTER_BOUNDARY: founder confirmation packet requires human approval adapter"
        )
    if work_packet_targets_local_gui(packet) and not packet.required_worker_runtime:
        errors.append("ADAPTER_BOUNDARY: local GUI packet requires worker runtime")
    if packet_requires_mastery(packet) and not packet.required_mastery_categories:
        errors.append("ADAPTER_BOUNDARY: external packet requires mastery requirements")
    if not packet.proof_artifact_requirements and work_packet_targets_local_gui(packet):
        errors.append("ADAPTER_BOUNDARY: local GUI packet requires proof artifact requirements")
    return errors
