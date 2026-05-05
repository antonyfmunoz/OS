"""Adapter Path Inventory for W0-001 and Google Workspace.

Inventories all access paths for a tool/platform package with their
declaration status, maturity percent, gaps, and blockers.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .full_path_maturity import PathDeclarationStatus


@dataclass
class AdapterPathInventoryItem:
    package_id: str = ""
    path_id: str = ""
    path_name: str = ""
    path_type: str = ""
    declaration_status: PathDeclarationStatus = PathDeclarationStatus.FUTURE_CANDIDATE
    capability: str = ""
    auth_method: str = ""
    current_status: str = ""
    target_maturity_percent: float = 100.0
    current_maturity_percent: float = 0.0
    tool_mastery_pack: str = ""
    governance_policy: str = ""
    tests_present: bool = False
    contract_mapping_present: bool = False
    blockers: list[str] = field(default_factory=list)
    gaps_to_100: list[str] = field(default_factory=list)
    hardening_plan_exists: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "path_id": self.path_id,
            "path_name": self.path_name,
            "path_type": self.path_type,
            "declaration_status": self.declaration_status.value,
            "capability": self.capability,
            "auth_method": self.auth_method,
            "current_status": self.current_status,
            "target_maturity_percent": self.target_maturity_percent,
            "current_maturity_percent": self.current_maturity_percent,
            "tool_mastery_pack": self.tool_mastery_pack,
            "governance_policy": self.governance_policy,
            "tests_present": self.tests_present,
            "contract_mapping_present": self.contract_mapping_present,
            "blockers": self.blockers,
            "gaps_to_100": self.gaps_to_100,
            "hardening_plan_exists": self.hardening_plan_exists,
        }


def _gws_path(
    path_id: str,
    path_name: str,
    path_type: str,
    declaration: PathDeclarationStatus,
    capability: str,
    auth: str,
    status: str,
    mastery: str,
    maturity_pct: float,
    gaps: list[str],
    blockers: list[str] | None = None,
) -> AdapterPathInventoryItem:
    return AdapterPathInventoryItem(
        package_id="google_workspace",
        path_id=path_id,
        path_name=path_name,
        path_type=path_type,
        declaration_status=declaration,
        capability=capability,
        auth_method=auth,
        current_status=status,
        target_maturity_percent=100.0,
        current_maturity_percent=maturity_pct,
        tool_mastery_pack=mastery,
        gaps_to_100=gaps,
        blockers=blockers or [],
    )


def inventory_google_workspace_paths() -> list[AdapterPathInventoryItem]:
    D = PathDeclarationStatus.DECLARED
    C = PathDeclarationStatus.FUTURE_CANDIDATE
    B = PathDeclarationStatus.BLOCKED_DEPENDENCY
    R = PathDeclarationStatus.REQUIRES_APPROVAL
    E = PathDeclarationStatus.EXCLUDED_FROM_PACKAGE

    return [
        _gws_path(
            "gws_api_tab_aware", "API tab-aware extractor", "api",
            D, "tab_aware_extraction", "oauth_user_consent",
            "complete", "google_docs_mastery_pack", 14.3,
            [
                "missing formal adapter package",
                "missing governance policy",
                "missing no-secret policy",
                "missing contract mapping",
                "missing validation tests",
                "missing auth profile formalization",
            ],
        ),
        _gws_path(
            "gws_sdk_tab_aware", "SDK tab-aware extractor", "sdk",
            C, "tab_aware_extraction", "oauth_user_consent",
            "not_implemented", "", 0.0,
            ["not implemented", "no mastery pack", "no tests", "no governance"],
        ),
        _gws_path(
            "gws_cli_wrapper", "CLI interface wrapper", "cli",
            E, "tab_aware_extraction", "oauth_cache",
            "complete", "", 0.0,
            ["wraps API — not independent", "excluded from package"],
        ),
        _gws_path(
            "gws_cli_direct", "CLI direct protocol", "cli",
            C, "tab_aware_extraction", "oauth_cache",
            "not_implemented", "", 0.0,
            ["not implemented", "no mastery", "no tests"],
        ),
        _gws_path(
            "gws_cli_vendor", "CLI vendor/native", "cli",
            C, "tab_aware_extraction", "varies",
            "unknown", "", 0.0,
            ["unknown", "must prove tab support"],
        ),
        _gws_path(
            "gws_mcp_wrapper", "MCP interface wrapper", "mcp",
            E, "tab_aware_extraction", "varies",
            "not_implemented", "", 0.0,
            ["not independent", "excluded"],
        ),
        _gws_path(
            "gws_mcp_api_connector", "MCP API connector", "mcp",
            C, "tab_aware_extraction", "oauth_user_consent",
            "not_implemented", "", 0.0,
            ["not implemented", "must prove tab support"],
        ),
        _gws_path(
            "gws_mcp_vendor_wrapper", "MCP vendor/tool wrapper", "mcp",
            C, "tab_aware_extraction", "varies",
            "unknown", "", 0.0,
            ["unknown", "must prove all-tabs support"],
        ),
        _gws_path(
            "gws_mcp_local_file", "MCP local file connector", "mcp",
            C, "file_extraction", "local_machine_identity",
            "not_implemented", "", 0.0,
            ["not implemented", "requires export policy"],
        ),
        _gws_path(
            "gws_mcp_cu_controller", "MCP computer-use controller", "mcp",
            C, "tab_aware_extraction", "browser_session_profile",
            "not_implemented", "", 0.0,
            ["not implemented", "maps to CU requirements"],
        ),
        _gws_path(
            "gws_cu_native", "Native Computer Use", "computer_use",
            D, "tab_aware_extraction", "browser_session_profile",
            "partial", "google_docs_mastery_pack", 0.0,
            [
                "partial implementation",
                "foreground ownership blocks extraction",
                "missing tab detection",
                "missing tab navigation",
                "missing body extraction",
                "missing scrolling/end detection",
                "missing per-tab provenance",
                "missing parity validation",
                "missing governance",
                "missing tests",
            ],
            ["foreground ownership blocks content extraction"],
        ),
        _gws_path(
            "gws_browser_automation", "Browser automation", "browser_automation",
            R, "tab_aware_extraction", "browser_session_profile",
            "blocked", "", 0.0,
            ["blocked", "not approved"],
            ["requires separate approval"],
        ),
        _gws_path(
            "gws_browser_extension", "Browser extension", "browser_extension",
            C, "tab_aware_extraction", "browser_session_profile",
            "not_implemented", "", 0.0,
            ["not implemented", "future candidate"],
        ),
        _gws_path(
            "gws_local_export", "Local export/archive parser", "local_export",
            C, "file_extraction", "local_machine_identity",
            "not_implemented", "", 0.0,
            ["not implemented", "requires export approval"],
        ),
        _gws_path(
            "gws_local_sync", "Local sync parser", "local_sync",
            C, "file_extraction", "local_machine_identity",
            "not_implemented", "", 0.0,
            ["not implemented", "requires sync policy"],
        ),
        _gws_path(
            "gws_file_parser", "File parser", "file_parser",
            C, "file_extraction", "local_machine_identity",
            "not_implemented", "", 0.0,
            ["not implemented"],
        ),
    ]


def inventory_claude_code_paths() -> list[AdapterPathInventoryItem]:
    return [
        AdapterPathInventoryItem(
            package_id="claude_code",
            path_id="cc_cli",
            path_name="Claude Code CLI",
            path_type="cli",
            declaration_status=PathDeclarationStatus.DECLARED,
            capability="code_doc_test_orchestration",
            auth_method="anthropic_api_key",
            current_status="complete",
            current_maturity_percent=14.3,
            tool_mastery_pack="claude_code_mastery_pack",
            gaps_to_100=[
                "missing formal adapter package",
                "missing governance policy",
                "missing no-secret policy",
                "missing contract mapping",
                "missing validation tests",
                "missing auth profile formalization",
            ],
        ),
    ]


def inventory_w0_001_operational_tools() -> list[AdapterPathInventoryItem]:
    tools = [
        ("shell_bash", "Shell/Bash", "cli", "local_command_execution", "local_identity", "complete"),
        ("python", "Python runtime", "runtime", "validation_test_execution", "local_identity", "complete"),
        ("pytest", "pytest framework", "runtime", "test_execution", "local_identity", "complete"),
        ("git", "Git VCS", "cli", "version_control", "ssh_key", "complete"),
        ("tmux", "tmux session manager", "cli", "session_management", "local_identity", "complete"),
        ("vps_runtime", "VPS/WSL runtime", "runtime", "execution_environment", "ssh_key", "complete"),
    ]
    items: list[AdapterPathInventoryItem] = []
    for tool_id, name, ptype, cap, auth, status in tools:
        items.append(
            AdapterPathInventoryItem(
                package_id=tool_id,
                path_id=f"{tool_id}_primary",
                path_name=name,
                path_type=ptype,
                declaration_status=PathDeclarationStatus.DECLARED,
                capability=cap,
                auth_method=auth,
                current_status=status,
                current_maturity_percent=0.0,
                gaps_to_100=[
                    "missing formal adapter package",
                    "missing tool mastery formalization",
                    "missing governance policy",
                    "missing no-secret policy",
                    "missing contract mapping",
                    "missing validation tests",
                ],
            )
        )
    return items


def classify_declared_vs_candidate_paths(
    items: list[AdapterPathInventoryItem],
) -> tuple[list[AdapterPathInventoryItem], list[AdapterPathInventoryItem]]:
    declared = [i for i in items if i.declaration_status == PathDeclarationStatus.DECLARED]
    candidates = [i for i in items if i.declaration_status == PathDeclarationStatus.FUTURE_CANDIDATE]
    return declared, candidates


def build_adapter_path_inventory_report(
    items: list[AdapterPathInventoryItem],
) -> dict[str, Any]:
    declared, candidates = classify_declared_vs_candidate_paths(items)
    blocked = [i for i in items if i.declaration_status == PathDeclarationStatus.BLOCKED_DEPENDENCY]
    approval = [i for i in items if i.declaration_status == PathDeclarationStatus.REQUIRES_APPROVAL]
    excluded = [i for i in items if i.declaration_status == PathDeclarationStatus.EXCLUDED_FROM_PACKAGE]

    return {
        "total_paths": len(items),
        "declared_count": len(declared),
        "candidate_count": len(candidates),
        "blocked_count": len(blocked),
        "approval_required_count": len(approval),
        "excluded_count": len(excluded),
        "declared_paths": [i.path_name for i in declared],
        "candidate_paths": [i.path_name for i in candidates],
        "blocked_paths": [i.path_name for i in blocked],
        "approval_required_paths": [i.path_name for i in approval],
        "excluded_paths": [i.path_name for i in excluded],
    }
