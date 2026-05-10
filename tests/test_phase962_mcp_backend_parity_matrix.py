"""Tests for Phase 96.2 MCP additions to Google Docs backend parity matrix."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate.extraction_backend_contracts import (
    ExtractionBackendType,
    MCPSubtype,
)
from eos_ai.substrate.google_docs_backend_parity_matrix import (
    build_google_docs_backend_matrix,
)


def test_matrix_includes_mcp_entries():
    """Backend matrix includes MCP rows after Phase 96.2."""
    matrix = build_google_docs_backend_matrix()
    assert len(matrix.mcp_entries) > 0


def test_matrix_has_five_mcp_subtypes():
    """Matrix has 5 MCP entries covering key subtypes."""
    matrix = build_google_docs_backend_matrix()
    assert len(matrix.mcp_entries) == 5
    subtypes = {e.mcp_subtype for e in matrix.mcp_entries}
    assert MCPSubtype.MCP_AS_INTERFACE.value in subtypes
    assert MCPSubtype.MCP_API_CONNECTOR.value in subtypes
    assert MCPSubtype.MCP_VENDOR_TOOL_WRAPPER.value in subtypes
    assert MCPSubtype.MCP_LOCAL_FILE_CONNECTOR.value in subtypes
    assert MCPSubtype.MCP_COMPUTER_USE_CONTROLLER.value in subtypes


def test_mcp_wrapper_entry_is_not_implemented():
    """MCP_AS_INTERFACE entry is NOT_IMPLEMENTED."""
    matrix = build_google_docs_backend_matrix()
    wrapper = next(
        e for e in matrix.mcp_entries if e.mcp_subtype == MCPSubtype.MCP_AS_INTERFACE.value
    )
    assert wrapper.overall_status == "NOT_IMPLEMENTED"


def test_matrix_includes_browser_automation_entry():
    """Matrix includes browser automation entry and it is BLOCKED."""
    matrix = build_google_docs_backend_matrix()
    assert matrix.browser_automation_entry is not None
    assert matrix.browser_automation_entry.overall_status == "BLOCKED"


def test_matrix_includes_local_file_entry():
    """Matrix includes local file entry and it is NOT_APPROVED."""
    matrix = build_google_docs_backend_matrix()
    assert matrix.local_file_entry is not None
    assert matrix.local_file_entry.overall_status == "NOT_APPROVED"


def test_matrix_serialization_includes_mcp():
    """Serialized matrix includes mcp_backends list."""
    matrix = build_google_docs_backend_matrix()
    d = matrix.to_dict()
    assert "mcp_backends" in d
    assert len(d["mcp_backends"]) == 5
    assert "browser_automation" in d
    assert "local_file" in d


def test_existing_backends_still_present():
    """API, CLI, and CU entries still present after MCP addition."""
    matrix = build_google_docs_backend_matrix()
    assert matrix.api_entry is not None
    assert matrix.cli_entry is not None
    assert matrix.cu_entry is not None
    assert matrix.api_entry.overall_status == "complete"


def test_mcp_entries_have_independence_levels():
    """All MCP entries declare an independence level."""
    matrix = build_google_docs_backend_matrix()
    for entry in matrix.mcp_entries:
        assert entry.independence_level != ""


def test_mcp_cu_controller_maps_to_cu():
    """MCP_COMPUTER_USE_CONTROLLER maps to CU backend."""
    matrix = build_google_docs_backend_matrix()
    cu_mcp = next(
        e
        for e in matrix.mcp_entries
        if e.mcp_subtype == MCPSubtype.MCP_COMPUTER_USE_CONTROLLER.value
    )
    assert cu_mcp.overall_status == "MAPS_TO_CU"
