"""
Auth layer contracts for Phase 96.3.

OAuth is authorization, not backend.
Browser profile session is authorization/session context, not backend.
Secret values never enter model context.
Auth profile is selected before or alongside backend selection.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AuthMethodType(str, Enum):
    OAUTH_USER_CONSENT = "oauth_user_consent"
    OAUTH_DEVICE_FLOW = "oauth_device_flow"
    SERVICE_ACCOUNT = "service_account"
    DOMAIN_WIDE_DELEGATION = "domain_wide_delegation"
    API_KEY = "api_key"
    PERSONAL_ACCESS_TOKEN = "personal_access_token"
    PASSWORD_MANAGER_SECRET = "password_manager_secret"
    LOCAL_ENV_SECRET = "local_env_secret"
    BROWSER_SESSION_PROFILE = "browser_session_profile"
    SSO_SAML = "sso_saml"
    MANUAL_LOGIN = "manual_login"
    ADMIN_GRANTED_APP_CONSENT = "admin_granted_app_consent"
    LOCAL_MACHINE_IDENTITY = "local_machine_identity"
    SSH_KEY = "ssh_key"
    CERTIFICATE_MTLS = "certificate_mtls"
    UNKNOWN = "unknown"


class AuthMaterialHandling(str, Enum):
    SECRET_BROKER_REQUIRED = "secret_broker_required"
    MODEL_NEVER_SEES_SECRET = "model_never_sees_secret"
    LOCAL_ONLY = "local_only"
    TOKEN_CACHE_OPAQUE = "token_cache_opaque"
    BROWSER_PROFILE_OPAQUE = "browser_profile_opaque"
    MANUAL_ONLY = "manual_only"
    NOT_SECRET = "not_secret"


def is_auth_not_backend(method: AuthMethodType) -> bool:
    """Auth methods are authorization layers, not extraction backends."""
    return True


def is_browser_profile_auth_not_backend(method: AuthMethodType) -> bool:
    """Browser profile session is auth/session context, not backend."""
    return method == AuthMethodType.BROWSER_SESSION_PROFILE


def secret_must_not_enter_model_context() -> bool:
    """Secret values must never be visible to the model."""
    return True


@dataclass
class AuthProfile:
    """Authorization profile for a backend or source access."""

    auth_id: str
    method_type: AuthMethodType
    source_system: str = ""
    account_scope: str = ""
    allowed_backends: list[str] = field(default_factory=list)
    secret_handling: AuthMaterialHandling = AuthMaterialHandling.MODEL_NEVER_SEES_SECRET
    scope_description: str = ""
    token_exposure_allowed: bool = False
    model_visibility: bool = False
    rotation_required: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "auth_id": self.auth_id,
            "method_type": self.method_type.value,
            "source_system": self.source_system,
            "account_scope": self.account_scope,
            "allowed_backends": self.allowed_backends,
            "secret_handling": self.secret_handling.value,
            "scope_description": self.scope_description,
            "token_exposure_allowed": self.token_exposure_allowed,
            "model_visibility": self.model_visibility,
            "rotation_required": self.rotation_required,
            "notes": self.notes,
        }
