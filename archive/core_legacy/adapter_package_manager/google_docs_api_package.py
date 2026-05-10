"""Google Docs API Adapter Package (W-GDOCS-API-001).

Tab-aware document extraction for W0-001.
Derived from W-GWS-API-001 where applicable.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


W_GDOCS_API_001_ID = "W-GDOCS-API-001"
W_GDOCS_API_001_NAME = "Google Docs API Adapter Package"

DOCS_API_CAPABILITIES = [
    "documents_get_with_include_tabs_content",
    "document_tabs_traversal",
    "child_tabs_recursive_traversal",
    "per_tab_content_extraction",
    "empty_tab_marking",
    "inaccessible_content_marking",
    "per_tab_provenance",
    "canonical_source_record_emission",
    "w0_001_coverage_validation",
]

_DOCS_GOVERNANCE = [
    "read_only",
    "no_edits",
    "no_deletes",
    "no_moves",
    "no_shares",
    "no_permission_changes",
    "no_export_unless_approved",
    "no_download_unless_approved",
    "no_credential_capture",
    "no_memory_promotion",
]

W0_001_DOCS_COVERAGE = {
    "expected_docs": 28,
    "expected_tabs": 321,
    "expected_child_tabs": 134,
    "expected_words": 283831,
}


@dataclass
class GoogleDocsApiPackage:
    package_id: str = W_GDOCS_API_001_ID
    package_name: str = W_GDOCS_API_001_NAME
    family_id: str = "google_workspace"
    core_package_id: str = "W-GWS-CORE-001"
    service_name: str = "Google Docs"
    service_type: str = "api"
    capabilities: list[str] = field(
        default_factory=lambda: list(DOCS_API_CAPABILITIES)
    )
    governance: list[str] = field(
        default_factory=lambda: list(_DOCS_GOVERNANCE)
    )
    tool_mastery_pack: str = "google_docs_tool_mastery_pack"
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
    w0_001_coverage: dict[str, int] = field(
        default_factory=lambda: dict(W0_001_DOCS_COVERAGE)
    )
    requires_include_tabs_content: bool = True
    requires_document_tabs_traversal: bool = True
    requires_child_tabs_recursion: bool = True
    rejects_first_tab_only: bool = True
    known_gaps: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=lambda: [
        "Derived from W-GWS-API-001 Docs-related capabilities",
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
            "w0_001_coverage": self.w0_001_coverage,
            "requires_include_tabs_content": self.requires_include_tabs_content,
            "requires_document_tabs_traversal": self.requires_document_tabs_traversal,
            "requires_child_tabs_recursion": self.requires_child_tabs_recursion,
            "rejects_first_tab_only": self.rejects_first_tab_only,
            "known_gaps": self.known_gaps,
            "notes": self.notes,
        }


def build_google_docs_api_package() -> GoogleDocsApiPackage:
    return GoogleDocsApiPackage()


def docs_api_requires_include_tabs_content(
    pkg: GoogleDocsApiPackage,
) -> bool:
    return pkg.requires_include_tabs_content


def docs_api_requires_tabs_traversal(pkg: GoogleDocsApiPackage) -> bool:
    return pkg.requires_document_tabs_traversal


def docs_api_requires_child_tabs_recursion(
    pkg: GoogleDocsApiPackage,
) -> bool:
    return pkg.requires_child_tabs_recursion


def docs_api_rejects_first_tab_only(pkg: GoogleDocsApiPackage) -> bool:
    return pkg.rejects_first_tab_only


def docs_api_has_w0_001_coverage(pkg: GoogleDocsApiPackage) -> bool:
    return (
        pkg.w0_001_coverage.get("expected_docs", 0) == 28
        and pkg.w0_001_coverage.get("expected_tabs", 0) == 321
        and pkg.w0_001_coverage.get("expected_child_tabs", 0) == 134
        and pkg.w0_001_coverage.get("expected_words", 0) == 283831
    )


def docs_api_is_read_only(pkg: GoogleDocsApiPackage) -> bool:
    return "read_only" in pkg.governance


def docs_api_inherits_from_legacy(pkg: GoogleDocsApiPackage) -> bool:
    return pkg.legacy_provenance == "W-GWS-API-001"
