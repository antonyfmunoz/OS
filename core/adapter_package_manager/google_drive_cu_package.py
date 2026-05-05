"""Google Drive Computer Use Adapter Package (W-GDRIVE-CU-001).

Visible GUI / Computer Use Drive inventory path for W0-001.
NOT 100% mature — requires CU infrastructure proof.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


W_GDRIVE_CU_001_ID = "W-GDRIVE-CU-001"
W_GDRIVE_CU_001_NAME = "Google Drive Computer Use Adapter Package"

DRIVE_CU_CAPABILITIES_REQUIRED = [
    "visible_local_gui_ownership",
    "correct_browser_profile_account_context",
    "google_drive_visible_and_reachable",
    "my_drive_scope_visible",
    "file_inventory_visible_extractable",
    "metadata_for_api_parity_comparison",
    "provenance_capture",
]

DRIVE_CU_GOVERNANCE = [
    "no_mutation",
    "no_credential_capture",
    "no_screenshots_unless_approved",
    "no_playwright_cdp_unless_approved",
    "read_only",
]

DRIVE_CU_HARDENING_GAPS = [
    "CU infrastructure not yet available",
    "GUI ownership not yet proven",
    "Browser profile/account context not verified",
    "Drive visibility not yet confirmed",
    "File inventory extraction via CU not demonstrated",
    "API parity comparison not yet run",
]


@dataclass
class GoogleDriveCuPackage:
    package_id: str = W_GDRIVE_CU_001_ID
    package_name: str = W_GDRIVE_CU_001_NAME
    family_id: str = "google_workspace"
    core_package_id: str = "W-GWS-CORE-001"
    service_name: str = "Google Drive"
    service_type: str = "computer_use"
    capabilities_required: list[str] = field(
        default_factory=lambda: list(DRIVE_CU_CAPABILITIES_REQUIRED)
    )
    governance: list[str] = field(
        default_factory=lambda: list(DRIVE_CU_GOVERNANCE)
    )
    auth_model: str = "BROWSER_PROFILE_SESSION_AUTH_CANDIDATE"
    current_maturity_percent: float = 0.0
    target_maturity_percent: float = 100.0
    is_mature: bool = False
    hardening_gaps: list[str] = field(
        default_factory=lambda: list(DRIVE_CU_HARDENING_GAPS)
    )
    has_contract_mapping: bool = False
    has_governance: bool = True
    has_tests: bool = False
    has_tool_mastery: bool = False
    has_auth: bool = False
    notes: list[str] = field(default_factory=lambda: [
        "PARTIAL_NEEDS_HARDENING",
        "Do not mark 100% without GUI proof",
    ])

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "package_name": self.package_name,
            "family_id": self.family_id,
            "core_package_id": self.core_package_id,
            "service_name": self.service_name,
            "service_type": self.service_type,
            "capabilities_required": self.capabilities_required,
            "governance": self.governance,
            "auth_model": self.auth_model,
            "current_maturity_percent": self.current_maturity_percent,
            "target_maturity_percent": self.target_maturity_percent,
            "is_mature": self.is_mature,
            "hardening_gaps": self.hardening_gaps,
            "has_contract_mapping": self.has_contract_mapping,
            "has_governance": self.has_governance,
            "has_tests": self.has_tests,
            "has_tool_mastery": self.has_tool_mastery,
            "has_auth": self.has_auth,
            "notes": self.notes,
        }


def build_google_drive_cu_package() -> GoogleDriveCuPackage:
    return GoogleDriveCuPackage()


def drive_cu_is_mature(pkg: GoogleDriveCuPackage) -> bool:
    return pkg.is_mature and pkg.current_maturity_percent >= 100.0


def drive_cu_has_hardening_gaps(pkg: GoogleDriveCuPackage) -> bool:
    return len(pkg.hardening_gaps) > 0


def drive_cu_blocks_w0_001(pkg: GoogleDriveCuPackage) -> bool:
    return not drive_cu_is_mature(pkg)
