"""Phase 84 approval views — governance approval display contracts.

Display-only approval representations. Phase 84 does not mutate
governance state unless an existing safe approval route exists.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


class ApprovalSurfaceAction(str, Enum):
    APPROVE = "approve"
    DENY = "deny"
    ESCALATE = "escalate"
    REQUEST_MORE_INFO = "request_more_info"
    DEFER = "defer"
    UNKNOWN = "unknown"


class ApprovalDisplayStatus(str, Enum):
    PENDING = "pending"
    DISPLAYED = "displayed"
    RESPONDED = "responded"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


def normalize_approval_surface_action(value: str) -> ApprovalSurfaceAction:
    try:
        return ApprovalSurfaceAction(value.lower().strip())
    except (ValueError, AttributeError):
        return ApprovalSurfaceAction.UNKNOWN


def normalize_approval_display_status(value: str) -> ApprovalDisplayStatus:
    try:
        return ApprovalDisplayStatus(value.lower().strip())
    except (ValueError, AttributeError):
        return ApprovalDisplayStatus.UNKNOWN


@dataclass
class ApprovalRequestView:
    approval_id: str
    title: str = ""
    summary: str = ""
    risk_level: str = ""
    authority_required: str = ""
    requested_action: str = ""
    environment: str = ""
    capability: str = ""
    adapter: str | None = None
    consequences: list[str] = field(default_factory=list)
    reversible: bool | None = None
    expires_at: str | None = None
    display_status: ApprovalDisplayStatus = ApprovalDisplayStatus.UNKNOWN
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "title": self.title,
            "summary": self.summary,
            "risk_level": self.risk_level,
            "authority_required": self.authority_required,
            "requested_action": self.requested_action,
            "environment": self.environment,
            "capability": self.capability,
            "adapter": self.adapter,
            "consequences": self.consequences,
            "reversible": self.reversible,
            "expires_at": self.expires_at,
            "display_status": self.display_status.value
            if isinstance(self.display_status, Enum)
            else self.display_status,
            "metadata": self.metadata,
        }


@dataclass
class ApprovalResponseEnvelope:
    response_id: str
    approval_id: str = ""
    surface_id: str = ""
    user_id: str | None = None
    action: ApprovalSurfaceAction = ApprovalSurfaceAction.UNKNOWN
    reason: str | None = None
    timestamp: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id": self.response_id,
            "approval_id": self.approval_id,
            "surface_id": self.surface_id,
            "user_id": self.user_id,
            "action": self.action.value if isinstance(self.action, Enum) else self.action,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class ApprovalResponseValidation:
    response_id: str
    valid: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    route_target: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id": self.response_id,
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "route_target": self.route_target,
            "metadata": self.metadata,
        }


def create_approval_request_view(
    approval_id: str,
    *,
    title: str = "",
    summary: str = "",
    risk_level: str = "",
    authority_required: str = "",
    requested_action: str = "",
    environment: str = "",
    capability: str = "",
    adapter: str | None = None,
    consequences: list[str] | None = None,
    reversible: bool | None = None,
    expires_at: str | None = None,
    display_status: ApprovalDisplayStatus = ApprovalDisplayStatus.PENDING,
    metadata: dict[str, Any] | None = None,
) -> ApprovalRequestView:
    return ApprovalRequestView(
        approval_id=approval_id,
        title=title,
        summary=summary,
        risk_level=risk_level,
        authority_required=authority_required,
        requested_action=requested_action,
        environment=environment,
        capability=capability,
        adapter=adapter,
        consequences=consequences or [],
        reversible=reversible,
        expires_at=expires_at,
        display_status=display_status,
        metadata=metadata or {},
    )


def validate_approval_response(response: ApprovalResponseEnvelope) -> ApprovalResponseValidation:
    errors: list[str] = []
    warnings: list[str] = []

    if not response.approval_id:
        errors.append("Missing approval_id")
    if not response.surface_id:
        errors.append("Missing surface_id")
    if response.action == ApprovalSurfaceAction.UNKNOWN:
        errors.append("Unknown approval action is invalid")

    route_target = ""
    if not errors:
        route_target = "governance"
        warnings.append(
            "Approval response routed to governance handler (Phase 84: envelope only, no mutation)"
        )

    return ApprovalResponseValidation(
        response_id=response.response_id,
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        route_target=route_target,
    )
