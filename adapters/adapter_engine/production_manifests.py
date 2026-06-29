"""Production adapter manifests for the 4 live adapter families.

Registered at operator_api startup via populate_production_registry().
"""

from __future__ import annotations

from adapters.adapter_engine.adapter_manifest import AdapterManifest, AdapterMaturityLevel
from adapters.adapter_engine.adapter_registry_contracts import (
    AdapterDescriptor,
    AdapterRegistry,
    CapabilityDescriptor,
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
        CapabilityDescriptor(
            capability_id="model_router:call_with_fallback",
            action_type="ai_inference",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
        CapabilityDescriptor(
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
        CapabilityDescriptor(
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
        CapabilityDescriptor(
            capability_id="gws:gmail_read",
            action_type="email_read",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
        CapabilityDescriptor(
            capability_id="gws:gmail_send",
            action_type="email_send",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
        CapabilityDescriptor(
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
        CapabilityDescriptor(
            capability_id="calendar:list_events",
            action_type="calendar_read",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
        CapabilityDescriptor(
            capability_id="calendar:create_event",
            action_type="calendar_write",
            required_authority=AuthorityDomain.REMOTE_ORCHESTRATION,
        ),
    ],
    maturity=AdapterMaturityLevel.L2_CAPABILITIES_KNOWN,
    version="v1",
    notes=["Google Calendar + Calendly integration"],
)

ALL_PRODUCTION_MANIFESTS: list[AdapterManifest] = [
    MODEL_ROUTER_MANIFEST,
    CC_SDK_MANIFEST,
    GOOGLE_WORKSPACE_MANIFEST,
    CALENDAR_MANIFEST,
]


def populate_production_registry(registry: AdapterRegistry | None = None) -> AdapterRegistry:
    """Register all production adapter manifests into the registry."""
    if registry is None:
        registry = AdapterRegistry()
    for manifest in ALL_PRODUCTION_MANIFESTS:
        registry.register_manifest(manifest)
    return registry
