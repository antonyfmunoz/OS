"""Tests for Phase 96.2 MCP backend contracts."""

import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.extraction_backend_contracts import (
    BackendIndependenceLevel,
    ExtractionBackendType,
    ExtractionCoverageStatus,
    MCPSubtype,
    independence_counts_as_fallback,
)
from eos_ai.substrate.mcp_backend_contracts import (
    MCPBackendEvaluation,
    MCPToolProfile,
)


def test_mcp_tool_profile_defaults():
    """MCPToolProfile defaults to MCP_UNKNOWN subtype and LEVEL_0."""
    p = MCPToolProfile(tool_name="test", server_name="test-server")
    assert p.mcp_subtype == MCPSubtype.MCP_UNKNOWN
    assert p.independence_level == BackendIndependenceLevel.LEVEL_0_INTERFACE_WRAPPER
    assert p.inferred_backend_type == ExtractionBackendType.MCP


def test_mcp_tool_profile_serialization():
    """MCPToolProfile serializes all fields."""
    p = MCPToolProfile(
        tool_name="gdocs-reader",
        server_name="google-mcp",
        mcp_subtype=MCPSubtype.MCP_API_CONNECTOR,
        independence_level=BackendIndependenceLevel.LEVEL_1_DIFFERENT_IMPLEMENTATION_SAME_PROVIDER_API,
        can_read_tabs=True,
        can_read_body=True,
    )
    d = p.to_dict()
    assert d["tool_name"] == "gdocs-reader"
    assert d["mcp_subtype"] == "mcp_api_connector"
    assert d["independence_level"] == "level_1_different_impl_same_api"
    assert d["can_read_tabs"] is True
    assert d["can_read_body"] is True


def test_mcp_evaluation_serialization():
    """MCPBackendEvaluation serializes with nested profile."""
    p = MCPToolProfile(tool_name="test", server_name="srv")
    e = MCPBackendEvaluation(
        tool_profile=p,
        contract_coverage_status=ExtractionCoverageStatus.PARTIAL,
        parity_status="PARTIAL_NEEDS_WORK",
    )
    d = e.to_dict()
    assert d["contract_coverage_status"] == "partial"
    assert d["parity_status"] == "PARTIAL_NEEDS_WORK"
    assert d["tool_profile"]["tool_name"] == "test"


def test_level_0_not_independent_fallback():
    """LEVEL_0 interface wrapper does NOT count as independent fallback."""
    assert not independence_counts_as_fallback(BackendIndependenceLevel.LEVEL_0_INTERFACE_WRAPPER)


def test_level_1_counts_as_independent():
    """LEVEL_1 (different implementation) counts as independent."""
    assert independence_counts_as_fallback(
        BackendIndependenceLevel.LEVEL_1_DIFFERENT_IMPLEMENTATION_SAME_PROVIDER_API
    )


def test_level_2_counts_as_independent():
    """LEVEL_2 (different toolchain) counts as independent."""
    assert independence_counts_as_fallback(
        BackendIndependenceLevel.LEVEL_2_DIFFERENT_TOOLCHAIN_SAME_PROVIDER_API
    )


def test_level_3_counts_as_independent():
    """LEVEL_3 (different data channel) counts as independent."""
    assert independence_counts_as_fallback(
        BackendIndependenceLevel.LEVEL_3_DIFFERENT_DATA_ACCESS_CHANNEL
    )


def test_level_4_counts_as_independent():
    """LEVEL_4 (different modality e.g. CU) counts as independent."""
    assert independence_counts_as_fallback(BackendIndependenceLevel.LEVEL_4_DIFFERENT_MODALITY)


def test_level_5_counts_as_independent():
    """LEVEL_5 (human assisted) counts as independent."""
    assert independence_counts_as_fallback(BackendIndependenceLevel.LEVEL_5_HUMAN_ASSISTED)


def test_mcp_subtype_enum_values():
    """All 8 MCP subtypes exist."""
    assert len(MCPSubtype) == 8
    assert MCPSubtype.MCP_AS_INTERFACE.value == "mcp_as_interface"
    assert MCPSubtype.MCP_NATIVE_SOURCE_CONNECTOR.value == "mcp_native_source_connector"


def test_backend_types_include_mcp_and_local_file():
    """ExtractionBackendType includes MCP and LOCAL_FILE."""
    assert ExtractionBackendType.MCP.value == "mcp"
    assert ExtractionBackendType.LOCAL_FILE.value == "local_file"


def test_mcp_wrapper_is_level_0():
    """MCP wrapper profile should be LEVEL_0."""
    p = MCPToolProfile(
        tool_name="internal-wrapper",
        server_name="local",
        mcp_subtype=MCPSubtype.MCP_AS_INTERFACE,
        independence_level=BackendIndependenceLevel.LEVEL_0_INTERFACE_WRAPPER,
    )
    assert not independence_counts_as_fallback(p.independence_level)
