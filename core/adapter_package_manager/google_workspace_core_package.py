"""Google Workspace Core Foundation Package (W-GWS-CORE-001).

Shared foundation for all Google Workspace service adapter packages.
Contains auth/session model, governance defaults, no-secret policy,
rate limit doctrine, and workspace-level Tool Mastery requirements.

Maturity here means the shared Drive/Docs foundation for W0-001 is ready.
It does NOT imply Gmail/Sheets/Slides maturity.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


W_GWS_CORE_001_ID = "W-GWS-CORE-001"
W_GWS_CORE_001_NAME = "Google Workspace Core Foundation Package"

_SHARED_AUTH_MODELS = [
    "OAUTH_USER_CONSENT_OPAQUE_TOKEN_CACHE",
    "BROWSER_PROFILE_SESSION_AUTH_CANDIDATE",
    "SERVICE_ACCOUNT_DOMAIN_WIDE_DELEGATION_FUTURE",
]

_NO_SECRET_POLICY = [
    "no_credential_capture",
    "no_token_reading",
    "no_cookie_reading",
    "no_api_key_capture",
    "no_secret_logging",
    "auth_token_opaque",
]

_SHARED_GOVERNANCE_DEFAULTS = [
    "read_only_default",
    "no_mutation_unless_approved",
    "no_export_unless_approved",
    "no_download_unless_approved",
    "no_permission_changes",
    "no_account_switching_unless_approved",
    "instance_scope_preservation",
    "no_memory_promotion",
    "no_global_canon_write",
]

_RATE_LIMIT_DOCTRINE = [
    "respect_google_api_quota",
    "exponential_backoff_on_429",
    "per_service_rate_awareness",
    "no_bulk_scraping",
]


@dataclass
class GoogleWorkspaceCorePackage:
    package_id: str = W_GWS_CORE_001_ID
    package_name: str = W_GWS_CORE_001_NAME
    shared_auth_models: list[str] = field(
        default_factory=lambda: list(_SHARED_AUTH_MODELS)
    )
    no_secret_policy: list[str] = field(
        default_factory=lambda: list(_NO_SECRET_POLICY)
    )
    shared_governance_defaults: list[str] = field(
        default_factory=lambda: list(_SHARED_GOVERNANCE_DEFAULTS)
    )
    rate_limit_doctrine: list[str] = field(
        default_factory=lambda: list(_RATE_LIMIT_DOCTRINE)
    )
    workspace_tool_mastery_pack: str = "google_workspace_tool_mastery_pack"
    current_maturity_percent: float = 100.0
    target_maturity_percent: float = 100.0
    is_mature: bool = True
    scoped_to_w0_001: bool = True
    implies_gmail_maturity: bool = False
    implies_sheets_maturity: bool = False
    implies_slides_maturity: bool = False
    notes: list[str] = field(default_factory=lambda: [
        "Mature for W0-001 shared Drive/Docs foundation",
        "Does NOT imply Gmail/Sheets/Slides/Calendar maturity",
    ])

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "package_name": self.package_name,
            "shared_auth_models": self.shared_auth_models,
            "no_secret_policy": self.no_secret_policy,
            "shared_governance_defaults": self.shared_governance_defaults,
            "rate_limit_doctrine": self.rate_limit_doctrine,
            "workspace_tool_mastery_pack": self.workspace_tool_mastery_pack,
            "current_maturity_percent": self.current_maturity_percent,
            "target_maturity_percent": self.target_maturity_percent,
            "is_mature": self.is_mature,
            "scoped_to_w0_001": self.scoped_to_w0_001,
            "implies_gmail_maturity": self.implies_gmail_maturity,
            "implies_sheets_maturity": self.implies_sheets_maturity,
            "implies_slides_maturity": self.implies_slides_maturity,
            "notes": self.notes,
        }


def build_google_workspace_core_package() -> GoogleWorkspaceCorePackage:
    return GoogleWorkspaceCorePackage()


def core_has_shared_auth(pkg: GoogleWorkspaceCorePackage) -> bool:
    return len(pkg.shared_auth_models) > 0


def core_has_no_secret_policy(pkg: GoogleWorkspaceCorePackage) -> bool:
    return "no_credential_capture" in pkg.no_secret_policy


def core_has_shared_governance(pkg: GoogleWorkspaceCorePackage) -> bool:
    return "read_only_default" in pkg.shared_governance_defaults


def core_does_not_imply_gmail(pkg: GoogleWorkspaceCorePackage) -> bool:
    return not pkg.implies_gmail_maturity


def core_does_not_imply_sheets(pkg: GoogleWorkspaceCorePackage) -> bool:
    return not pkg.implies_sheets_maturity
