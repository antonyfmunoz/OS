"""
Google Workspace backend/access-path options matrix for Phase 96.3 + 96.6.

Enumerates all candidate access paths for Google Drive/Docs
ingestion with their current status, independence level, requirements,
and Tool Mastery status.

Phase 96.6: BackendCategory semantically means "access path category."
Each option now tracks whether Google Docs Tool Mastery Pack checks
are satisfied for that access path.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from eos_ai.transport.backend_registry_contracts import (
    BackendCategory,
    BackendImplementationType,
    BackendProfile,
    BackendStatus,
)


@dataclass
class GoogleWorkspaceBackendOption:
    """One candidate backend for Google Workspace extraction."""

    option_id: int
    name: str
    category: BackendCategory
    implementation_type: BackendImplementationType
    independence_level: str
    current_status: BackendStatus
    auth_methods: list[str] = field(default_factory=list)
    notes: str = ""
    tool_mastery_status: str = "not_assessed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "option_id": self.option_id,
            "name": self.name,
            "category": self.category.value,
            "implementation_type": self.implementation_type.value,
            "independence_level": self.independence_level,
            "current_status": self.current_status.value,
            "auth_methods": self.auth_methods,
            "tool_mastery_status": self.tool_mastery_status,
            "notes": self.notes,
        }


def build_google_workspace_backend_options() -> list[GoogleWorkspaceBackendOption]:
    """Build the full matrix of Google Workspace backend options."""
    return [
        GoogleWorkspaceBackendOption(
            1,
            "API tab-aware extractor",
            BackendCategory.API,
            BackendImplementationType.INTERNAL_API_EXTRACTOR,
            "reference",
            BackendStatus.COMPLETE,
            ["oauth_user_consent", "service_account"],
            "Tab-aware re-extraction done for W0-001",
            tool_mastery_status="required_google_docs_mastery_pack",
        ),
        GoogleWorkspaceBackendOption(
            2,
            "SDK tab-aware extractor",
            BackendCategory.SDK,
            BackendImplementationType.OFFICIAL_SDK,
            "level_1",
            BackendStatus.NOT_IMPLEMENTED,
            ["oauth_user_consent", "service_account"],
            "Possible via official client library",
            tool_mastery_status="required_google_docs_mastery_pack",
        ),
        GoogleWorkspaceBackendOption(
            3,
            "CLI interface wrapper",
            BackendCategory.CLI,
            BackendImplementationType.CLI_INTERFACE_WRAPPER,
            "level_0",
            BackendStatus.COMPLETE,
            ["oauth_cache"],
            "Wraps same API — not independent",
        ),
        GoogleWorkspaceBackendOption(
            4,
            "CLI direct protocol",
            BackendCategory.CLI,
            BackendImplementationType.CLI_DIRECT_PROTOCOL,
            "level_1",
            BackendStatus.NOT_IMPLEMENTED,
            ["oauth_cache", "service_account"],
            "Must use includeTabsContent=true",
            tool_mastery_status="required_google_docs_mastery_pack",
        ),
        GoogleWorkspaceBackendOption(
            5,
            "CLI vendor/native",
            BackendCategory.CLI,
            BackendImplementationType.CLI_VENDOR_NATIVE,
            "level_2",
            BackendStatus.UNKNOWN,
            ["varies"],
            "Must prove tab support",
        ),
        GoogleWorkspaceBackendOption(
            6,
            "MCP interface wrapper",
            BackendCategory.MCP,
            BackendImplementationType.MCP_INTERFACE_WRAPPER,
            "level_0",
            BackendStatus.NOT_IMPLEMENTED,
            ["varies"],
            "Not independent",
        ),
        GoogleWorkspaceBackendOption(
            7,
            "MCP API connector",
            BackendCategory.MCP,
            BackendImplementationType.MCP_API_CONNECTOR,
            "level_1",
            BackendStatus.NOT_IMPLEMENTED,
            ["oauth_user_consent"],
            "Must prove tab-aware support",
            tool_mastery_status="required_google_docs_mastery_pack",
        ),
        GoogleWorkspaceBackendOption(
            8,
            "MCP vendor/tool wrapper",
            BackendCategory.MCP,
            BackendImplementationType.MCP_VENDOR_TOOL_WRAPPER,
            "level_2",
            BackendStatus.UNKNOWN,
            ["varies"],
            "Must prove all-tabs support",
        ),
        GoogleWorkspaceBackendOption(
            9,
            "MCP local file connector",
            BackendCategory.MCP,
            BackendImplementationType.MCP_LOCAL_FILE_CONNECTOR,
            "level_3",
            BackendStatus.NOT_IMPLEMENTED,
            ["local_machine_identity"],
            "Requires export/sync policy",
        ),
        GoogleWorkspaceBackendOption(
            10,
            "MCP computer-use controller",
            BackendCategory.MCP,
            BackendImplementationType.MCP_COMPUTER_USE_CONTROLLER,
            "level_4",
            BackendStatus.NOT_IMPLEMENTED,
            ["browser_session_profile"],
            "Maps to CU requirements",
        ),
        GoogleWorkspaceBackendOption(
            11,
            "Native Computer Use",
            BackendCategory.COMPUTER_USE,
            BackendImplementationType.VISIBLE_GUI_COMPUTER_USE,
            "level_4",
            BackendStatus.PARTIAL,
            ["browser_session_profile"],
            "Foreground ownership blocks content extraction",
            tool_mastery_status="required_google_docs_mastery_pack",
        ),
        GoogleWorkspaceBackendOption(
            12,
            "Browser automation",
            BackendCategory.BROWSER_AUTOMATION,
            BackendImplementationType.MCP_BROWSER_AUTOMATION,
            "varies",
            BackendStatus.BLOCKED,
            ["browser_session_profile"],
            "Not approved unless separately approved",
            tool_mastery_status="required_if_approved",
        ),
        GoogleWorkspaceBackendOption(
            13,
            "Browser extension",
            BackendCategory.BROWSER_EXTENSION,
            BackendImplementationType.BROWSER_EXTENSION_CONNECTOR,
            "level_2",
            BackendStatus.NOT_IMPLEMENTED,
            ["browser_session_profile"],
            "Future candidate",
        ),
        GoogleWorkspaceBackendOption(
            14,
            "RPA/Desktop automation",
            BackendCategory.RPA_DESKTOP_AUTOMATION,
            BackendImplementationType.RPA_DESKTOP_AUTOMATION_CONNECTOR,
            "level_4",
            BackendStatus.NOT_IMPLEMENTED,
            ["local_machine_identity"],
            "Power Automate / AutoHotkey / WinUI",
        ),
        GoogleWorkspaceBackendOption(
            15,
            "Local export/archive parser",
            BackendCategory.LOCAL_EXPORT_ARCHIVE,
            BackendImplementationType.LOCAL_EXPORT_PARSER,
            "level_3",
            BackendStatus.NOT_IMPLEMENTED,
            ["local_machine_identity"],
            "Requires export/download/Takeout approval",
        ),
        GoogleWorkspaceBackendOption(
            16,
            "Local sync parser",
            BackendCategory.LOCAL_SYNC,
            BackendImplementationType.LOCAL_SYNC_PARSER,
            "level_3",
            BackendStatus.NOT_IMPLEMENTED,
            ["local_machine_identity"],
            "Requires Drive Desktop/sync policy",
        ),
        GoogleWorkspaceBackendOption(
            17,
            "Database/direct storage",
            BackendCategory.DATABASE_DIRECT,
            BackendImplementationType.DATABASE_DIRECT_READER,
            "n/a",
            BackendStatus.NOT_IMPLEMENTED,
            [],
            "Not applicable for Google Docs directly",
        ),
        GoogleWorkspaceBackendOption(
            18,
            "Webhook/event stream",
            BackendCategory.WEBHOOK_EVENT_STREAM,
            BackendImplementationType.WEBHOOK_EVENT_STREAM_CONSUMER,
            "level_1",
            BackendStatus.NOT_IMPLEMENTED,
            ["service_account"],
            "Future incremental sync candidate",
        ),
        GoogleWorkspaceBackendOption(
            19,
            "File parser",
            BackendCategory.FILE_PARSER,
            BackendImplementationType.FILE_PARSER,
            "level_3",
            BackendStatus.NOT_IMPLEMENTED,
            ["local_machine_identity"],
            "For exported DOCX/PDF/MD/HTML",
        ),
        GoogleWorkspaceBackendOption(
            20,
            "Manual/human-assisted",
            BackendCategory.MANUAL_HUMAN_ASSISTED,
            BackendImplementationType.HUMAN_ASSISTED,
            "level_5",
            BackendStatus.UNKNOWN,
            ["manual_login"],
            "Last resort",
        ),
    ]


def get_complete_backends() -> list[GoogleWorkspaceBackendOption]:
    """Return only COMPLETE backends."""
    return [
        o
        for o in build_google_workspace_backend_options()
        if o.current_status == BackendStatus.COMPLETE
    ]


def get_candidate_backends() -> list[GoogleWorkspaceBackendOption]:
    """Return backends that are candidates for implementation."""
    return [
        o
        for o in build_google_workspace_backend_options()
        if o.current_status not in (BackendStatus.BLOCKED, BackendStatus.COMPLETE)
    ]
