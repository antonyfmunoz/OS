"""
Adapter Engine contracts for Phase 96.5 + 96.6.

The Adapter Engine is the UMH subsystem that makes external tools,
SaaS platforms, sources, protocols, runtimes, and backends usable
by UMH. It does not merely connect — it integrates operationally.

Each mature adapter package contains 8 layers:
1. Access Adapter — how UMH connects (API/SDK/CLI/MCP/CU/etc.)
2. Auth Adapter — OAuth, API key, service account, browser profile, etc.
3. Capability Map — what the tool can do (read/write/search/etc.)
4. Tool Mastery Pack — expert-level usage: best practices, workflows,
   prompts, failure modes, edge cases, quality standards, anti-patterns,
   API defaults/traps, completeness requirements, validation checklists
5. Governance Policy — allowed/blocked actions, approval gates, risk levels
6. Execution Wrapper — callable implementation, retries, logging
7. Tests / Validation — adapter, safety, no-secret, parity, coverage
8. Registry Entry — access path class, auth class, independence, status

Tool Mastery is an internal layer of the Adapter Engine, not separate.
Tool Mastery Packs make tools usable like a master.
Access/Auth/Capability adapters make tools connectable.
Selection Engine chooses which adapter package to use.
Worker Runtime executes through the selected adapter using the mastery pack.

Phase 96.6 terminology precision:
- "interface" = where operators interact (CLI, Discord, web dashboard)
- "access path" = mechanism to reach data (API, SDK, MCP, CU, etc.)
- "auth method" = how access is authorized (OAuth, API key, etc.)
- "adapter package" = complete 8-layer operational bundle
- "execution environment" = where work runs (VPS, Docker, tmux, etc.)
- "capability" = what needs to be done, tool-independent
- BackendCategory enum is retained for backward compat but semantically
  means "access path category"
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class InterfaceType(str, Enum):
    """Where a human/operator/agent communicates with UMH."""

    CLI = "cli"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    MOBILE_APP = "mobile_app"
    WORKSTATION_UI = "workstation_ui"
    VOICE = "voice"
    WEB_DASHBOARD = "web_dashboard"
    API_CLIENT = "api_client"
    UNKNOWN = "unknown"


class AccessPathType(str, Enum):
    """Mechanism used to reach data/actions. Prefer over 'backend'."""

    API = "api"
    SDK = "sdk"
    CLI_DIRECT_PROTOCOL = "cli_direct_protocol"
    CLI_VENDOR_NATIVE = "cli_vendor_native"
    MCP_API_CONNECTOR = "mcp_api_connector"
    MCP_VENDOR_TOOL_WRAPPER = "mcp_vendor_tool_wrapper"
    MCP_LOCAL_FILE_CONNECTOR = "mcp_local_file_connector"
    MCP_COMPUTER_USE_CONTROLLER = "mcp_computer_use_controller"
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


class ExecutionEnvironmentType(str, Enum):
    """Where work runs."""

    VPS = "vps"
    LOCAL_DESKTOP_SESSION = "local_desktop_session"
    WSL = "wsl"
    TMUX = "tmux"
    DOCKER = "docker"
    BROWSER_PROFILE = "browser_profile"
    DESKTOP_DAEMON = "desktop_daemon"
    PYTHON_VENV = "python_venv"
    CLAUDE_CODE_SESSION = "claude_code_session"
    UNKNOWN = "unknown"


class CapabilityType(str, Enum):
    """What needs to be done, independent of the tool."""

    SOURCE_INVENTORY = "source_inventory"
    DOCUMENT_EXTRACTION = "document_extraction"
    TAB_AWARE_DOCUMENT_EXTRACTION = "tab_aware_document_extraction"
    BROWSER_CONTROL = "browser_control"
    VISIBLE_GUI_CONTROL = "visible_gui_control"
    FILE_PARSING = "file_parsing"
    MESSAGE_SENDING = "message_sending"
    MEMORY_WRITE = "memory_write"
    SOURCE_GRAPH_CONSTRUCTION = "source_graph_construction"
    ACTION_EXECUTION = "action_execution"
    UNKNOWN = "unknown"


class AdapterType(str, Enum):
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


class AdapterStatus(str, Enum):
    DISCOVERED = "discovered"
    CANDIDATE = "candidate"
    GENERATED = "generated"
    TESTED = "tested"
    AVAILABLE = "available"
    PREFERRED = "preferred"
    FALLBACK = "fallback"
    DEPRECATED = "deprecated"
    BLOCKED = "blocked"


@dataclass
class AdapterProfile:
    """Profile of an adapter/backend."""

    adapter_id: str
    adapter_type: AdapterType
    source_system: str = ""
    implementation_description: str = ""
    capabilities: list[str] = field(default_factory=list)
    independence_level: str = ""
    current_status: AdapterStatus = AdapterStatus.DISCOVERED
    auth_profile_ref: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "adapter_type": self.adapter_type.value,
            "source_system": self.source_system,
            "implementation_description": self.implementation_description,
            "capabilities": self.capabilities,
            "independence_level": self.independence_level,
            "current_status": self.current_status.value,
            "auth_profile_ref": self.auth_profile_ref,
            "notes": self.notes,
        }


@dataclass
class AdapterCapabilityMap:
    """Maps what an adapter can do."""

    adapter_id: str
    can_read: bool = False
    can_write: bool = False
    can_list: bool = False
    can_search: bool = False
    can_stream: bool = False
    supports_tabs: bool = False
    supports_child_tabs: bool = False
    supports_provenance: bool = False
    supports_canonical_records: bool = False
    mutation_risk: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "can_read": self.can_read,
            "can_write": self.can_write,
            "can_list": self.can_list,
            "can_search": self.can_search,
            "can_stream": self.can_stream,
            "supports_tabs": self.supports_tabs,
            "supports_child_tabs": self.supports_child_tabs,
            "supports_provenance": self.supports_provenance,
            "supports_canonical_records": self.supports_canonical_records,
            "mutation_risk": self.mutation_risk,
        }


@dataclass
class AdapterSafetyPolicy:
    """Safety policy for an adapter."""

    adapter_id: str
    read_only_enforced: bool = True
    no_secret_exposure: bool = True
    no_credential_capture: bool = True
    no_scope_expansion: bool = True
    redaction_rules: list[str] = field(default_factory=list)
    blocked_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "read_only_enforced": self.read_only_enforced,
            "no_secret_exposure": self.no_secret_exposure,
            "no_credential_capture": self.no_credential_capture,
            "no_scope_expansion": self.no_scope_expansion,
            "redaction_rules": self.redaction_rules,
            "blocked_actions": self.blocked_actions,
        }


@dataclass
class ToolMasteryPack:
    """Expert-level usage knowledge for a tool/platform.

    Tool Mastery is an internal layer of the Adapter Engine.
    It makes tools usable like a master — not just connectable.

    Examples:
    - Claude Code adapter's mastery pack = .claude/skills/claude-code-cli.md
    - Google Docs adapter's mastery pack = extraction best practices, tab traversal patterns
    - Discord adapter's mastery pack = rate limit patterns, embed formatting
    """

    adapter_id: str
    tool_name: str = ""
    version_scope: str = ""
    best_practices: list[str] = field(default_factory=list)
    common_workflows: list[str] = field(default_factory=list)
    anti_patterns: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    recovery_playbooks: list[str] = field(default_factory=list)
    hidden_features: list[str] = field(default_factory=list)
    api_defaults_and_traps: list[str] = field(default_factory=list)
    completeness_requirements: list[str] = field(default_factory=list)
    validation_checklist: list[str] = field(default_factory=list)
    edge_cases: list[str] = field(default_factory=list)
    quality_standards: list[str] = field(default_factory=list)
    operating_manual_ref: str = ""
    skill_file_ref: str = ""
    examples: list[str] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)
    last_verified: str = ""
    provenance_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "tool_name": self.tool_name,
            "version_scope": self.version_scope,
            "best_practices_count": len(self.best_practices),
            "common_workflows_count": len(self.common_workflows),
            "anti_patterns_count": len(self.anti_patterns),
            "failure_modes_count": len(self.failure_modes),
            "recovery_playbooks_count": len(self.recovery_playbooks),
            "hidden_features_count": len(self.hidden_features),
            "api_defaults_and_traps_count": len(self.api_defaults_and_traps),
            "completeness_requirements_count": len(self.completeness_requirements),
            "validation_checklist_count": len(self.validation_checklist),
            "edge_cases_count": len(self.edge_cases),
            "quality_standards_count": len(self.quality_standards),
            "operating_manual_ref": self.operating_manual_ref,
            "skill_file_ref": self.skill_file_ref,
            "examples_count": len(self.examples),
            "prompts_count": len(self.prompts),
            "last_verified": self.last_verified,
            "provenance_notes": self.provenance_notes,
        }


@dataclass
class AdapterRegistryEntry:
    """Full registry entry for an adapter package (8 layers)."""

    profile: AdapterProfile
    capability_map: AdapterCapabilityMap | None = None
    safety_policy: AdapterSafetyPolicy | None = None
    tool_mastery: ToolMasteryPack | None = None
    has_tests: bool = False
    has_docs: bool = False
    has_contract: bool = False
    has_tool_mastery: bool = False
    governance_classification: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile.to_dict(),
            "capability_map": self.capability_map.to_dict() if self.capability_map else None,
            "safety_policy": self.safety_policy.to_dict() if self.safety_policy else None,
            "tool_mastery": self.tool_mastery.to_dict() if self.tool_mastery else None,
            "has_tests": self.has_tests,
            "has_docs": self.has_docs,
            "has_contract": self.has_contract,
            "has_tool_mastery": self.has_tool_mastery,
            "governance_classification": self.governance_classification,
        }


@dataclass
class AdapterPackage:
    """Complete operational bundle for an external capability (8 layers)."""

    adapter_profile: AdapterProfile
    auth_profile_ref: str = ""
    access_paths: list[AccessPathType] = field(default_factory=list)
    capability_map: AdapterCapabilityMap | None = None
    governance_policy_ref: str = ""
    execution_wrapper_ref: str = ""
    tool_mastery_pack: ToolMasteryPack | None = None
    tests_ref: str = ""
    registry_entry: AdapterRegistryEntry | None = None
    selection_metadata: dict[str, Any] = field(default_factory=dict)
    maturity_score: float = 0.0
    gaps_to_100: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_profile": self.adapter_profile.to_dict(),
            "auth_profile_ref": self.auth_profile_ref,
            "access_paths": [p.value for p in self.access_paths],
            "capability_map": self.capability_map.to_dict() if self.capability_map else None,
            "governance_policy_ref": self.governance_policy_ref,
            "execution_wrapper_ref": self.execution_wrapper_ref,
            "tool_mastery_pack": self.tool_mastery_pack.to_dict()
            if self.tool_mastery_pack
            else None,
            "tests_ref": self.tests_ref,
            "registry_entry": self.registry_entry.to_dict() if self.registry_entry else None,
            "selection_metadata": self.selection_metadata,
            "maturity_score": self.maturity_score,
            "gaps_to_100": self.gaps_to_100,
        }


def tool_mastery_has_completeness_requirements(pack: ToolMasteryPack) -> bool:
    """A mature mastery pack must define what complete extraction looks like."""
    return len(pack.completeness_requirements) > 0


def tool_mastery_has_failure_modes(pack: ToolMasteryPack) -> bool:
    """A mature mastery pack must document how the tool can fail."""
    return len(pack.failure_modes) > 0


def tool_mastery_has_anti_patterns(pack: ToolMasteryPack) -> bool:
    """A mature mastery pack must document what NOT to do."""
    return len(pack.anti_patterns) > 0


def tool_mastery_has_validation_checklist(pack: ToolMasteryPack) -> bool:
    """A mature mastery pack must include a validation checklist."""
    return len(pack.validation_checklist) > 0


def tool_mastery_is_mature(pack: ToolMasteryPack) -> bool:
    """A Tool Mastery Pack is mature when it has all critical sections populated."""
    return all(
        [
            tool_mastery_has_completeness_requirements(pack),
            tool_mastery_has_failure_modes(pack),
            tool_mastery_has_anti_patterns(pack),
            tool_mastery_has_validation_checklist(pack),
        ]
    )
