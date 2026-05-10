"""Google Workspace API Tab-Aware Adapter Path (W-GWS-API-001).

Defines the adapter path identity, capabilities, and build function
for the API tab-aware extraction path.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .full_path_maturity import PathDeclarationStatus

W_GWS_API_001_PATH_ID = "W-GWS-API-001"
W_GWS_API_001_PACKAGE_ID = "google_workspace"
W_GWS_API_001_PATH_NAME = "Google Workspace API Tab-Aware Extractor"

SUPPORTED_CAPABILITIES = [
    "google_drive_inventory",
    "google_drive_metadata_extraction",
    "google_docs_tab_aware_extraction",
    "google_docs_child_tab_traversal",
    "canonical_source_record_emission",
    "source_graph_generation_support",
    "ingestion_coverage_validation",
]

EXCLUDED_GAPS = [
    "CU parity remains separate path",
    "MCP remains candidate path",
    "CLI direct remains candidate path",
    "export remains approval path",
]


@dataclass
class GoogleWorkspaceApiAdapterPath:
    package_id: str = W_GWS_API_001_PACKAGE_ID
    path_id: str = W_GWS_API_001_PATH_ID
    path_name: str = W_GWS_API_001_PATH_NAME
    path_type: str = "API"
    declaration_status: PathDeclarationStatus = PathDeclarationStatus.DECLARED
    current_status: str = "complete"
    target_maturity_percent: float = 100.0
    current_maturity_percent: float = 0.0
    supported_capabilities: list[str] = field(
        default_factory=lambda: list(SUPPORTED_CAPABILITIES)
    )
    required_auth_methods: list[str] = field(
        default_factory=lambda: ["OAUTH_USER_CONSENT_OPAQUE_TOKEN_CACHE"]
    )
    tool_mastery_pack: str = "google_docs_tool_mastery_pack"
    governance_policy: str = "w_gws_api_001_governance_policy"
    canonical_contract: str = "w_gws_api_001_canonical_contract_mapping"
    tests: list[str] = field(
        default_factory=lambda: [
            "test_w_gws_api_001_adapter_path",
            "test_w_gws_api_001_contract_mapping",
            "test_w_gws_api_001_governance",
            "test_w_gws_api_001_maturity",
        ]
    )
    known_gaps: list[str] = field(default_factory=list)
    excluded_gaps: list[str] = field(
        default_factory=lambda: list(EXCLUDED_GAPS)
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "path_id": self.path_id,
            "path_name": self.path_name,
            "path_type": self.path_type,
            "declaration_status": self.declaration_status.value,
            "current_status": self.current_status,
            "target_maturity_percent": self.target_maturity_percent,
            "current_maturity_percent": self.current_maturity_percent,
            "supported_capabilities": self.supported_capabilities,
            "required_auth_methods": self.required_auth_methods,
            "tool_mastery_pack": self.tool_mastery_pack,
            "governance_policy": self.governance_policy,
            "canonical_contract": self.canonical_contract,
            "tests": self.tests,
            "known_gaps": self.known_gaps,
            "excluded_gaps": self.excluded_gaps,
        }


def build_google_workspace_api_tab_aware_path() -> GoogleWorkspaceApiAdapterPath:
    return GoogleWorkspaceApiAdapterPath()
