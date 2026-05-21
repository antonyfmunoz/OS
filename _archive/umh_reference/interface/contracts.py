"""Phase 79 interface contracts — typed request/response for all UI surfaces.

CLI, API, Command Center, FAB, voice, messaging surfaces consume these
contracts. No execution logic. No adapter calls. No trace mutation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


class InterfaceType(str, Enum):
    CLI = "cli"
    API = "api"
    DESKTOP_COMMAND_CENTER = "desktop_command_center"
    DESKTOP_OVERLAY = "desktop_overlay"
    DESKTOP_MINIMIZED_WAVE = "desktop_minimized_wave"
    MOBILE_APP = "mobile_app"
    MOBILE_WIDGET = "mobile_widget"
    LIVE_ACTIVITY = "live_activity"
    VOICE = "voice"
    MESSAGING = "messaging"
    UNKNOWN = "unknown"


class InterfaceActionType(str, Enum):
    RUN = "run"
    STATUS = "status"
    BOOT = "boot"
    RESUME = "resume"
    QUERY_TRACES = "query_traces"
    QUERY_OUTCOMES = "query_outcomes"
    QUERY_FEEDBACK = "query_feedback"
    QUERY_MEMORY_CANDIDATES = "query_memory_candidates"
    QUERY_SYSTEM_STATUS = "query_system_status"
    QUERY_TIMELINE = "query_timeline"
    QUERY_FAILURES = "query_failures"
    QUERY_DECISION = "query_decision"
    ADD_USER_FEEDBACK = "add_user_feedback"
    APPROVAL_VIEW = "approval_view"
    MODE_SWITCH_REQUEST = "mode_switch_request"
    UNKNOWN = "unknown"


def normalize_interface_type(value: str) -> InterfaceType:
    value = value.strip().lower()
    for member in InterfaceType:
        if member.value == value:
            return member
    return InterfaceType.UNKNOWN


def normalize_interface_action_type(value: str) -> InterfaceActionType:
    value = value.strip().lower()
    for member in InterfaceActionType:
        if member.value == value:
            return member
    return InterfaceActionType.UNKNOWN


@dataclass
class InterfaceRequest:
    request_id: str
    user_id: str
    interface_type: InterfaceType = InterfaceType.UNKNOWN
    action_type: InterfaceActionType = InterfaceActionType.UNKNOWN
    payload: dict[str, Any] = field(default_factory=dict)
    workstation_context: dict[str, Any] | None = None
    auth_context: dict[str, Any] | None = None
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "interface_type": self.interface_type.value,
            "action_type": self.action_type.value,
            "payload": self.payload,
            "workstation_context": self.workstation_context,
            "auth_context": self.auth_context,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InterfaceRequest:
        return cls(
            request_id=data.get("request_id", ""),
            user_id=data.get("user_id", ""),
            interface_type=normalize_interface_type(data.get("interface_type", "unknown")),
            action_type=normalize_interface_action_type(data.get("action_type", "unknown")),
            payload=data.get("payload", {}),
            workstation_context=data.get("workstation_context"),
            auth_context=data.get("auth_context"),
            timestamp=data.get("timestamp", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class InterfaceResponse:
    request_id: str
    user_id: str
    status: str = "ok"
    trace_id: str | None = None
    display_payload: dict[str, Any] = field(default_factory=dict)
    governance_status: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "status": self.status,
            "trace_id": self.trace_id,
            "display_payload": self.display_payload,
            "governance_status": self.governance_status,
            "errors": self.errors,
            "warnings": self.warnings,
            "next_actions": self.next_actions,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InterfaceResponse:
        return cls(
            request_id=data.get("request_id", ""),
            user_id=data.get("user_id", ""),
            status=data.get("status", "ok"),
            trace_id=data.get("trace_id"),
            display_payload=data.get("display_payload", {}),
            governance_status=data.get("governance_status"),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
            next_actions=data.get("next_actions", []),
            timestamp=data.get("timestamp", ""),
            metadata=data.get("metadata", {}),
        )


def create_interface_request(
    user_id: str,
    action_type: InterfaceActionType = InterfaceActionType.UNKNOWN,
    interface_type: InterfaceType = InterfaceType.UNKNOWN,
    payload: dict[str, Any] | None = None,
) -> InterfaceRequest:
    return InterfaceRequest(
        request_id=f"req_{uuid.uuid4().hex[:12]}",
        user_id=user_id,
        interface_type=interface_type,
        action_type=action_type,
        payload=payload or {},
        timestamp=_iso_now(),
    )


def create_interface_response(
    request_id: str,
    user_id: str,
    *,
    status: str = "ok",
    display_payload: dict[str, Any] | None = None,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    next_actions: list[str] | None = None,
) -> InterfaceResponse:
    return InterfaceResponse(
        request_id=request_id,
        user_id=user_id,
        status=status,
        display_payload=display_payload or {},
        errors=errors or [],
        warnings=warnings or [],
        next_actions=next_actions or [],
        timestamp=_iso_now(),
    )
