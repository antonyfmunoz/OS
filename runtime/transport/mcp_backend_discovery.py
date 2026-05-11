"""
MCP backend discovery for Phase 96.3.

Discovery/classification capability for MCP tools.
Does not connect to external MCP tools — creates the framework
for evaluating what should be assessed next.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from runtime.transport.extraction_backend_contracts import (
    BackendIndependenceLevel,
    MCPSubtype,
)
from runtime.transport.mcp_backend_contracts import MCPToolProfile
from runtime.transport.mcp_backend_classifier import (
    classify_mcp_tool,
    evaluate_mcp_against_extraction_contract,
    mcp_counts_as_independent_backend,
)


@dataclass
class MCPDiscoveryPlan:
    """Plan for discovering and evaluating MCP tools."""

    source_type: str = ""
    candidate_subtypes: list[MCPSubtype] = field(default_factory=list)
    discovery_steps: list[str] = field(default_factory=list)
    evaluation_criteria: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "candidate_subtypes": [s.value for s in self.candidate_subtypes],
            "discovery_steps": self.discovery_steps,
            "evaluation_criteria": self.evaluation_criteria,
        }


@dataclass
class MCPDiscoveryReport:
    """Report of MCP tool discovery results."""

    tools_found: list[MCPToolProfile] = field(default_factory=list)
    tools_classified: int = 0
    independent_backends: int = 0
    interface_only: int = 0
    blocked: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tools_found": len(self.tools_found),
            "tools_classified": self.tools_classified,
            "independent_backends": self.independent_backends,
            "interface_only": self.interface_only,
            "blocked": self.blocked,
        }


def build_mcp_discovery_plan(source_type: str = "google_docs") -> MCPDiscoveryPlan:
    """Build a plan for discovering MCP tools for a source type."""
    return MCPDiscoveryPlan(
        source_type=source_type,
        candidate_subtypes=[
            MCPSubtype.MCP_API_CONNECTOR,
            MCPSubtype.MCP_VENDOR_TOOL_WRAPPER,
            MCPSubtype.MCP_LOCAL_FILE_CONNECTOR,
            MCPSubtype.MCP_COMPUTER_USE_CONTROLLER,
            MCPSubtype.MCP_NATIVE_SOURCE_CONNECTOR,
        ],
        discovery_steps=[
            "Identify available MCP servers/tools",
            "Classify each by subtype",
            "Inspect declared capabilities",
            "Map to canonical extraction contract",
            "Assess auth/scope requirements",
            "Assess mutation risk",
            "Assess data coverage",
            "Assess independence level",
            "Register as candidate backend",
            "Select only if appropriate for task",
        ],
        evaluation_criteria=[
            "Tab-aware Google Docs coverage",
            "All-tabs traversal",
            "Body content extraction",
            "Canonical record emission",
            "Read-only constraint",
            "No credential exposure",
            "Independence level",
        ],
    )


def parse_mcp_tool_manifest(manifest: dict[str, Any]) -> MCPToolProfile:
    """Parse an MCP tool manifest into a profile."""
    return MCPToolProfile(
        tool_name=manifest.get("name", "unknown"),
        server_name=manifest.get("server", "unknown"),
        declared_capabilities=manifest.get("capabilities", []),
        data_access_channel=manifest.get("data_access_channel", ""),
        requires_auth=manifest.get("requires_auth", False),
        can_read_metadata=manifest.get("can_read_metadata", False),
        can_read_body=manifest.get("can_read_body", False),
        can_read_tabs=manifest.get("can_read_tabs", False),
        can_read_child_tabs=manifest.get("can_read_child_tabs", False),
        can_emit_canonical_records=manifest.get("can_emit_canonical_records", False),
        notes=manifest.get("notes", ""),
    )


def classify_available_mcp_tool(tool_manifest: dict[str, Any]) -> MCPToolProfile:
    """Parse and classify an MCP tool from its manifest."""
    profile = parse_mcp_tool_manifest(tool_manifest)
    return classify_mcp_tool(profile)


def evaluate_mcp_tool_for_google_docs(tool_profile: MCPToolProfile) -> dict[str, Any]:
    """Evaluate an MCP tool specifically for Google Docs extraction."""
    from runtime.transport.extraction_backend_contracts import (
        ExtractionBackendType,
        build_google_docs_contract,
    )

    contract = build_google_docs_contract("evaluation", ExtractionBackendType.MCP)
    evaluation = evaluate_mcp_against_extraction_contract(tool_profile, contract)
    return evaluation.to_dict()


def register_mcp_candidate_backend(tool_profile: MCPToolProfile) -> dict[str, Any]:
    """Register an MCP tool as a candidate backend."""
    classified = classify_mcp_tool(tool_profile)
    return {
        "tool_name": classified.tool_name,
        "server_name": classified.server_name,
        "mcp_subtype": classified.mcp_subtype.value,
        "independence_level": classified.independence_level.value,
        "is_independent": mcp_counts_as_independent_backend(classified),
        "status": "candidate_registered",
    }


def build_mcp_discovery_report(
    tool_profiles: list[MCPToolProfile],
) -> MCPDiscoveryReport:
    """Build a discovery report from classified MCP tools."""
    independent = 0
    interface_only = 0
    blocked = 0

    for p in tool_profiles:
        classified = classify_mcp_tool(p)
        if classified.mcp_subtype == MCPSubtype.MCP_BROWSER_AUTOMATION:
            blocked += 1
        elif mcp_counts_as_independent_backend(classified):
            independent += 1
        else:
            interface_only += 1

    return MCPDiscoveryReport(
        tools_found=tool_profiles,
        tools_classified=len(tool_profiles),
        independent_backends=independent,
        interface_only=interface_only,
        blocked=blocked,
    )
