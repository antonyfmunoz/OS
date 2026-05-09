"""Control plane router contracts for the UMH substrate layer.

Typed dataclasses for the routing lifecycle:
  WorkPacket        -- incoming request from any interface
  CapabilityRequirement -- what the packet needs
  RouterDecision    -- which runtime/adapter was selected and why
  RuntimeProofReference -- pointer to a RuntimeProofRecord
  RouterResult      -- normalized result returned to the interface

Stateless. Deterministic. No LLM. No autonomy.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RouterStatus(str, Enum):
    ROUTED = "routed"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    NO_ADAPTER = "no_adapter"
    NO_RUNTIME = "no_runtime"
    INVALID_PACKET = "invalid_packet"


class CapabilityType(str, Enum):
    SHELL_EXECUTION = "shell_execution"
    WINDOWS_GUI_EXECUTION = "windows_gui_execution"
    DOCUMENT_EXTRACTION = "document_extraction"
    INGESTION_CANDIDACY = "ingestion_candidacy"
    MEMORY_PROMOTION = "memory_promotion"
    CANONICAL_MEMORY_QUERY = "canonical_memory_query"
    ENVIRONMENT_DISCOVERY = "environment_discovery"
    ADAPTER_SYNTHESIS = "adapter_synthesis"
    CAPABILITY_PLANNING = "capability_planning"
    ORCHESTRATION_GOVERNANCE = "orchestration_governance"
    SUBSTRATE_CONTINUITY = "substrate_continuity"
    GOVERNANCE_INTELLIGENCE = "governance_intelligence"
    CONSTITUTIONAL_GOVERNANCE = "constitutional_governance"
    DISTRIBUTED_FEDERATION = "distributed_federation"
    RESOURCE_ECONOMICS = "resource_economics"


ALLOWED_ACTION_TYPES = frozenset(
    {
        "adapter_report",
        "actuator_proof",
        "capability_report",
        "orchestration_report",
        "continuity_report",
        "governance_intelligence_report",
        "constitution_report",
        "economics_report",
        "federation_report",
        "ping",
        "open_application_url",
        "chrome_open_google_drive",
        "drive_open_safe_test_doc",
        "doc_extract_safe_test_doc",
        "doc_ingestion_candidate_safe_test_doc",
        "ingest_safe_doc",
        "ingest_safe_doc_cu",
        "chrome_proof",
        "explore_environment",
        "promote_safe_memory_candidate",
        "query_safe_memory_reference",
        "relay_status",
    }
)


@dataclass
class WorkPacket:
    """Incoming work request from any interface adapter."""

    packet_id: str
    action_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    capability_required: str = ""
    authority_level: str = ""
    requested_runtime: str = ""
    timeout_seconds: int = 60
    source_interface: str = ""
    trace_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class CapabilityRequirement:
    """Resolved capability needed for a WorkPacket."""

    action_type: str
    capability_type: CapabilityType
    requires_gui: bool = False
    requires_local_shell: bool = False
    authority_required: str = ""


@dataclass
class RouterDecision:
    """Record of the routing decision made by the control plane."""

    packet_id: str
    action_type: str
    runtime_target: str
    adapter_selected: str
    capability_matched: str
    authority_satisfied: bool = True
    rejection_reason: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class RuntimeProofReference:
    """Lightweight pointer to a RuntimeProofRecord."""

    proof_id: str = ""
    proof_status: str = ""
    adapter_status: str = ""
    request_id: str = ""
    trace_id: str = ""


@dataclass
class RouterResult:
    """Normalized result returned to the calling interface."""

    router_status: RouterStatus
    router_decision: RouterDecision | None = None
    runtime_target: str = ""
    adapter_selected: str = ""
    runtime_proof_reference: RuntimeProofReference | None = None
    execution_trace_id: str = ""
    normalized_status: str = ""
    error_message: str = ""
    started_at: str = ""
    completed_at: str = ""

    def __post_init__(self) -> None:
        if not self.started_at:
            self.started_at = datetime.now(timezone.utc).isoformat()
