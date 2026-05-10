"""
MCP backend classifier for Phase 96.2.

Classifies MCP tools by their underlying capability and failure domain,
determines independence level, and evaluates against the canonical
extraction contract.

Core rule: MCP counts as an independent backend only when it provides
distinct implementation, access channel, runtime, toolchain, or
failure-domain value. A wrapper around the same internal extractor
is LEVEL_0 and does NOT count.
"""

from __future__ import annotations

from typing import Any

from eos_ai.substrate.extraction_backend_contracts import (
    BackendIndependenceLevel,
    CanonicalExtractionContract,
    ExtractionBackendType,
    ExtractionCoverageStatus,
    MCPSubtype,
    independence_counts_as_fallback,
)
from eos_ai.substrate.mcp_backend_contracts import (
    MCPBackendEvaluation,
    MCPToolProfile,
)

_SUBTYPE_TO_INDEPENDENCE: dict[MCPSubtype, BackendIndependenceLevel] = {
    MCPSubtype.MCP_AS_INTERFACE: BackendIndependenceLevel.LEVEL_0_INTERFACE_WRAPPER,
    MCPSubtype.MCP_API_CONNECTOR: (
        BackendIndependenceLevel.LEVEL_1_DIFFERENT_IMPLEMENTATION_SAME_PROVIDER_API
    ),
    MCPSubtype.MCP_VENDOR_TOOL_WRAPPER: (
        BackendIndependenceLevel.LEVEL_2_DIFFERENT_TOOLCHAIN_SAME_PROVIDER_API
    ),
    MCPSubtype.MCP_LOCAL_FILE_CONNECTOR: (
        BackendIndependenceLevel.LEVEL_3_DIFFERENT_DATA_ACCESS_CHANNEL
    ),
    MCPSubtype.MCP_COMPUTER_USE_CONTROLLER: (BackendIndependenceLevel.LEVEL_4_DIFFERENT_MODALITY),
    MCPSubtype.MCP_BROWSER_AUTOMATION: (
        BackendIndependenceLevel.LEVEL_1_DIFFERENT_IMPLEMENTATION_SAME_PROVIDER_API
    ),
    MCPSubtype.MCP_NATIVE_SOURCE_CONNECTOR: (
        BackendIndependenceLevel.LEVEL_3_DIFFERENT_DATA_ACCESS_CHANNEL
    ),
    MCPSubtype.MCP_UNKNOWN: BackendIndependenceLevel.LEVEL_0_INTERFACE_WRAPPER,
}

_KEYWORD_HINTS: list[tuple[list[str], MCPSubtype]] = [
    (["internal", "extractor", "wrapper", "proxy"], MCPSubtype.MCP_AS_INTERFACE),
    (["google api", "docs api", "drive api", "official api"], MCPSubtype.MCP_API_CONNECTOR),
    (["gam", "rclone", "vendor", "cli tool"], MCPSubtype.MCP_VENDOR_TOOL_WRAPPER),
    (["local", "export", "sync", "archive", "file"], MCPSubtype.MCP_LOCAL_FILE_CONNECTOR),
    (
        ["computer use", "desktop", "accessibility", "mouse", "keyboard"],
        MCPSubtype.MCP_COMPUTER_USE_CONTROLLER,
    ),
    (
        ["playwright", "cdp", "selenium", "browser automation", "puppeteer"],
        MCPSubtype.MCP_BROWSER_AUTOMATION,
    ),
    (["native connector", "source connector"], MCPSubtype.MCP_NATIVE_SOURCE_CONNECTOR),
]


def infer_mcp_subtype(profile: MCPToolProfile) -> MCPSubtype:
    """Infer MCP subtype from profile capabilities and notes."""
    if profile.mcp_subtype != MCPSubtype.MCP_UNKNOWN:
        return profile.mcp_subtype

    searchable = " ".join(
        [
            profile.data_access_channel.lower(),
            profile.notes.lower(),
            " ".join(c.lower() for c in profile.declared_capabilities),
        ]
    )

    for keywords, subtype in _KEYWORD_HINTS:
        if any(kw in searchable for kw in keywords):
            return subtype

    return MCPSubtype.MCP_UNKNOWN


def infer_independence_level(profile: MCPToolProfile) -> BackendIndependenceLevel:
    """Infer independence level from MCP subtype."""
    subtype = infer_mcp_subtype(profile)
    return _SUBTYPE_TO_INDEPENDENCE.get(subtype, BackendIndependenceLevel.LEVEL_0_INTERFACE_WRAPPER)


def classify_mcp_tool(profile: MCPToolProfile) -> MCPToolProfile:
    """Classify an MCP tool by inferring subtype and independence level."""
    profile.mcp_subtype = infer_mcp_subtype(profile)
    profile.independence_level = infer_independence_level(profile)
    return profile


def evaluate_mcp_against_extraction_contract(
    profile: MCPToolProfile,
    contract: CanonicalExtractionContract,
) -> MCPBackendEvaluation:
    """Evaluate an MCP tool against the canonical extraction contract."""
    issues: list[str] = []

    if not profile.can_read_metadata:
        issues.append("cannot read metadata")
    if not profile.can_read_body:
        issues.append("cannot read body content")
    if not profile.can_read_tabs:
        issues.append("cannot read tabs")
    if not profile.can_read_child_tabs:
        issues.append("cannot read child tabs recursively")
    if not profile.can_emit_canonical_records:
        issues.append("cannot emit canonical source records")

    if contract.source_type == "google_doc":
        caps_text = " ".join(profile.declared_capabilities).lower()
        if profile.can_read_tabs and "includetabscontent" not in caps_text:
            if profile.mcp_subtype == MCPSubtype.MCP_API_CONNECTOR:
                issues.append("must use includeTabsContent=true or equivalent")

    if not issues:
        coverage = ExtractionCoverageStatus.COMPLETE
    elif len(issues) <= 2 and profile.can_read_body:
        coverage = ExtractionCoverageStatus.PARTIAL
    else:
        coverage = ExtractionCoverageStatus.FAILED

    is_independent = mcp_counts_as_independent_backend(profile)
    independence_value = f"{profile.independence_level.value} — {'independent' if is_independent else 'NOT independent'}"

    if profile.mcp_subtype == MCPSubtype.MCP_BROWSER_AUTOMATION:
        parity_status = "BLOCKED_UNLESS_APPROVED"
    elif coverage == ExtractionCoverageStatus.COMPLETE:
        parity_status = "AT_PARITY"
    elif coverage == ExtractionCoverageStatus.PARTIAL:
        parity_status = "PARTIAL_NEEDS_WORK"
    else:
        parity_status = "NOT_AT_PARITY"

    if profile.mcp_subtype == MCPSubtype.MCP_AS_INTERFACE:
        recommended = "Use as convenience interface only, not as fallback"
    elif profile.mcp_subtype == MCPSubtype.MCP_BROWSER_AUTOMATION:
        recommended = "Blocked unless separately approved"
    elif coverage == ExtractionCoverageStatus.COMPLETE and is_independent:
        recommended = "Valid independent backend — register in parity matrix"
    elif coverage == ExtractionCoverageStatus.PARTIAL:
        recommended = f"Harden to close gaps: {', '.join(issues)}"
    else:
        recommended = "Not ready for use — evaluate capabilities first"

    failure_notes = "; ".join(issues) if issues else "No gaps detected"

    return MCPBackendEvaluation(
        tool_profile=profile,
        contract_coverage_status=coverage,
        independence_value=independence_value,
        parity_status=parity_status,
        recommended_use=recommended,
        failure_domain_notes=failure_notes,
    )


def mcp_counts_as_independent_backend(profile: MCPToolProfile) -> bool:
    """Determine if an MCP tool counts as an independent backend."""
    level = infer_independence_level(profile)
    return independence_counts_as_fallback(level)


def build_mcp_backend_matrix_row(profile: MCPToolProfile) -> dict[str, Any]:
    """Build a matrix row for an MCP tool."""
    classified = classify_mcp_tool(profile)
    return {
        "backend_type": ExtractionBackendType.MCP.value,
        "tool_name": classified.tool_name,
        "server_name": classified.server_name,
        "mcp_subtype": classified.mcp_subtype.value,
        "independence_level": classified.independence_level.value,
        "is_independent_backend": mcp_counts_as_independent_backend(classified),
        "can_read_metadata": classified.can_read_metadata,
        "can_read_body": classified.can_read_body,
        "can_read_tabs": classified.can_read_tabs,
        "can_read_child_tabs": classified.can_read_child_tabs,
        "can_emit_canonical_records": classified.can_emit_canonical_records,
        "notes": classified.notes,
    }
