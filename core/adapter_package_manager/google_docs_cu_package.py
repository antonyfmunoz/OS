"""Google Docs Computer Use Adapter Package (W-GDOCS-CU-001).

Visible GUI / Computer Use Google Docs tab-aware navigation and
content extraction path for W0-001.
NOT 100% mature — requires CU infrastructure proof.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


W_GDOCS_CU_001_ID = "W-GDOCS-CU-001"
W_GDOCS_CU_001_NAME = "Google Docs Computer Use Adapter Package"

DOCS_CU_CAPABILITIES_REQUIRED = [
    "visible_local_gui_ownership",
    "correct_browser_profile_account_context",
    "docs_visibly_openable",
    "document_tabs_detectable",
    "child_tabs_detectable_navigable",
    "content_body_extraction",
    "scrolling_end_detection",
    "per_document_provenance",
    "per_tab_provenance",
    "empty_tab_marking",
    "inaccessible_tab_marking",
    "parity_against_w_gdocs_api_001_baseline",
]

DOCS_CU_GOVERNANCE = [
    "no_mutation",
    "no_credential_capture",
    "no_screenshots_unless_approved",
    "no_playwright_cdp_unless_approved",
    "read_only",
]

DOCS_CU_HARDENING_GAPS = [
    "CU infrastructure not yet available",
    "GUI ownership not yet proven",
    "Browser profile/account context not verified",
    "Document tab detection via CU not demonstrated",
    "Child tab navigation via CU not demonstrated",
    "Content/body extraction via CU not demonstrated",
    "Scrolling/end detection not demonstrated",
    "Per-tab provenance via CU not captured",
    "Parity against API baseline not run",
]


@dataclass
class GoogleDocsCuPackage:
    package_id: str = W_GDOCS_CU_001_ID
    package_name: str = W_GDOCS_CU_001_NAME
    family_id: str = "google_workspace"
    core_package_id: str = "W-GWS-CORE-001"
    service_name: str = "Google Docs"
    service_type: str = "computer_use"
    capabilities_required: list[str] = field(
        default_factory=lambda: list(DOCS_CU_CAPABILITIES_REQUIRED)
    )
    governance: list[str] = field(
        default_factory=lambda: list(DOCS_CU_GOVERNANCE)
    )
    auth_model: str = "BROWSER_PROFILE_SESSION_AUTH_CANDIDATE"
    current_maturity_percent: float = 0.0
    target_maturity_percent: float = 100.0
    is_mature: bool = False
    hardening_gaps: list[str] = field(
        default_factory=lambda: list(DOCS_CU_HARDENING_GAPS)
    )
    has_contract_mapping: bool = False
    has_governance: bool = True
    has_tests: bool = False
    has_tool_mastery: bool = False
    has_auth: bool = False
    parity_baseline: str = "W-GDOCS-API-001"
    notes: list[str] = field(default_factory=lambda: [
        "PARTIAL_NEEDS_HARDENING",
        "Do not mark 100% without tab/content/parity proof",
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
            "parity_baseline": self.parity_baseline,
            "notes": self.notes,
        }


def build_google_docs_cu_package() -> GoogleDocsCuPackage:
    return GoogleDocsCuPackage()


def docs_cu_is_mature(pkg: GoogleDocsCuPackage) -> bool:
    return pkg.is_mature and pkg.current_maturity_percent >= 100.0


def docs_cu_has_hardening_gaps(pkg: GoogleDocsCuPackage) -> bool:
    return len(pkg.hardening_gaps) > 0


def docs_cu_blocks_w0_001(pkg: GoogleDocsCuPackage) -> bool:
    return not docs_cu_is_mature(pkg)


def docs_cu_requires_api_parity(pkg: GoogleDocsCuPackage) -> bool:
    return pkg.parity_baseline == "W-GDOCS-API-001"
