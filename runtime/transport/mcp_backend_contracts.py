"""
MCP backend contracts for Phase 96.2.

MCP is a protocol/adapter layer, not automatically an independent backend.
An MCP server/tool must be classified by its underlying capability and
failure domain before it can be evaluated against the extraction contract.

These dataclasses capture the profile and evaluation of any MCP tool
that claims to provide extraction capability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from runtime.transport.extraction_backend_contracts import (
    BackendIndependenceLevel,
    ExtractionBackendType,
    ExtractionCoverageStatus,
    MCPSubtype,
)


@dataclass
class MCPToolProfile:
    """Profile of an MCP tool's extraction capabilities."""

    tool_name: str
    server_name: str
    declared_capabilities: list[str] = field(default_factory=list)
    inferred_backend_type: ExtractionBackendType = ExtractionBackendType.MCP
    mcp_subtype: MCPSubtype = MCPSubtype.MCP_UNKNOWN
    independence_level: BackendIndependenceLevel = (
        BackendIndependenceLevel.LEVEL_0_INTERFACE_WRAPPER
    )
    data_access_channel: str = ""
    requires_auth: bool = False
    can_read_metadata: bool = False
    can_read_body: bool = False
    can_read_tabs: bool = False
    can_read_child_tabs: bool = False
    can_emit_canonical_records: bool = False
    blocked_actions: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "server_name": self.server_name,
            "declared_capabilities": self.declared_capabilities,
            "inferred_backend_type": self.inferred_backend_type.value,
            "mcp_subtype": self.mcp_subtype.value,
            "independence_level": self.independence_level.value,
            "data_access_channel": self.data_access_channel,
            "requires_auth": self.requires_auth,
            "can_read_metadata": self.can_read_metadata,
            "can_read_body": self.can_read_body,
            "can_read_tabs": self.can_read_tabs,
            "can_read_child_tabs": self.can_read_child_tabs,
            "can_emit_canonical_records": self.can_emit_canonical_records,
            "blocked_actions": self.blocked_actions,
            "notes": self.notes,
        }


@dataclass
class MCPBackendEvaluation:
    """Evaluation of an MCP tool against the extraction contract."""

    tool_profile: MCPToolProfile
    contract_coverage_status: ExtractionCoverageStatus = ExtractionCoverageStatus.UNKNOWN
    independence_value: str = ""
    parity_status: str = ""
    recommended_use: str = ""
    failure_domain_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_profile": self.tool_profile.to_dict(),
            "contract_coverage_status": self.contract_coverage_status.value,
            "independence_value": self.independence_value,
            "parity_status": self.parity_status,
            "recommended_use": self.recommended_use,
            "failure_domain_notes": self.failure_domain_notes,
        }
