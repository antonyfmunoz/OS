"""Tests for Phase 96.2 MCP backend classifier."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate.extraction_backend_contracts import (
    BackendIndependenceLevel,
    ExtractionBackendType,
    ExtractionCoverageStatus,
    MCPSubtype,
    build_google_docs_contract,
)
from eos_ai.substrate.mcp_backend_contracts import MCPToolProfile
from eos_ai.substrate.mcp_backend_classifier import (
    build_mcp_backend_matrix_row,
    classify_mcp_tool,
    evaluate_mcp_against_extraction_contract,
    infer_independence_level,
    infer_mcp_subtype,
    mcp_counts_as_independent_backend,
)


def test_wrapper_classified_as_level_0():
    """MCP wrapping internal extractor is LEVEL_0 and not independent."""
    p = MCPToolProfile(
        tool_name="gdocs-proxy",
        server_name="internal-mcp",
        declared_capabilities=["read_doc"],
        data_access_channel="internal extractor wrapper",
    )
    assert infer_mcp_subtype(p) == MCPSubtype.MCP_AS_INTERFACE
    assert infer_independence_level(p) == BackendIndependenceLevel.LEVEL_0_INTERFACE_WRAPPER
    assert not mcp_counts_as_independent_backend(p)


def test_api_connector_classified_as_level_1():
    """MCP calling Google API directly is LEVEL_1."""
    p = MCPToolProfile(
        tool_name="gdocs-api",
        server_name="google-mcp",
        declared_capabilities=["documents.get"],
        data_access_channel="Google Docs API",
    )
    assert infer_mcp_subtype(p) == MCPSubtype.MCP_API_CONNECTOR
    assert infer_independence_level(p) == (
        BackendIndependenceLevel.LEVEL_1_DIFFERENT_IMPLEMENTATION_SAME_PROVIDER_API
    )
    assert mcp_counts_as_independent_backend(p)


def test_vendor_tool_wrapper_classified_as_level_2():
    """MCP wrapping GAM/rclone/vendor CLI is LEVEL_2."""
    p = MCPToolProfile(
        tool_name="gam-bridge",
        server_name="vendor-mcp",
        declared_capabilities=["list_files", "get_doc"],
        data_access_channel="GAM CLI tool",
    )
    assert infer_mcp_subtype(p) == MCPSubtype.MCP_VENDOR_TOOL_WRAPPER
    assert infer_independence_level(p) == (
        BackendIndependenceLevel.LEVEL_2_DIFFERENT_TOOLCHAIN_SAME_PROVIDER_API
    )
    assert mcp_counts_as_independent_backend(p)


def test_local_file_connector_classified_as_level_3():
    """MCP reading local synced files is LEVEL_3."""
    p = MCPToolProfile(
        tool_name="local-reader",
        server_name="file-mcp",
        declared_capabilities=["read_file"],
        data_access_channel="local export sync",
    )
    assert infer_mcp_subtype(p) == MCPSubtype.MCP_LOCAL_FILE_CONNECTOR
    assert infer_independence_level(p) == (
        BackendIndependenceLevel.LEVEL_3_DIFFERENT_DATA_ACCESS_CHANNEL
    )
    assert mcp_counts_as_independent_backend(p)


def test_computer_use_controller_classified_as_level_4():
    """MCP controlling desktop/browser is LEVEL_4."""
    p = MCPToolProfile(
        tool_name="cu-controller",
        server_name="desktop-mcp",
        declared_capabilities=["click", "type", "scroll"],
        data_access_channel="computer use desktop accessibility",
    )
    assert infer_mcp_subtype(p) == MCPSubtype.MCP_COMPUTER_USE_CONTROLLER
    assert infer_independence_level(p) == BackendIndependenceLevel.LEVEL_4_DIFFERENT_MODALITY
    assert mcp_counts_as_independent_backend(p)


def test_browser_automation_classified_and_blocked():
    """MCP browser automation is classified but blocked unless approved."""
    p = MCPToolProfile(
        tool_name="playwright-bridge",
        server_name="browser-mcp",
        declared_capabilities=["navigate", "click"],
        data_access_channel="playwright CDP",
        can_read_body=True,
        can_read_tabs=True,
        can_read_child_tabs=True,
        can_read_metadata=True,
        can_emit_canonical_records=True,
    )
    classified = classify_mcp_tool(p)
    assert classified.mcp_subtype == MCPSubtype.MCP_BROWSER_AUTOMATION

    contract = build_google_docs_contract("test", ExtractionBackendType.MCP)
    evaluation = evaluate_mcp_against_extraction_contract(classified, contract)
    assert evaluation.parity_status == "BLOCKED_UNLESS_APPROVED"


def test_mcp_cannot_claim_complete_without_full_capabilities():
    """MCP missing tabs/body/provenance cannot be COMPLETE."""
    p = MCPToolProfile(
        tool_name="partial-reader",
        server_name="test-mcp",
        mcp_subtype=MCPSubtype.MCP_API_CONNECTOR,
        can_read_metadata=True,
        can_read_body=False,
        can_read_tabs=False,
        can_read_child_tabs=False,
        can_emit_canonical_records=False,
    )
    contract = build_google_docs_contract("test", ExtractionBackendType.MCP)
    evaluation = evaluate_mcp_against_extraction_contract(p, contract)
    assert evaluation.contract_coverage_status != ExtractionCoverageStatus.COMPLETE


def test_mcp_google_docs_requires_include_tabs_content():
    """MCP API connector for Google Docs must use includeTabsContent=true."""
    p = MCPToolProfile(
        tool_name="gdocs-reader",
        server_name="google-mcp",
        mcp_subtype=MCPSubtype.MCP_API_CONNECTOR,
        declared_capabilities=["documents.get"],
        can_read_metadata=True,
        can_read_body=True,
        can_read_tabs=True,
        can_read_child_tabs=True,
        can_emit_canonical_records=True,
    )
    contract = build_google_docs_contract("test", ExtractionBackendType.MCP)
    evaluation = evaluate_mcp_against_extraction_contract(p, contract)
    assert "includeTabsContent" in evaluation.failure_domain_notes


def test_mcp_and_cli_not_independent_just_because_different_interface():
    """MCP and CLI wrapping same API extractor are both LEVEL_0, not independent."""
    mcp_profile = MCPToolProfile(
        tool_name="same-extractor-mcp",
        server_name="internal",
        data_access_channel="internal extractor wrapper",
    )
    assert infer_mcp_subtype(mcp_profile) == MCPSubtype.MCP_AS_INTERFACE
    assert not mcp_counts_as_independent_backend(mcp_profile)


def test_build_matrix_row_includes_all_fields():
    """build_mcp_backend_matrix_row returns complete row dict."""
    p = MCPToolProfile(
        tool_name="gdocs-api",
        server_name="google-mcp",
        data_access_channel="Google Docs API",
        can_read_metadata=True,
        can_read_body=True,
    )
    row = build_mcp_backend_matrix_row(p)
    assert row["backend_type"] == "mcp"
    assert row["tool_name"] == "gdocs-api"
    assert "mcp_subtype" in row
    assert "independence_level" in row
    assert "is_independent_backend" in row


def test_unknown_subtype_defaults_to_level_0():
    """Unknown MCP tools default to LEVEL_0 (not independent)."""
    p = MCPToolProfile(
        tool_name="mystery",
        server_name="unknown-server",
    )
    assert infer_mcp_subtype(p) == MCPSubtype.MCP_UNKNOWN
    assert infer_independence_level(p) == BackendIndependenceLevel.LEVEL_0_INTERFACE_WRAPPER
    assert not mcp_counts_as_independent_backend(p)


def test_classify_mcp_tool_mutates_profile():
    """classify_mcp_tool fills in subtype and independence level."""
    p = MCPToolProfile(
        tool_name="local-reader",
        server_name="file-mcp",
        data_access_channel="local export sync",
    )
    assert p.mcp_subtype == MCPSubtype.MCP_UNKNOWN
    classified = classify_mcp_tool(p)
    assert classified.mcp_subtype == MCPSubtype.MCP_LOCAL_FILE_CONNECTOR
    assert classified.independence_level == (
        BackendIndependenceLevel.LEVEL_3_DIFFERENT_DATA_ACCESS_CHANNEL
    )


def test_full_capability_mcp_api_connector_evaluates_partial_without_tabs_flag():
    """Even with all capabilities, missing includeTabsContent flag is flagged."""
    p = MCPToolProfile(
        tool_name="full-reader",
        server_name="google-mcp",
        mcp_subtype=MCPSubtype.MCP_API_CONNECTOR,
        declared_capabilities=["documents.get"],
        can_read_metadata=True,
        can_read_body=True,
        can_read_tabs=True,
        can_read_child_tabs=True,
        can_emit_canonical_records=True,
    )
    contract = build_google_docs_contract("test", ExtractionBackendType.MCP)
    ev = evaluate_mcp_against_extraction_contract(p, contract)
    assert ev.contract_coverage_status == ExtractionCoverageStatus.PARTIAL
