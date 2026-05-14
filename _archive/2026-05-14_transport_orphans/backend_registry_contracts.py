"""
Backend registry contracts for Phase 96.3.

All backend/access-path types must target the same canonical
extraction contract. API, SDK, CLI, MCP, Computer Use, browser
automation, browser extension, RPA, local sync, local export,
database, webhook, file parser, mobile, manual, hybrid are all
candidates — not quality tiers.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BackendCategory(str, Enum):
    API = "api"
    SDK = "sdk"
    CLI = "cli"
    MCP = "mcp"
    COMPUTER_USE = "computer_use"
    BROWSER_AUTOMATION = "browser_automation"
    BROWSER_EXTENSION = "browser_extension"
    RPA_DESKTOP_AUTOMATION = "rpa_desktop_automation"
    LOCAL_SYNC = "local_sync"
    LOCAL_EXPORT_ARCHIVE = "local_export_archive"
    DATABASE_DIRECT = "database_direct"
    WEBHOOK_EVENT_STREAM = "webhook_event_stream"
    FILE_PARSER = "file_parser"
    MOBILE_AUTOMATION = "mobile_automation"
    MANUAL_HUMAN_ASSISTED = "manual_human_assisted"
    HYBRID = "hybrid"


class BackendImplementationType(str, Enum):
    INTERNAL_API_EXTRACTOR = "internal_api_extractor"
    OFFICIAL_SDK = "official_sdk"
    CLI_INTERFACE_WRAPPER = "cli_interface_wrapper"
    CLI_DIRECT_PROTOCOL = "cli_direct_protocol"
    CLI_VENDOR_NATIVE = "cli_vendor_native"
    MCP_INTERFACE_WRAPPER = "mcp_interface_wrapper"
    MCP_API_CONNECTOR = "mcp_api_connector"
    MCP_VENDOR_TOOL_WRAPPER = "mcp_vendor_tool_wrapper"
    MCP_LOCAL_FILE_CONNECTOR = "mcp_local_file_connector"
    MCP_COMPUTER_USE_CONTROLLER = "mcp_computer_use_controller"
    MCP_BROWSER_AUTOMATION = "mcp_browser_automation"
    MCP_NATIVE_SOURCE_CONNECTOR = "mcp_native_source_connector"
    VISIBLE_GUI_COMPUTER_USE = "visible_gui_computer_use"
    BROWSER_EXTENSION_CONNECTOR = "browser_extension_connector"
    RPA_DESKTOP_AUTOMATION_CONNECTOR = "rpa_desktop_automation_connector"
    LOCAL_EXPORT_PARSER = "local_export_parser"
    LOCAL_SYNC_PARSER = "local_sync_parser"
    DATABASE_DIRECT_READER = "database_direct_reader"
    WEBHOOK_EVENT_STREAM_CONSUMER = "webhook_event_stream_consumer"
    FILE_PARSER = "file_parser"
    MOBILE_AUTOMATION_CONNECTOR = "mobile_automation_connector"
    HUMAN_ASSISTED = "human_assisted"
    HYBRID_CONNECTOR = "hybrid_connector"


class BackendSelectionFactor(str, Enum):
    COMPLETENESS = "completeness"
    SAFETY = "safety"
    PROVENANCE = "provenance"
    SPEED = "speed"
    AUTH_STATUS = "auth_status"
    FAILURE_DOMAIN_INDEPENDENCE = "failure_domain_independence"
    IMPLEMENTATION_MATURITY = "implementation_maturity"
    HUMAN_SUPERVISION_REQUIRED = "human_supervision_required"
    COST = "cost"
    RATE_LIMIT_RISK = "rate_limit_risk"
    DATA_FIDELITY = "data_fidelity"
    MUTATION_RISK = "mutation_risk"
    SECRET_EXPOSURE_RISK = "secret_exposure_risk"


class BackendStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    NOT_IMPLEMENTED = "not_implemented"
    UNKNOWN = "unknown"


@dataclass
class BackendProfile:
    """Full profile of a backend/access-path candidate."""

    backend_id: str
    category: BackendCategory
    implementation_type: BackendImplementationType
    source_type: str = ""
    supported_capabilities: list[str] = field(default_factory=list)
    independence_level: str = ""
    current_status: BackendStatus = BackendStatus.UNKNOWN
    coverage_contract_status: str = ""
    failure_modes: list[str] = field(default_factory=list)
    safety_constraints: list[str] = field(default_factory=list)
    required_auth_methods: list[str] = field(default_factory=list)
    required_approvals: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend_id": self.backend_id,
            "category": self.category.value,
            "implementation_type": self.implementation_type.value,
            "source_type": self.source_type,
            "supported_capabilities": self.supported_capabilities,
            "independence_level": self.independence_level,
            "current_status": self.current_status.value,
            "coverage_contract_status": self.coverage_contract_status,
            "failure_modes": self.failure_modes,
            "safety_constraints": self.safety_constraints,
            "required_auth_methods": self.required_auth_methods,
            "required_approvals": self.required_approvals,
            "notes": self.notes,
        }
