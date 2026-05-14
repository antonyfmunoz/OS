"""UMH Protocol — Execution Plane (Layer 7).

Covers action system (§13.1), work packets (§13.2), and environments (§13.4).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from .common import (
    AdapterPackageRef,
    AdapterRef,
    ApprovalStatus,
    AuthorityLevel,
    CapabilityRef,
    Constraint,
    EnvironmentRef,
    EnvironmentType,
    FailureMode,
    GovernancePolicyRef,
    MasteryRef,
    PacketStatus,
    Permission,
    ProofRequirement,
    RiskLevel,
    WorkerRef,
)


# ---------------------------------------------------------------------------
# §13.1 — Action System
# ---------------------------------------------------------------------------


class StateTransition(BaseModel):
    """An intended state change. Referenced in §13.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    from_state: dict[str, Any] = {}
    to_state: dict[str, Any] = {}
    description: str = ""


class SuccessCriterion(BaseModel):
    """Criterion for action success. Referenced in §13.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    criterion_id: str
    description: str
    verification_method: str = ""


class ActionContract(BaseModel):
    """Proposed state transformation. Defined in canonical synthesis §13.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    action_id: str
    action_type: str
    intended_state_change: StateTransition
    required_capabilities: list[CapabilityRef] = []
    required_adapters: list[AdapterRef] = []
    required_environments: list[EnvironmentRef] = []
    required_workers: list[WorkerRef] = []
    required_mastery: list[MasteryRef] = []
    governance_policy: GovernancePolicyRef | None = None
    risk_level: RiskLevel
    authority_required: AuthorityLevel
    success_criteria: list[SuccessCriterion] = []
    failure_modes: list[FailureMode] = []
    proof_requirements: list[ProofRequirement] = []
    idempotency_key: str


# ---------------------------------------------------------------------------
# §13.2 — Work Packet
# ---------------------------------------------------------------------------


class OutputSpec(BaseModel):
    """Expected output specification. Referenced in §13.2."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    output_id: str
    name: str
    type: str = ""
    description: str = ""


class WorkPacket(BaseModel):
    """Governed executable instruction. Defined in canonical synthesis §13.2."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    packet_id: str
    work_order_id: str
    title: str
    description: str
    action_type: str
    target_environment: EnvironmentRef
    required_adapter_packages: list[AdapterPackageRef] = []
    required_tool_or_mastery_packs: list[MasteryRef] = []
    risk_level: RiskLevel
    approval_status: ApprovalStatus
    founder_confirmation_required: bool = False
    allowed_actions: list[str] = []
    blocked_actions: list[str] = []
    expected_outputs: list[OutputSpec] = []
    proof_requirements: list[ProofRequirement] = []
    timeout_seconds: int
    created_at: int
    expires_at: int
    status: PacketStatus
    trace_id: str
    notes: str = ""


# ---------------------------------------------------------------------------
# §13.4 — Environment
# ---------------------------------------------------------------------------


class ResourceModel(BaseModel):
    """Resource availability for an environment. Referenced in §13.4."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    cpu_cores: int | None = None
    memory_gb: float | None = None
    disk_gb: float | None = None
    gpu: bool = False
    description: str = ""


class NetworkState(BaseModel):
    """Network connectivity state. Referenced in §13.4."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    connected: bool = True
    bandwidth_mbps: float | None = None
    latency_ms: float | None = None
    vpn_active: bool = False


class Environment(BaseModel):
    """Execution environment. Defined in canonical synthesis §13.4."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    environment_id: str
    type: EnvironmentType
    capabilities: list[CapabilityRef] = []
    constraints: list[Constraint] = []
    resources: ResourceModel | None = None
    permissions: list[Permission] = []
    network_state: NetworkState | None = None
    availability: float = 1.0
    reliability: float = 1.0
