"""Canonical Type Registry — single source of truth for all UMH domain types.

Every Enum, BaseModel, and dataclass that defines a reusable domain concept
is registered here. New code MUST import from these canonical locations.
Creating a parallel type that overlaps with any registered type is a defect.

This registry is consumed by:
  - scripts/check_type_divergence.py (pre-commit gate)
  - CLAUDE.md (AI instruction)
  - Human code review

To add a new type: define it in the correct canonical module, then add
its name and module path here. The pre-commit hook will enforce it.

UMH substrate subsystem. Domain-agnostic.
"""

from __future__ import annotations

# ── Canonical Type Registry ─────────────────────────────────────────────────
# Maps type name → list of canonical module paths where it may be defined.
# Most types have exactly one canonical location. Types with multiple entries
# are homonyms: same name, genuinely different concepts (e.g., Capability as
# an Enum of job capability names vs Capability as a Pydantic model describing
# a capability instance).

CANONICAL_TYPES: dict[str, list[str]] = {
    # ── substrate/types.py ──────────────────────────────────────────────
    "SignalSource": ["substrate.types"],
    "SignalUrgency": ["substrate.types"],
    "Modality": ["substrate.types"],
    "Attachment": ["substrate.types"],
    "SignalEnvelope": ["substrate.types"],
    "Identity": ["substrate.types"],
    "MemoryType": ["substrate.types"],
    "MemoryEntry": ["substrate.types"],
    "MemoryQuery": ["substrate.types"],
    "ExecutionContext": ["substrate.types"],
    "PermissionTier": ["substrate.types"],
    "RiskClass": ["substrate.types"],
    "GovernanceDecision": ["substrate.types"],
    "GovernanceVerdict": ["substrate.types"],
    "PipelineGovernanceVerdict": ["substrate.types"],
    "ExecutionPlan": ["substrate.types"],
    "AdapterResponse": ["substrate.types"],
    "ExecutionOutcome": ["substrate.types"],
    "ExecutionResult": ["substrate.types"],
    "PipelineExecutionResult": ["substrate.types"],
    "TraceEventType": ["substrate.types"],
    "TraceEvent": ["substrate.types"],
    "TraceRecord": ["substrate.types"],
    "FeedbackType": ["substrate.types"],
    "FeedbackRecord": ["substrate.types"],
    "ComponentType": ["substrate.types"],
    "ComponentStatus": ["substrate.types"],
    "Component": ["substrate.types"],
    "RegistrationResult": ["substrate.types"],
    "PrimitiveType": ["substrate.types"],
    "OntologicalCategory": ["substrate.types"],
    "RelationshipType": ["substrate.types"],
    "TemporalMode": ["substrate.types"],
    "CausalRole": ["substrate.types"],
    "PrimitiveObservation": ["substrate.types"],
    "IngestionResult": ["substrate.types"],
    "SubstrateStatus": ["substrate.types"],
    "CapabilityStatus": ["substrate.types"],
    "CapabilityCategory": ["substrate.types"],
    "EnvironmentDomain": ["substrate.types"],
    "ResourceStatus": ["substrate.types"],
    "InterpretationType": ["substrate.types"],
    "OutcomeType": ["substrate.types"],
    "ProofType": ["substrate.types"],
    "ProofStatus": ["substrate.types"],
    "WorkPacketStatus": ["substrate.types"],
    "WorkPacketPriority": ["substrate.types"],
    "DecompositionComponentType": ["substrate.types"],
    "AdapterType": ["substrate.types"],
    "AdapterStatus": ["substrate.types"],
    "OperatorType": ["substrate.types"],
    "WorkflowStepType": ["substrate.types"],
    "WorkflowExecutionMode": ["substrate.types"],
    "WorkflowTriggerType": ["substrate.types"],
    "DashboardWidgetType": ["substrate.types"],
    "AutonomyLevel": ["substrate.types"],
    "WorldModelUpdateType": ["substrate.types"],
    # ── substrate/contracts/agent_types.py ──────────────────────────────
    "TaskType": ["substrate.contracts.agent_types"],
    "ModelProvider": ["substrate.contracts.agent_types"],
    # ── substrate/execution/runtime/capability_router.py ────────────────
    # Capability (Enum) lists job capability names: CODE_WRITE, REASON, etc.
    # Capability (BaseModel) in substrate.types describes a capability instance.
    # Both are canonical — different concepts, same name.
    "Capability": [
        "substrate.execution.runtime.capability_router",
        "substrate.types",
    ],
    # ── substrate/execution/runtime/worker_runtime_contracts.py ─────────
    "EnvironmentType": ["substrate.execution.runtime.worker_runtime_contracts"],
    "AuthorityDomain": ["substrate.execution.runtime.worker_runtime_contracts"],
    "MessageBusType": ["substrate.execution.runtime.worker_runtime_contracts"],
    # ── nodes/environments/work_packet.py ───────────────────────────────
    # WorkPacketStatus also in substrate.types — both canonical (different schemas)
    "WorkPacketRiskLevel": ["nodes.environments.work_packet"],
    "WorkPacketExecutionEnvironment": ["nodes.environments.work_packet"],
    # ── substrate/organism/runtime_graph.py ─────────────────────────────
    "AvailabilityStatus": ["substrate.organism.runtime_graph"],
    "RuntimeClass": ["substrate.organism.runtime_graph"],
    "RuntimeCapability": ["substrate.organism.runtime_graph"],
    # ── substrate/organism/coordinator.py ───────────────────────────────
    "WorkUnitStatus": ["substrate.organism.coordinator"],
    "ObjectiveStatus": ["substrate.organism.coordinator"],
    "WorkUnitType": ["substrate.organism.coordinator"],
    # ── substrate/organism/workcell_protocol.py ─────────────────────────
    "WorkcellStatus": ["substrate.organism.workcell_protocol"],
    "WorkcellRole": ["substrate.organism.workcell_protocol"],
    # ── substrate/organism/runtime_supervisor.py ────────────────────────
    "SupervisedHealth": ["substrate.organism.runtime_supervisor"],
    # ── substrate/organism/mission.py ─────────────────────────────────
    "MissionStatus": ["substrate.organism.mission"],
    # ── substrate/organism/workcell_daemon.py ──────────────────────────
    "DaemonStatus": ["substrate.organism.workcell_daemon"],
    # ── substrate/governance/policy/execution_authority_engine_v1.py ─────
    "AuthorityClass": ["substrate.governance.policy.execution_authority_engine_v1"],
    "ApprovalRequirement": ["substrate.governance.policy.execution_authority_engine_v1"],
    # ── substrate/organism/execution_economy.py ─────────────────────────
    "ExecutionClass": ["substrate.organism.execution_economy"],
    "VerificationResult": ["substrate.organism.execution_economy"],
    # ── substrate/organism/recursion_governance.py ─────────────────────
    "EscalationLevel": ["substrate.organism.recursion_governance"],
    "RecursionApproval": ["substrate.organism.recursion_governance"],
    # ── substrate/organism/advisor_hierarchy.py ────────────────────────
    "AdvisorScope": ["substrate.organism.advisor_hierarchy"],
    "AdvisorAuthority": ["substrate.organism.advisor_hierarchy"],
    "AdvisorStatus": ["substrate.organism.advisor_hierarchy"],
    # ── substrate/organism/leverage_assimilation.py ──────────────────
    "LeveragePrimitiveType": ["substrate.organism.leverage_assimilation"],
    # ── substrate/organism/event_spine.py ─────────────────────────────
    "EventDomain": ["substrate.organism.event_spine"],
    "EventPriority": ["substrate.organism.event_spine"],
    # ── substrate/organism/objective_queue.py ──────────────────────────
    "ObjectiveQueueStatus": ["substrate.organism.objective_queue"],
    # ── substrate/organism/allocation_loop.py ──────────────────────────
    "AllocationStrategy": ["substrate.organism.allocation_loop"],
    # ── substrate/organism/async_coordinator.py ───────────────────────
    "AsyncObjectiveStatus": ["substrate.organism.async_coordinator"],
    # ── substrate/organism/projection_port.py ────────────────────────
    "StateSlice": ["substrate.organism.projection_port"],
    # ── substrate/self_model.py ────────────────────────────────────────
    "Layer": ["substrate.self_model"],
    "ContextKind": ["substrate.self_model"],
}


# ── Legacy Duplicates ───────────────────────────────────────────────────────
# Pre-existing type definitions that duplicate canonical types. These existed
# before the divergence gate was installed (2026-05-27). Each entry is:
#   file_module_path → set of type names it's allowed to define despite
#   those names being owned by another module.
#
# These are TECHNICAL DEBT, not design. Each should be converged to import
# from the canonical source. New entries here require explicit justification.
# The gate blocks NEW divergence; this allowlist grandfathers OLD divergence.

LEGACY_DUPLICATES: dict[str, set[str]] = {
    # substrate.types defines both WorkPacketStatus (Enum) and references it
    # nodes.environments.work_packet also defines it — same semantics, needs merge
    "nodes.environments.work_packet": {"WorkPacketStatus"},
    # substrate.types.ProofStatus vs worker_runtime_contracts.ProofStatus
    "substrate.execution.runtime.worker_runtime_contracts": {"ProofStatus"},
    # Older contract modules that predate type centralization
    "substrate.execution.runtime.execution_contracts_v1": {"SignalSource", "GovernanceVerdict"},
    "substrate.execution.runtime.runtime_execution_result_v1": {"ExecutionOutcome"},
    "substrate.execution.bridge.capabilities": {"Capability"},
    "substrate.execution.loop.execution_loop": {"ExecutionResult"},
    "substrate.state.memory.contracts.canonical_memory_store_v1": {"MemoryEntry"},
    "substrate.sockets.envelopes": {"SignalEnvelope"},
    "substrate.foundation.primitives": {"Modality"},
    "substrate.understanding.ontology.primitive_decomposition_v1": {
        "PrimitiveType",
        "RelationshipType",
        "PrimitiveObservation",
    },
    "substrate.understanding.perception.orchestrator": {"IngestionResult"},
    "adapters.adapter_engine.substrate_candidate_gen_v1": {"MemoryType"},
    "nodes.environments.execution_binding_contracts": {"EnvironmentType"},
}


def lookup(type_name: str) -> list[str] | None:
    """Return the canonical import paths for a type name, or None if not registered."""
    return CANONICAL_TYPES.get(type_name)


def check_name(type_name: str, defining_module: str) -> str | None:
    """Return an error message if type_name is already registered elsewhere.

    Returns None if:
    - The name is not in the registry (genuinely new type)
    - The defining module is one of the canonical locations
    - The defining module is in the legacy duplicates allowlist
    """
    canonical_list = CANONICAL_TYPES.get(type_name)
    if canonical_list is None:
        return None
    for canonical in canonical_list:
        if defining_module == canonical or defining_module.endswith(canonical):
            return None
    legacy = LEGACY_DUPLICATES.get(defining_module, set())
    if type_name in legacy:
        return None
    return (
        f"DIVERGENCE BLOCKED: '{type_name}' already exists in "
        f"{canonical_list[0]}. "
        f"Import it: from {canonical_list[0]} import {type_name}"
    )
