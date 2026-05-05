"""
Extraction backend parity contracts for Phase 96.0 + 96.2.

Defines the canonical contract that ALL extraction backends (API, CLI,
MCP, Computer Use, Browser Automation, Local File) must satisfy.
No backend may claim COMPLETE unless it meets every coverage requirement.

Same target outcome. Different mechanisms. Same output schema.
Same completeness contract. Parity validation between backends.

Phase 96.2 addition: MCP is a protocol/adapter layer, not automatically
an independent backend. MCP tools must be classified by their underlying
capability and failure domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExtractionBackendType(str, Enum):
    API = "api"
    CLI = "cli"
    MCP = "mcp"
    COMPUTER_USE = "computer_use"
    BROWSER_AUTOMATION = "browser_automation"
    LOCAL_FILE = "local_file"
    MANUAL = "manual"
    HYBRID = "hybrid"


class MCPSubtype(str, Enum):
    MCP_AS_INTERFACE = "mcp_as_interface"
    MCP_API_CONNECTOR = "mcp_api_connector"
    MCP_VENDOR_TOOL_WRAPPER = "mcp_vendor_tool_wrapper"
    MCP_LOCAL_FILE_CONNECTOR = "mcp_local_file_connector"
    MCP_COMPUTER_USE_CONTROLLER = "mcp_computer_use_controller"
    MCP_BROWSER_AUTOMATION = "mcp_browser_automation"
    MCP_NATIVE_SOURCE_CONNECTOR = "mcp_native_source_connector"
    MCP_UNKNOWN = "mcp_unknown"


class BackendIndependenceLevel(str, Enum):
    LEVEL_0_INTERFACE_WRAPPER = "level_0_interface_wrapper"
    LEVEL_1_DIFFERENT_IMPLEMENTATION_SAME_PROVIDER_API = "level_1_different_impl_same_api"
    LEVEL_2_DIFFERENT_TOOLCHAIN_SAME_PROVIDER_API = "level_2_different_toolchain_same_api"
    LEVEL_3_DIFFERENT_DATA_ACCESS_CHANNEL = "level_3_different_data_channel"
    LEVEL_4_DIFFERENT_MODALITY = "level_4_different_modality"
    LEVEL_5_HUMAN_ASSISTED = "level_5_human_assisted"


def independence_counts_as_fallback(level: BackendIndependenceLevel) -> bool:
    """LEVEL_0 does not count as an independent fallback."""
    return level != BackendIndependenceLevel.LEVEL_0_INTERFACE_WRAPPER


class ExtractionCapability(str, Enum):
    SOURCE_INVENTORY = "source_inventory"
    DOCUMENT_METADATA = "document_metadata"
    DOCUMENT_BODY = "document_body"
    DOCUMENT_TABS = "document_tabs"
    CHILD_TABS = "child_tabs"
    PAGE_SCROLLING = "page_scrolling"
    VISIBLE_UI_EXTRACTION = "visible_ui_extraction"
    CLIPBOARD_CAPTURE = "clipboard_capture"
    ACCESSIBILITY_TREE_EXTRACTION = "accessibility_tree_extraction"
    PROVENANCE_CAPTURE = "provenance_capture"
    COMPLETENESS_VALIDATION = "completeness_validation"


class ExtractionCoverageStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class ExtractionFailureReason(str, Enum):
    AUTH_REQUIRED = "auth_required"
    ACCESS_DENIED = "access_denied"
    BACKEND_LIMITATION = "backend_limitation"
    UI_INACCESSIBLE = "ui_inaccessible"
    FOREGROUND_OWNERSHIP_BLOCKED = "foreground_ownership_blocked"
    TAB_NAVIGATION_FAILED = "tab_navigation_failed"
    SCROLL_EXTRACTION_FAILED = "scroll_extraction_failed"
    CLIPBOARD_BLOCKED = "clipboard_blocked"
    CONTENT_NOT_VISIBLE = "content_not_visible"
    USER_APPROVAL_REQUIRED = "user_approval_required"


@dataclass
class CapabilityDeclaration:
    """A single capability declared by a backend."""

    capability: ExtractionCapability
    status: ExtractionCoverageStatus
    failure_reason: ExtractionFailureReason | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "capability": self.capability.value,
            "status": self.status.value,
        }
        if self.failure_reason:
            d["failure_reason"] = self.failure_reason.value
        if self.notes:
            d["notes"] = self.notes
        return d


@dataclass
class CanonicalExtractionContract:
    """The contract every extraction backend must satisfy."""

    source_id: str
    source_type: str
    backend_type: ExtractionBackendType
    required_capabilities: list[ExtractionCapability] = field(default_factory=list)
    required_outputs: list[str] = field(default_factory=list)
    coverage_requirements: dict[str, str] = field(default_factory=dict)
    blocked_actions: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    failure_reporting_rules: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "backend_type": self.backend_type.value,
            "required_capabilities": [c.value for c in self.required_capabilities],
            "required_outputs": self.required_outputs,
            "coverage_requirements": self.coverage_requirements,
            "blocked_actions": self.blocked_actions,
            "success_criteria": self.success_criteria,
            "failure_reporting_rules": self.failure_reporting_rules,
        }


@dataclass
class BackendCapabilityReport:
    """Full capability report for a single backend."""

    backend_type: ExtractionBackendType
    capabilities: list[CapabilityDeclaration] = field(default_factory=list)
    overall_status: ExtractionCoverageStatus = ExtractionCoverageStatus.UNKNOWN
    missing_capabilities: list[ExtractionCapability] = field(default_factory=list)
    blocked_capabilities: list[ExtractionCapability] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend_type": self.backend_type.value,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "overall_status": self.overall_status.value,
            "missing_capabilities": [c.value for c in self.missing_capabilities],
            "blocked_capabilities": [c.value for c in self.blocked_capabilities],
        }


def build_google_docs_contract(
    file_id: str,
    backend_type: ExtractionBackendType,
) -> CanonicalExtractionContract:
    """Build the canonical extraction contract for a Google Doc."""
    return CanonicalExtractionContract(
        source_id=file_id,
        source_type="google_doc",
        backend_type=backend_type,
        required_capabilities=[
            ExtractionCapability.SOURCE_INVENTORY,
            ExtractionCapability.DOCUMENT_METADATA,
            ExtractionCapability.DOCUMENT_BODY,
            ExtractionCapability.DOCUMENT_TABS,
            ExtractionCapability.CHILD_TABS,
            ExtractionCapability.PROVENANCE_CAPTURE,
            ExtractionCapability.COMPLETENESS_VALIDATION,
        ],
        required_outputs=[
            "document_source_record",
            "tab_source_records",
            "provenance_record",
            "coverage_status",
        ],
        coverage_requirements={
            "all_documents_in_scope": "required",
            "all_document_tabs": "required",
            "all_child_tabs": "required",
            "all_pages_body_content": "required",
            "empty_tabs_marked": "required",
            "inaccessible_items_with_reason": "required",
            "provenance_preserved": "required",
        },
        blocked_actions=[
            "edit_document",
            "delete_document",
            "share_document",
            "download_document",
            "switch_account",
            "open_gmail",
            "capture_credentials",
            "store_screenshots",
        ],
        success_criteria=[
            "all_tabs_discovered",
            "all_tab_content_extracted",
            "empty_tabs_identified",
            "backend_type_recorded",
            "provenance_complete",
            "output_matches_canonical_schema",
        ],
        failure_reporting_rules=[
            "partial_backend_must_not_claim_complete",
            "blocked_capabilities_must_specify_reason",
            "missing_tabs_must_be_enumerated",
            "missing_content_must_report_word_count_gap",
            "failure_reason_must_use_ExtractionFailureReason_enum",
        ],
    )


def evaluate_backend_against_contract(
    contract: CanonicalExtractionContract,
    capabilities: list[CapabilityDeclaration],
    actual_backend_type: ExtractionBackendType | None = None,
) -> BackendCapabilityReport:
    """Evaluate whether a backend's capabilities satisfy the contract."""
    cap_map = {c.capability: c for c in capabilities}

    missing: list[ExtractionCapability] = []
    blocked: list[ExtractionCapability] = []

    for required in contract.required_capabilities:
        if required not in cap_map:
            missing.append(required)
        elif cap_map[required].status == ExtractionCoverageStatus.BLOCKED:
            blocked.append(required)
        elif cap_map[required].status == ExtractionCoverageStatus.FAILED:
            missing.append(required)
        elif cap_map[required].status == ExtractionCoverageStatus.PARTIAL:
            missing.append(required)

    if not missing and not blocked:
        overall = ExtractionCoverageStatus.COMPLETE
    elif blocked and not missing:
        overall = ExtractionCoverageStatus.BLOCKED
    elif missing:
        has_any_complete = any(c.status == ExtractionCoverageStatus.COMPLETE for c in capabilities)
        overall = (
            ExtractionCoverageStatus.PARTIAL
            if has_any_complete
            else ExtractionCoverageStatus.FAILED
        )
    else:
        overall = ExtractionCoverageStatus.UNKNOWN

    backend = actual_backend_type if actual_backend_type else contract.backend_type

    return BackendCapabilityReport(
        backend_type=backend,
        capabilities=capabilities,
        overall_status=overall,
        missing_capabilities=missing,
        blocked_capabilities=blocked,
    )
