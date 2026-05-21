"""Phase 84 interface command envelope — typed command routing.

Every interface command declares source surface, action type,
and whether it is read-only, approval, or execution-intent.
No command executes in Phase 84. Routing is advisory.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


class InterfaceCommandType(str, Enum):
    READ_QUERY = "read_query"
    EXECUTION_INTENT = "execution_intent"
    APPROVAL_RESPONSE = "approval_response"
    NOTIFICATION_ACK = "notification_ack"
    MODE_CHANGE = "mode_change"
    SURFACE_STATE_CHANGE = "surface_state_change"
    VOICE_STATE_CHANGE = "voice_state_change"
    DASHBOARD_QUERY = "dashboard_query"
    TRACE_QUERY = "trace_query"
    REGISTRY_QUERY = "registry_query"
    ONTOLOGY_QUERY = "ontology_query"
    STORAGE_QUERY = "storage_query"
    MIGRATION_QUERY = "migration_query"
    WORKSTATION_QUERY = "workstation_query"
    UNKNOWN = "unknown"


class InterfaceCommandStatus(str, Enum):
    RECEIVED = "received"
    VALIDATED = "validated"
    REJECTED = "rejected"
    ROUTED = "routed"
    REQUIRES_APPROVAL = "requires_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"


class InterfaceActionRisk(str, Enum):
    NONE = "none"
    READ_ONLY = "read_only"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


_READ_ONLY_TYPES = frozenset(
    {
        InterfaceCommandType.READ_QUERY,
        InterfaceCommandType.DASHBOARD_QUERY,
        InterfaceCommandType.TRACE_QUERY,
        InterfaceCommandType.REGISTRY_QUERY,
        InterfaceCommandType.ONTOLOGY_QUERY,
        InterfaceCommandType.STORAGE_QUERY,
        InterfaceCommandType.MIGRATION_QUERY,
        InterfaceCommandType.WORKSTATION_QUERY,
        InterfaceCommandType.NOTIFICATION_ACK,
        InterfaceCommandType.MODE_CHANGE,
        InterfaceCommandType.SURFACE_STATE_CHANGE,
        InterfaceCommandType.VOICE_STATE_CHANGE,
    }
)


def normalize_command_type(value: str) -> InterfaceCommandType:
    try:
        return InterfaceCommandType(value.lower().strip())
    except (ValueError, AttributeError):
        return InterfaceCommandType.UNKNOWN


def normalize_command_status(value: str) -> InterfaceCommandStatus:
    try:
        return InterfaceCommandStatus(value.lower().strip())
    except (ValueError, AttributeError):
        return InterfaceCommandStatus.UNKNOWN


def normalize_action_risk(value: str) -> InterfaceActionRisk:
    try:
        return InterfaceActionRisk(value.lower().strip())
    except (ValueError, AttributeError):
        return InterfaceActionRisk.UNKNOWN


@dataclass
class InterfaceCommandEnvelope:
    command_id: str
    surface_id: str
    surface_type: str = ""
    user_id: str | None = None
    session_id: str | None = None
    command_type: InterfaceCommandType = InterfaceCommandType.UNKNOWN
    raw_intent: str | None = None
    normalized_intent: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    risk: InterfaceActionRisk = InterfaceActionRisk.UNKNOWN
    requires_governance: bool = False
    read_only: bool = True
    timestamp: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_id": self.command_id,
            "surface_id": self.surface_id,
            "surface_type": self.surface_type,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "command_type": self.command_type.value
            if isinstance(self.command_type, Enum)
            else self.command_type,
            "raw_intent": self.raw_intent,
            "normalized_intent": self.normalized_intent,
            "payload": self.payload,
            "risk": self.risk.value if isinstance(self.risk, Enum) else self.risk,
            "requires_governance": self.requires_governance,
            "read_only": self.read_only,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InterfaceCommandEnvelope:
        return cls(
            command_id=data.get("command_id", ""),
            surface_id=data.get("surface_id", ""),
            surface_type=data.get("surface_type", ""),
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            command_type=normalize_command_type(data.get("command_type", "unknown")),
            raw_intent=data.get("raw_intent"),
            normalized_intent=data.get("normalized_intent"),
            payload=data.get("payload", {}),
            risk=normalize_action_risk(data.get("risk", "unknown")),
            requires_governance=data.get("requires_governance", False),
            read_only=data.get("read_only", True),
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class InterfaceCommandValidation:
    command_id: str
    valid: bool = False
    status: InterfaceCommandStatus = InterfaceCommandStatus.UNKNOWN
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    route_target: str | None = None
    requires_control_plane: bool = False
    requires_governance: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_id": self.command_id,
            "valid": self.valid,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "errors": self.errors,
            "warnings": self.warnings,
            "route_target": self.route_target,
            "requires_control_plane": self.requires_control_plane,
            "requires_governance": self.requires_governance,
            "metadata": self.metadata,
        }


@dataclass
class InterfaceCommandRoute:
    command_id: str
    route_target: str = ""
    route_reason: str = ""
    allowed: bool = False
    read_only: bool = True
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_id": self.command_id,
            "route_target": self.route_target,
            "route_reason": self.route_reason,
            "allowed": self.allowed,
            "read_only": self.read_only,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def create_command_envelope(
    surface_id: str,
    command_type: InterfaceCommandType = InterfaceCommandType.UNKNOWN,
    *,
    surface_type: str = "",
    user_id: str | None = None,
    session_id: str | None = None,
    raw_intent: str | None = None,
    normalized_intent: str | None = None,
    payload: dict[str, Any] | None = None,
    risk: InterfaceActionRisk = InterfaceActionRisk.UNKNOWN,
    metadata: dict[str, Any] | None = None,
) -> InterfaceCommandEnvelope:
    cid = f"cmd_{hashlib.sha256(f'{surface_id}{_iso_now()}'.encode()).hexdigest()[:10]}"
    ro = command_type in _READ_ONLY_TYPES
    gov = (
        command_type == InterfaceCommandType.EXECUTION_INTENT
        or command_type == InterfaceCommandType.APPROVAL_RESPONSE
    )
    return InterfaceCommandEnvelope(
        command_id=cid,
        surface_id=surface_id,
        surface_type=surface_type,
        user_id=user_id,
        session_id=session_id,
        command_type=command_type,
        raw_intent=raw_intent,
        normalized_intent=normalized_intent,
        payload=payload or {},
        risk=risk
        if risk != InterfaceActionRisk.UNKNOWN
        else (InterfaceActionRisk.READ_ONLY if ro else InterfaceActionRisk.UNKNOWN),
        requires_governance=gov,
        read_only=ro,
        timestamp=_iso_now(),
        metadata=metadata or {},
    )


_ROUTE_MAP: dict[InterfaceCommandType, tuple[str, str]] = {
    InterfaceCommandType.READ_QUERY: ("observability", "read query"),
    InterfaceCommandType.DASHBOARD_QUERY: ("observability", "dashboard query"),
    InterfaceCommandType.TRACE_QUERY: ("observability", "trace query"),
    InterfaceCommandType.REGISTRY_QUERY: ("registry", "registry query"),
    InterfaceCommandType.ONTOLOGY_QUERY: ("ontology", "ontology query"),
    InterfaceCommandType.STORAGE_QUERY: ("storage", "storage query"),
    InterfaceCommandType.MIGRATION_QUERY: ("migration", "migration query"),
    InterfaceCommandType.WORKSTATION_QUERY: ("workstation", "workstation query"),
    InterfaceCommandType.EXECUTION_INTENT: (
        "control_plane",
        "execution intent requires control plane",
    ),
    InterfaceCommandType.APPROVAL_RESPONSE: (
        "governance",
        "approval response requires governance route",
    ),
    InterfaceCommandType.NOTIFICATION_ACK: ("interface", "notification acknowledgment"),
    InterfaceCommandType.MODE_CHANGE: ("workstation", "mode change"),
    InterfaceCommandType.SURFACE_STATE_CHANGE: ("interface", "surface state change"),
    InterfaceCommandType.VOICE_STATE_CHANGE: ("interface", "voice state change"),
}


def validate_interface_command(envelope: InterfaceCommandEnvelope) -> InterfaceCommandValidation:
    errors: list[str] = []
    warnings: list[str] = []

    if not envelope.surface_id:
        errors.append("Missing source surface_id")
    if envelope.command_type == InterfaceCommandType.UNKNOWN:
        errors.append("Unknown command type")

    route_info = _ROUTE_MAP.get(envelope.command_type)
    route_target = route_info[0] if route_info else None
    requires_cp = envelope.command_type == InterfaceCommandType.EXECUTION_INTENT
    requires_gov = envelope.requires_governance

    if requires_cp:
        warnings.append("Execution intent routes to control plane only")
    if requires_gov and envelope.command_type == InterfaceCommandType.APPROVAL_RESPONSE:
        warnings.append("Approval response routes to governance-compatible handler")

    valid = len(errors) == 0
    status = InterfaceCommandStatus.VALIDATED if valid else InterfaceCommandStatus.REJECTED

    return InterfaceCommandValidation(
        command_id=envelope.command_id,
        valid=valid,
        status=status,
        errors=errors,
        warnings=warnings,
        route_target=route_target,
        requires_control_plane=requires_cp,
        requires_governance=requires_gov,
    )


def route_interface_command(envelope: InterfaceCommandEnvelope) -> InterfaceCommandRoute:
    validation = validate_interface_command(envelope)
    if not validation.valid:
        return InterfaceCommandRoute(
            command_id=envelope.command_id,
            route_target="",
            route_reason="validation failed",
            allowed=False,
            read_only=envelope.read_only,
            warnings=validation.errors,
        )

    route_info = _ROUTE_MAP.get(envelope.command_type, ("unknown", "no route defined"))
    return InterfaceCommandRoute(
        command_id=envelope.command_id,
        route_target=route_info[0],
        route_reason=route_info[1],
        allowed=True,
        read_only=envelope.read_only,
        warnings=validation.warnings,
    )
