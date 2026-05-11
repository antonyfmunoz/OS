"""
Google Docs backend parity matrix for Phase 96.0 + 96.2.

Evaluates API, CLI, MCP, and Computer Use backends against the canonical
Google Docs extraction contract and produces a capability matrix.

Expected current state:
- API: COMPLETE after tab-aware extraction
- CLI: PARTIAL/COMPLETE depending on tab-aware wrapper
- MCP: varies by subtype — must be classified before evaluation
- Computer Use: PARTIAL (tab detection proven, content extraction blocked)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from runtime.transport.extraction_backend_contracts import (
    BackendCapabilityReport,
    BackendIndependenceLevel,
    CanonicalExtractionContract,
    CapabilityDeclaration,
    ExtractionBackendType,
    ExtractionCapability,
    ExtractionCoverageStatus,
    ExtractionFailureReason,
    MCPSubtype,
    build_google_docs_contract,
    evaluate_backend_against_contract,
)


@dataclass
class BackendMatrixEntry:
    """One backend's row in the parity matrix."""

    backend_type: ExtractionBackendType
    capabilities: dict[str, str] = field(default_factory=dict)
    overall_status: str = "UNKNOWN"
    independence_level: str = ""
    mcp_subtype: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "backend_type": self.backend_type.value,
            "capabilities": self.capabilities,
            "overall_status": self.overall_status,
            "notes": self.notes,
        }
        if self.independence_level:
            d["independence_level"] = self.independence_level
        if self.mcp_subtype:
            d["mcp_subtype"] = self.mcp_subtype
        return d


@dataclass
class GoogleDocsParityMatrix:
    """Full parity matrix for Google Docs extraction backends."""

    contract: CanonicalExtractionContract | None = None
    api_entry: BackendMatrixEntry | None = None
    cli_entry: BackendMatrixEntry | None = None
    cu_entry: BackendMatrixEntry | None = None
    mcp_entries: list[BackendMatrixEntry] = field(default_factory=list)
    browser_automation_entry: BackendMatrixEntry | None = None
    local_file_entry: BackendMatrixEntry | None = None
    recommended_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "contract_source_type": self.contract.source_type if self.contract else "",
            "api": self.api_entry.to_dict() if self.api_entry else None,
            "cli": self.cli_entry.to_dict() if self.cli_entry else None,
            "computer_use": self.cu_entry.to_dict() if self.cu_entry else None,
            "mcp_backends": [e.to_dict() for e in self.mcp_entries],
            "browser_automation": (
                self.browser_automation_entry.to_dict() if self.browser_automation_entry else None
            ),
            "local_file": (self.local_file_entry.to_dict() if self.local_file_entry else None),
            "recommended_action": self.recommended_action,
        }
        return d


def mark_api_capabilities(
    tab_aware: bool = True,
) -> list[CapabilityDeclaration]:
    """Declare API backend capabilities for Google Docs."""
    base_status = (
        ExtractionCoverageStatus.COMPLETE if tab_aware else ExtractionCoverageStatus.PARTIAL
    )

    return [
        CapabilityDeclaration(
            capability=ExtractionCapability.SOURCE_INVENTORY,
            status=ExtractionCoverageStatus.COMPLETE,
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.DOCUMENT_METADATA,
            status=ExtractionCoverageStatus.COMPLETE,
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.DOCUMENT_BODY,
            status=ExtractionCoverageStatus.COMPLETE,
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.DOCUMENT_TABS,
            status=base_status,
            notes="" if tab_aware else "requires includeTabsContent=true",
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.CHILD_TABS,
            status=base_status,
            notes="" if tab_aware else "requires recursive traversal",
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.PROVENANCE_CAPTURE,
            status=ExtractionCoverageStatus.COMPLETE,
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.COMPLETENESS_VALIDATION,
            status=ExtractionCoverageStatus.COMPLETE,
        ),
    ]


def mark_cli_capabilities(
    wraps_tab_aware_api: bool = True,
) -> list[CapabilityDeclaration]:
    """Declare CLI backend capabilities for Google Docs."""
    tab_status = (
        ExtractionCoverageStatus.COMPLETE
        if wraps_tab_aware_api
        else ExtractionCoverageStatus.PARTIAL
    )

    return [
        CapabilityDeclaration(
            capability=ExtractionCapability.SOURCE_INVENTORY,
            status=ExtractionCoverageStatus.COMPLETE,
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.DOCUMENT_METADATA,
            status=ExtractionCoverageStatus.COMPLETE,
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.DOCUMENT_BODY,
            status=ExtractionCoverageStatus.COMPLETE,
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.DOCUMENT_TABS,
            status=tab_status,
            notes="wraps API with includeTabsContent"
            if wraps_tab_aware_api
            else "CLI must pass tab flag",
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.CHILD_TABS,
            status=tab_status,
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.PROVENANCE_CAPTURE,
            status=ExtractionCoverageStatus.COMPLETE,
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.COMPLETENESS_VALIDATION,
            status=ExtractionCoverageStatus.COMPLETE,
        ),
    ]


def mark_computer_use_capabilities() -> list[CapabilityDeclaration]:
    """Declare Computer Use backend capabilities for Google Docs (current state)."""
    return [
        CapabilityDeclaration(
            capability=ExtractionCapability.SOURCE_INVENTORY,
            status=ExtractionCoverageStatus.COMPLETE,
            notes="Drive file list via accessibility tree proven",
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.DOCUMENT_METADATA,
            status=ExtractionCoverageStatus.PARTIAL,
            notes="title and tab names detected; modified/owner not yet extracted",
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.DOCUMENT_BODY,
            status=ExtractionCoverageStatus.BLOCKED,
            failure_reason=ExtractionFailureReason.FOREGROUND_OWNERSHIP_BLOCKED,
            notes="SetForegroundWindow fails; clipboard capture requires foreground",
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.DOCUMENT_TABS,
            status=ExtractionCoverageStatus.PARTIAL,
            failure_reason=ExtractionFailureReason.TAB_NAVIGATION_FAILED,
            notes="tab DETECTION proven (8/8); tab NAVIGATION not yet proven",
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.CHILD_TABS,
            status=ExtractionCoverageStatus.UNKNOWN,
            notes="not tested — depends on tab navigation working first",
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.PAGE_SCROLLING,
            status=ExtractionCoverageStatus.BLOCKED,
            failure_reason=ExtractionFailureReason.FOREGROUND_OWNERSHIP_BLOCKED,
            notes="SendKeys not delivered without foreground",
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.VISIBLE_UI_EXTRACTION,
            status=ExtractionCoverageStatus.PARTIAL,
            notes="accessibility tree readable; canvas content not exposed",
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.CLIPBOARD_CAPTURE,
            status=ExtractionCoverageStatus.BLOCKED,
            failure_reason=ExtractionFailureReason.CLIPBOARD_BLOCKED,
            notes="Ctrl+A/C requires foreground ownership",
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.ACCESSIBILITY_TREE_EXTRACTION,
            status=ExtractionCoverageStatus.COMPLETE,
            notes="proven for Drive inventory and Doc tab detection",
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.PROVENANCE_CAPTURE,
            status=ExtractionCoverageStatus.COMPLETE,
        ),
        CapabilityDeclaration(
            capability=ExtractionCapability.COMPLETENESS_VALIDATION,
            status=ExtractionCoverageStatus.PARTIAL,
            notes="can validate tab count but not content completeness",
        ),
    ]


def build_google_docs_backend_matrix(
    file_id: str = "generic",
    api_tab_aware: bool = True,
    cli_wraps_api: bool = True,
) -> GoogleDocsParityMatrix:
    """Build the full backend parity matrix for Google Docs."""
    contract = build_google_docs_contract(file_id, ExtractionBackendType.API)

    api_caps = mark_api_capabilities(tab_aware=api_tab_aware)
    cli_caps = mark_cli_capabilities(wraps_tab_aware_api=cli_wraps_api)
    cu_caps = mark_computer_use_capabilities()

    api_report = evaluate_backend_against_contract(
        contract, api_caps, actual_backend_type=ExtractionBackendType.API
    )
    cli_report = evaluate_backend_against_contract(
        contract, cli_caps, actual_backend_type=ExtractionBackendType.CLI
    )

    cu_contract = build_google_docs_contract(file_id, ExtractionBackendType.COMPUTER_USE)
    cu_report = evaluate_backend_against_contract(
        cu_contract, cu_caps, actual_backend_type=ExtractionBackendType.COMPUTER_USE
    )

    api_entry = _report_to_matrix_entry(api_report)
    cli_entry = _report_to_matrix_entry(cli_report)
    cu_entry = _report_to_matrix_entry(cu_report)

    mcp_entries = _build_mcp_matrix_entries()
    browser_entry = _build_browser_automation_entry()
    local_file_entry = _build_local_file_entry()

    recommendation = recommend_next_backend_hardening_step(api_report, cli_report, cu_report)

    return GoogleDocsParityMatrix(
        contract=contract,
        api_entry=api_entry,
        cli_entry=cli_entry,
        cu_entry=cu_entry,
        mcp_entries=mcp_entries,
        browser_automation_entry=browser_entry,
        local_file_entry=local_file_entry,
        recommended_action=recommendation,
    )


def _report_to_matrix_entry(report: BackendCapabilityReport) -> BackendMatrixEntry:
    """Convert a capability report to a matrix entry."""
    caps: dict[str, str] = {}
    for cap in report.capabilities:
        caps[cap.capability.value] = cap.status.value

    return BackendMatrixEntry(
        backend_type=report.backend_type,
        capabilities=caps,
        overall_status=report.overall_status.value,
    )


def _build_mcp_matrix_entries() -> list[BackendMatrixEntry]:
    """Build MCP matrix entries for all known MCP subtypes relevant to Google Docs."""
    entries: list[BackendMatrixEntry] = []

    entries.append(
        BackendMatrixEntry(
            backend_type=ExtractionBackendType.MCP,
            overall_status="NOT_IMPLEMENTED",
            independence_level=BackendIndependenceLevel.LEVEL_0_INTERFACE_WRAPPER.value,
            mcp_subtype=MCPSubtype.MCP_AS_INTERFACE.value,
            notes="Wrapper around internal API extractor — not independent fallback",
        )
    )

    entries.append(
        BackendMatrixEntry(
            backend_type=ExtractionBackendType.MCP,
            overall_status="NOT_IMPLEMENTED",
            independence_level=(
                BackendIndependenceLevel.LEVEL_1_DIFFERENT_IMPLEMENTATION_SAME_PROVIDER_API.value
            ),
            mcp_subtype=MCPSubtype.MCP_API_CONNECTOR.value,
            notes="Must use includeTabsContent=true; still depends on Google API availability",
        )
    )

    entries.append(
        BackendMatrixEntry(
            backend_type=ExtractionBackendType.MCP,
            overall_status="UNKNOWN",
            independence_level=(
                BackendIndependenceLevel.LEVEL_2_DIFFERENT_TOOLCHAIN_SAME_PROVIDER_API.value
            ),
            mcp_subtype=MCPSubtype.MCP_VENDOR_TOOL_WRAPPER.value,
            notes="Would wrap GAM/rclone/etc. — unknown if all-tabs support exists",
        )
    )

    entries.append(
        BackendMatrixEntry(
            backend_type=ExtractionBackendType.MCP,
            overall_status="NOT_APPROVED",
            independence_level=BackendIndependenceLevel.LEVEL_3_DIFFERENT_DATA_ACCESS_CHANNEL.value,
            mcp_subtype=MCPSubtype.MCP_LOCAL_FILE_CONNECTOR.value,
            notes="Requires export/local-file/sync policy approval",
        )
    )

    entries.append(
        BackendMatrixEntry(
            backend_type=ExtractionBackendType.MCP,
            overall_status="MAPS_TO_CU",
            independence_level=BackendIndependenceLevel.LEVEL_4_DIFFERENT_MODALITY.value,
            mcp_subtype=MCPSubtype.MCP_COMPUTER_USE_CONTROLLER.value,
            notes="Maps to Computer Use backend — same capabilities and blockers",
        )
    )

    return entries


def _build_browser_automation_entry() -> BackendMatrixEntry:
    """Build the browser automation matrix entry (blocked unless approved)."""
    return BackendMatrixEntry(
        backend_type=ExtractionBackendType.BROWSER_AUTOMATION,
        overall_status="BLOCKED",
        notes="Blocked unless separately approved — Playwright/CDP/Selenium",
    )


def _build_local_file_entry() -> BackendMatrixEntry:
    """Build the local file/export parser matrix entry."""
    return BackendMatrixEntry(
        backend_type=ExtractionBackendType.LOCAL_FILE,
        overall_status="NOT_APPROVED",
        independence_level=BackendIndependenceLevel.LEVEL_3_DIFFERENT_DATA_ACCESS_CHANNEL.value,
        notes="Requires export/download/sync approval — not yet approved",
    )


def recommend_next_backend_hardening_step(
    api_report: BackendCapabilityReport,
    cli_report: BackendCapabilityReport,
    cu_report: BackendCapabilityReport,
) -> str:
    """Recommend the next step to improve backend parity."""
    if api_report.overall_status != ExtractionCoverageStatus.COMPLETE:
        return "RUN_TAB_AWARE_API_EXTRACTION"

    if cli_report.overall_status != ExtractionCoverageStatus.COMPLETE:
        return "WRAP_CLI_WITH_TAB_AWARE_API"

    if cu_report.overall_status == ExtractionCoverageStatus.COMPLETE:
        return "ALL_BACKENDS_AT_PARITY"

    if ExtractionCapability.DOCUMENT_BODY in cu_report.blocked_capabilities:
        return "HARDEN_CU_DOCUMENT_READER_FIX_FOREGROUND"

    if ExtractionCapability.DOCUMENT_TABS in cu_report.missing_capabilities:
        return "HARDEN_CU_TAB_NAVIGATION"

    return "HARDEN_CU_DOCUMENT_READER_GENERAL"
