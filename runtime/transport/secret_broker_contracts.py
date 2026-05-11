"""
Secret broker contracts for Phase 94D.9S.

Defines the abstraction layer for secret management.
Secrets are protected resources used by approved deterministic actions.
The model/advisor never sees secret values.

A SecretRef is metadata-only — like a file descriptor.
A SecretUseGrant authorizes a specific action to use a secret.
Secret values exist only inside local action execution, never in model context.

No secret values in repr/str/logs/messages/memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SecretScope(str, Enum):
    GOOGLE_WORKSPACE = "google_workspace"
    WHOP = "whop"
    STRIPE = "stripe"
    GITHUB = "github"
    DISCORD = "discord"
    GENERIC = "generic"


class SecretBackendType(str, Enum):
    LOCAL_ENV = "local_env"
    WINDOWS_CREDENTIAL_MANAGER = "windows_credential_manager"
    ONEPASSWORD = "1password"
    BITWARDEN = "bitwarden"
    DOPPLER = "doppler"
    VAULT = "vault"
    INFISICAL = "infisical"


class SecretUseStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    USED_SUCCESS = "used_success"
    USED_FAILURE = "used_failure"
    DENIED = "denied"
    EXPIRED = "expired"
    REVOKED = "revoked"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SecretRef:
    """Metadata-only reference to a secret. Never contains the value."""

    key: str
    scope: SecretScope
    account: str
    backend: SecretBackendType
    description: str = ""
    available: bool = False

    def __repr__(self) -> str:
        return (
            f"SecretRef(key='{self.key}', scope='{self.scope.value}', "
            f"account='{self.account}', available={self.available})"
        )

    def __str__(self) -> str:
        return f"[SECRET_REF:{self.key}@{self.scope.value}]"

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "scope": self.scope.value,
            "account": self.account,
            "backend": self.backend.value,
            "description": self.description,
            "available": self.available,
            "value": "[REDACTED]",
        }


@dataclass
class SecretUseRequest:
    """Request to use a secret for a specific action."""

    secret_ref: SecretRef
    action_id: str
    work_order_id: str
    requested_by: str
    reason: str
    requested_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "secret_key": self.secret_ref.key,
            "secret_scope": self.secret_ref.scope.value,
            "action_id": self.action_id,
            "work_order_id": self.work_order_id,
            "requested_by": self.requested_by,
            "reason": self.reason,
            "requested_at": self.requested_at,
            "secret_value": "[NEVER_INCLUDED]",
        }

    def __repr__(self) -> str:
        return (
            f"SecretUseRequest(key='{self.secret_ref.key}', "
            f"action='{self.action_id}', wo='{self.work_order_id}')"
        )


@dataclass
class SecretUseGrant:
    """Authorization to use a secret. Value is injected only at execution time."""

    secret_ref: SecretRef
    action_id: str
    work_order_id: str
    approved_by: str
    account_scope: str
    granted_at: str = field(default_factory=_now_iso)
    expires_at: str | None = None
    single_use: bool = True

    def __repr__(self) -> str:
        return (
            f"SecretUseGrant(key='{self.secret_ref.key}', "
            f"action='{self.action_id}', approved_by='{self.approved_by}', "
            f"value='[REDACTED]')"
        )

    def __str__(self) -> str:
        return f"[GRANT:{self.secret_ref.key}→{self.action_id}|approved_by:{self.approved_by}]"

    def to_dict(self) -> dict[str, Any]:
        return {
            "secret_key": self.secret_ref.key,
            "action_id": self.action_id,
            "work_order_id": self.work_order_id,
            "approved_by": self.approved_by,
            "account_scope": self.account_scope,
            "granted_at": self.granted_at,
            "expires_at": self.expires_at,
            "single_use": self.single_use,
            "secret_value": "[REDACTED]",
        }


@dataclass
class SecretUseAuditEvent:
    """Audit record of secret use. Never contains the secret value."""

    secret_ref: SecretRef
    action_id: str
    work_order_id: str
    status: SecretUseStatus
    performed_by: str
    performed_at: str = field(default_factory=_now_iso)
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "secret_key": self.secret_ref.key,
            "secret_scope": self.secret_ref.scope.value,
            "action_id": self.action_id,
            "work_order_id": self.work_order_id,
            "status": self.status.value,
            "performed_by": self.performed_by,
            "performed_at": self.performed_at,
            "detail": self.detail,
            "secret_value": "[NEVER_LOGGED]",
        }

    def __repr__(self) -> str:
        return (
            f"SecretUseAuditEvent(key='{self.secret_ref.key}', "
            f"action='{self.action_id}', status='{self.status.value}')"
        )


def validate_secret_use_request(request: SecretUseRequest) -> list[str]:
    """Validate a secret use request has all required fields."""
    errors: list[str] = []
    if not request.action_id:
        errors.append("action_id is required")
    if not request.work_order_id:
        errors.append("work_order_id is required")
    if not request.requested_by:
        errors.append("requested_by is required")
    if not request.secret_ref.key:
        errors.append("secret_ref.key is required")
    return errors


def validate_secret_use_grant(grant: SecretUseGrant) -> list[str]:
    """Validate a secret use grant has all required fields."""
    errors: list[str] = []
    if not grant.action_id:
        errors.append("action_id is required")
    if not grant.work_order_id:
        errors.append("work_order_id is required")
    if not grant.approved_by:
        errors.append("approved_by is required")
    if not grant.account_scope:
        errors.append("account_scope is required")
    return errors
