"""Google Drive API Adapter Package (W-GDRIVE-API-001).

Drive inventory and metadata extraction for W0-001.
Derived from W-GWS-API-001 where applicable.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


W_GDRIVE_API_001_ID = "W-GDRIVE-API-001"
W_GDRIVE_API_001_NAME = "Google Drive API Adapter Package"

DRIVE_API_CAPABILITIES = [
    "google_drive_inventory",
    "google_drive_metadata_extraction",
    "folder_file_identification",
    "mime_type_detection",
    "modified_time_extraction",
    "owner_metadata_extraction",
    "source_provenance",
    "in_scope_file_listing",
]

_DRIVE_GOVERNANCE = [
    "read_only",
    "no_permission_changes",
    "no_edits",
    "no_deletes",
    "no_moves",
    "no_shares",
    "no_export_unless_approved",
    "no_download_unless_approved",
    "no_credential_capture",
]


@dataclass
class GoogleDriveApiPackage:
    package_id: str = W_GDRIVE_API_001_ID
    package_name: str = W_GDRIVE_API_001_NAME
    family_id: str = "google_workspace"
    core_package_id: str = "W-GWS-CORE-001"
    service_name: str = "Google Drive"
    service_type: str = "api"
    capabilities: list[str] = field(
        default_factory=lambda: list(DRIVE_API_CAPABILITIES)
    )
    governance: list[str] = field(
        default_factory=lambda: list(_DRIVE_GOVERNANCE)
    )
    tool_mastery_pack: str = "google_drive_tool_mastery_pack"
    auth_model: str = "OAUTH_USER_CONSENT_OPAQUE_TOKEN_CACHE"
    current_maturity_percent: float = 100.0
    target_maturity_percent: float = 100.0
    is_mature: bool = True
    legacy_provenance: str = "W-GWS-API-001"
    has_contract_mapping: bool = True
    has_governance: bool = True
    has_tests: bool = True
    has_tool_mastery: bool = True
    has_auth: bool = True
    known_gaps: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=lambda: [
        "Derived from W-GWS-API-001 Drive-related capabilities",
    ])

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "package_name": self.package_name,
            "family_id": self.family_id,
            "core_package_id": self.core_package_id,
            "service_name": self.service_name,
            "service_type": self.service_type,
            "capabilities": self.capabilities,
            "governance": self.governance,
            "tool_mastery_pack": self.tool_mastery_pack,
            "auth_model": self.auth_model,
            "current_maturity_percent": self.current_maturity_percent,
            "target_maturity_percent": self.target_maturity_percent,
            "is_mature": self.is_mature,
            "legacy_provenance": self.legacy_provenance,
            "has_contract_mapping": self.has_contract_mapping,
            "has_governance": self.has_governance,
            "has_tests": self.has_tests,
            "has_tool_mastery": self.has_tool_mastery,
            "has_auth": self.has_auth,
            "known_gaps": self.known_gaps,
            "notes": self.notes,
        }


def build_google_drive_api_package() -> GoogleDriveApiPackage:
    return GoogleDriveApiPackage()


def drive_api_supports_inventory(pkg: GoogleDriveApiPackage) -> bool:
    return "google_drive_inventory" in pkg.capabilities


def drive_api_supports_metadata(pkg: GoogleDriveApiPackage) -> bool:
    return "google_drive_metadata_extraction" in pkg.capabilities


def drive_api_is_read_only(pkg: GoogleDriveApiPackage) -> bool:
    return "read_only" in pkg.governance


def drive_api_inherits_from_legacy(pkg: GoogleDriveApiPackage) -> bool:
    return pkg.legacy_provenance == "W-GWS-API-001"
