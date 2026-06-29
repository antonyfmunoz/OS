"""Production adapter manifests for all live adapter families.

Registered at operator_api startup via populate_production_registry().
"""

from __future__ import annotations

from adapters.adapter_engine.adapter_manifest import AdapterManifest, AdapterMaturityLevel
from adapters.adapter_engine.adapter_registry_contracts import (
    AdapterDescriptor,
    AdapterRegistry,
    AdapterCapability,
)
from adapters.adapter_engine.modality import ModalityType
from adapters.adapter_engine.participant import ParticipantType
from substrate.execution.runtime.worker_runtime_contracts import (
    AuthorityDomain,
    MessageBusType,
)

MODEL_ROUTER_MANIFEST = AdapterManifest(
    adapter_id="model_router",
    adapter_type="ai_routing",
    modalities=[ModalityType.API],
    participant_type=ParticipantType.EXTERNAL,
    capabilities=[
        AdapterCapability(
            capability_id="model_router:call_with_fallback",
            action_type="ai_inference",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
        AdapterCapability(
            capability_id="model_router:call_heavy",
            action_type="ai_heavy_inference",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
    ],
    maturity=AdapterMaturityLevel.L3_TESTED,
    version="v1",
    notes=["Dual-path heavy/fast routing via Anthropic, Gemini, Ollama, CC SDK"],
)

CC_SDK_MANIFEST = AdapterManifest(
    adapter_id="cc_sdk",
    adapter_type="claude_code",
    modalities=[ModalityType.API],
    participant_type=ParticipantType.EXTERNAL,
    capabilities=[
        AdapterCapability(
            capability_id="cc_sdk:query",
            action_type="claude_code_query",
            requires_local_shell=True,
            required_authority=AuthorityDomain.LOCAL_SHELL,
        ),
    ],
    maturity=AdapterMaturityLevel.L2_CAPABILITIES_KNOWN,
    version="v1",
    notes=["Subprocess-based CC CLI wrapper with CPU gate and backpressure"],
)

GOOGLE_WORKSPACE_MANIFEST = AdapterManifest(
    adapter_id="google_workspace",
    adapter_type="google_workspace",
    modalities=[ModalityType.API],
    participant_type=ParticipantType.EXTERNAL,
    capabilities=[
        AdapterCapability(
            capability_id="gws:gmail_read",
            action_type="email_read",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
        AdapterCapability(
            capability_id="gws:gmail_send",
            action_type="email_send",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
        AdapterCapability(
            capability_id="gws:drive_scan",
            action_type="drive_scan",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
    ],
    maturity=AdapterMaturityLevel.L2_CAPABILITIES_KNOWN,
    version="v1",
    notes=["OAuth2 via service account, Gmail + Drive + Docs"],
)

CALENDAR_MANIFEST = AdapterManifest(
    adapter_id="calendar",
    adapter_type="calendar",
    modalities=[ModalityType.API],
    participant_type=ParticipantType.EXTERNAL,
    capabilities=[
        AdapterCapability(
            capability_id="calendar:list_events",
            action_type="calendar_read",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
        AdapterCapability(
            capability_id="calendar:create_event",
            action_type="calendar_write",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
    ],
    maturity=AdapterMaturityLevel.L2_CAPABILITIES_KNOWN,
    version="v1",
    notes=["Google Calendar + Calendly integration"],
)

BROWSER_MANIFEST = AdapterManifest(
    adapter_id="browser",
    adapter_type="browser_automation",
    modalities=[ModalityType.COMPUTER_USE],
    participant_type=ParticipantType.EXTERNAL,
    capabilities=[
        AdapterCapability(
            capability_id="browser:navigate",
            action_type="browser_navigate",
            requires_gui=True,
            required_authority=AuthorityDomain.LOCAL_GUI,
        ),
        AdapterCapability(
            capability_id="browser:run_task",
            action_type="browser_task",
            requires_gui=True,
            required_authority=AuthorityDomain.LOCAL_GUI,
        ),
    ],
    maturity=AdapterMaturityLevel.L2_CAPABILITIES_KNOWN,
    version="v1",
    notes=["Playwright-based browser agent, runs on executor nodes only"],
)

BROWSER_AUTH_MANIFEST = AdapterManifest(
    adapter_id="browser_auth",
    adapter_type="browser_auth",
    modalities=[ModalityType.COMPUTER_USE],
    participant_type=ParticipantType.EXTERNAL,
    capabilities=[
        AdapterCapability(
            capability_id="browser_auth:clerk_login",
            action_type="clerk_auth",
            requires_gui=True,
            required_authority=AuthorityDomain.LOCAL_GUI,
        ),
        AdapterCapability(
            capability_id="browser_auth:sso_chain",
            action_type="sso_auth",
            requires_gui=True,
            required_authority=AuthorityDomain.LOCAL_GUI,
        ),
    ],
    maturity=AdapterMaturityLevel.L2_CAPABILITIES_KNOWN,
    version="v1",
    notes=["Clerk login + SSO chain (GitHub/Google) for browser automation"],
)

BROWSER_EXPORTS_MANIFEST = AdapterManifest(
    adapter_id="browser_exports",
    adapter_type="data_export",
    modalities=[ModalityType.COMPUTER_USE],
    participant_type=ParticipantType.EXTERNAL,
    capabilities=[
        AdapterCapability(
            capability_id="browser_exports:claude",
            action_type="export_claude",
            requires_gui=True,
            required_authority=AuthorityDomain.LOCAL_GUI,
        ),
        AdapterCapability(
            capability_id="browser_exports:chatgpt",
            action_type="export_chatgpt",
            requires_gui=True,
            required_authority=AuthorityDomain.LOCAL_GUI,
        ),
        AdapterCapability(
            capability_id="browser_exports:instagram",
            action_type="export_instagram",
            requires_gui=True,
            required_authority=AuthorityDomain.LOCAL_GUI,
        ),
    ],
    maturity=AdapterMaturityLevel.L1_CONNECTED,
    version="v1",
    notes=["Playwright data export scripts for Claude, ChatGPT, Instagram"],
)

NOTION_MANIFEST = AdapterManifest(
    adapter_id="notion",
    adapter_type="knowledge_base",
    modalities=[ModalityType.API],
    participant_type=ParticipantType.EXTERNAL,
    capabilities=[
        AdapterCapability(
            capability_id="notion:publish",
            action_type="notion_publish",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
        AdapterCapability(
            capability_id="notion:sync",
            action_type="notion_sync",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
    ],
    maturity=AdapterMaturityLevel.L2_CAPABILITIES_KNOWN,
    version="v1",
    notes=["Notion API publisher + bidirectional sync"],
)

DATA_SOURCE_MANIFEST = AdapterManifest(
    adapter_id="data_sources",
    adapter_type="ingestion",
    modalities=[ModalityType.API, ModalityType.FILESYSTEM],
    participant_type=ParticipantType.EXTERNAL,
    capabilities=[
        AdapterCapability(
            capability_id="data_sources:local_file",
            action_type="ingest_local_file",
            required_authority=AuthorityDomain.LOCAL_SHELL,
        ),
        AdapterCapability(
            capability_id="data_sources:github",
            action_type="ingest_github",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
        AdapterCapability(
            capability_id="data_sources:gws",
            action_type="ingest_gws",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
        AdapterCapability(
            capability_id="data_sources:conversation",
            action_type="ingest_conversation",
            required_authority=AuthorityDomain.LOCAL_SHELL,
        ),
    ],
    maturity=AdapterMaturityLevel.L2_CAPABILITIES_KNOWN,
    version="v1",
    notes=["Source adapters for ingestion pipeline: local, GitHub, GWS, conversations"],
)

TOOL_ADAPTERS_MANIFEST = AdapterManifest(
    adapter_id="tool_adapters",
    adapter_type="system_tools",
    modalities=[ModalityType.FILESYSTEM],
    participant_type=ParticipantType.EXTERNAL,
    capabilities=[
        AdapterCapability(
            capability_id="tools:filesystem",
            action_type="filesystem_ops",
            requires_local_shell=True,
            required_authority=AuthorityDomain.LOCAL_SHELL,
        ),
        AdapterCapability(
            capability_id="tools:shell",
            action_type="shell_exec",
            requires_local_shell=True,
            required_authority=AuthorityDomain.LOCAL_SHELL,
        ),
        AdapterCapability(
            capability_id="tools:git",
            action_type="git_ops",
            requires_local_shell=True,
            required_authority=AuthorityDomain.LOCAL_SHELL,
        ),
        AdapterCapability(
            capability_id="tools:tmux",
            action_type="tmux_ops",
            requires_local_shell=True,
            required_authority=AuthorityDomain.LOCAL_SHELL,
        ),
    ],
    maturity=AdapterMaturityLevel.L2_CAPABILITIES_KNOWN,
    version="v1",
    notes=["Governed filesystem, shell, git, tmux adapters"],
)

BROADCAST_MANIFEST = AdapterManifest(
    adapter_id="broadcast",
    adapter_type="media_pipeline",
    modalities=[ModalityType.API],
    participant_type=ParticipantType.EXTERNAL,
    capabilities=[
        AdapterCapability(
            capability_id="broadcast:scene_render",
            action_type="scene_render",
            required_authority=AuthorityDomain.LOCAL_SHELL,
        ),
        AdapterCapability(
            capability_id="broadcast:zmq_stream",
            action_type="zmq_stream",
            required_authority=AuthorityDomain.LOCAL_SHELL,
        ),
    ],
    maturity=AdapterMaturityLevel.L1_CONNECTED,
    version="v1",
    notes=["FFmpeg + ZMQ broadcast pipeline for media rendering"],
)

NOTEBOOKLM_MANIFEST = AdapterManifest(
    adapter_id="notebooklm",
    adapter_type="knowledge_sync",
    modalities=[ModalityType.API],
    participant_type=ParticipantType.EXTERNAL,
    capabilities=[
        AdapterCapability(
            capability_id="notebooklm:sync",
            action_type="notebooklm_sync",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
    ],
    maturity=AdapterMaturityLevel.L1_CONNECTED,
    version="v1",
    notes=["Bidirectional Neon <-> NotebookLM sync"],
)

SCRAPLING_MANIFEST = AdapterManifest(
    adapter_id="scrapling",
    adapter_type="web_scraping",
    modalities=[ModalityType.API],
    participant_type=ParticipantType.EXTERNAL,
    capabilities=[
        AdapterCapability(
            capability_id="scrapling:fetch",
            action_type="web_fetch",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
    ],
    maturity=AdapterMaturityLevel.L1_CONNECTED,
    version="v1",
    notes=["Stealth HTTP fetching via Scrapling for research/monitoring"],
)

TAILSCALE_MANIFEST = AdapterManifest(
    adapter_id="tailscale",
    adapter_type="network",
    modalities=[ModalityType.API],
    participant_type=ParticipantType.EXTERNAL,
    capabilities=[
        AdapterCapability(
            capability_id="tailscale:list_devices",
            action_type="tailscale_list",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
    ],
    maturity=AdapterMaturityLevel.L1_CONNECTED,
    version="v1",
    notes=["Tailscale Admin API v2 for device management"],
)

SSH_MANIFEST = AdapterManifest(
    adapter_id="ssh",
    adapter_type="remote_shell",
    modalities=[ModalityType.API],
    participant_type=ParticipantType.EXTERNAL,
    capabilities=[
        AdapterCapability(
            capability_id="ssh:remote_exec",
            action_type="ssh_exec",
            requires_local_shell=True,
            required_authority=AuthorityDomain.LOCAL_SHELL,
        ),
        AdapterCapability(
            capability_id="ssh:scp",
            action_type="scp_transfer",
            requires_local_shell=True,
            required_authority=AuthorityDomain.LOCAL_SHELL,
        ),
    ],
    maturity=AdapterMaturityLevel.L2_CAPABILITIES_KNOWN,
    version="v1",
    notes=["SSH/SCP utilities with CPU gate compliance"],
)

GITHUB_OPERATIONS_MANIFEST = AdapterManifest(
    adapter_id="github_operations",
    adapter_type="github",
    modalities=[ModalityType.API],
    participant_type=ParticipantType.EXTERNAL,
    capabilities=[
        AdapterCapability(
            capability_id="github:create_pr",
            action_type="github_pr_create",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
        AdapterCapability(
            capability_id="github:merge_pr",
            action_type="github_pr_merge",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
        AdapterCapability(
            capability_id="github:create_branch",
            action_type="github_branch_create",
            requires_local_shell=True,
            required_authority=AuthorityDomain.LOCAL_SHELL,
        ),
    ],
    maturity=AdapterMaturityLevel.L2_CAPABILITIES_KNOWN,
    version="v1",
    notes=["GitHub CLI wrapper for governed PR and branch operations"],
)

ALL_PRODUCTION_MANIFESTS: list[AdapterManifest] = [
    MODEL_ROUTER_MANIFEST,
    CC_SDK_MANIFEST,
    GOOGLE_WORKSPACE_MANIFEST,
    CALENDAR_MANIFEST,
    BROWSER_MANIFEST,
    BROWSER_AUTH_MANIFEST,
    BROWSER_EXPORTS_MANIFEST,
    NOTION_MANIFEST,
    DATA_SOURCE_MANIFEST,
    TOOL_ADAPTERS_MANIFEST,
    BROADCAST_MANIFEST,
    NOTEBOOKLM_MANIFEST,
    SCRAPLING_MANIFEST,
    TAILSCALE_MANIFEST,
    SSH_MANIFEST,
    GITHUB_OPERATIONS_MANIFEST,
]


def populate_production_registry(registry: AdapterRegistry | None = None) -> AdapterRegistry:
    """Register all production adapter manifests into the registry."""
    if registry is None:
        registry = AdapterRegistry()
    for manifest in ALL_PRODUCTION_MANIFESTS:
        registry.register_manifest(manifest)
    return registry
