"""Action / Execution Separation Law contracts.

Action = intended state transformation.
Capability = abstract ability required.
Adapter = connection/translation boundary.
Environment = where execution happens.
Worker Runtime = what performs execution.
Actuation = low-level effect-producing operation.
Work Packet = governed executable instruction.
Proof Artifact = evidence that execution happened correctly.
Trace = complete inspectable record.
Learning = governed update process.

Action is NOT execution. Adapter is NOT worker. Environment is NOT
worker. Actuation is NOT adapter. Work Packet binds action to execution.
Proof requirements must exist BEFORE execution.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ActionType(str, Enum):
    READ = "read"
    WRITE = "write"
    TRANSFORM = "transform"
    ROUTE = "route"
    NOTIFY = "notify"
    APPROVE = "approve"
    INGEST = "ingest"
    EXTRACT = "extract"
    VALIDATE = "validate"
    SIMULATE = "simulate"
    ANALYZE = "analyze"
    GENERATE = "generate"
    CONTROL_ENVIRONMENT = "control_environment"
    HUMAN_CONFIRMATION = "human_confirmation"


class ExecutionSeparationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    ACTION_MISSING = "action_missing"
    CAPABILITY_MISSING = "capability_missing"
    ENVIRONMENT_MISSING = "environment_missing"
    WORKER_MISSING = "worker_missing"
    ADAPTER_BOUNDARY_MISSING = "adapter_boundary_missing"
    GOVERNANCE_MISSING = "governance_missing"
    PROOF_MISSING = "proof_missing"


@dataclass
class ActionContract:
    action_id: str = ""
    action_type: ActionType = ActionType.READ
    intended_state_change: str = ""
    required_capabilities: list[str] = field(default_factory=list)
    required_adapters: list[str] = field(default_factory=list)
    required_environments: list[str] = field(default_factory=list)
    required_workers: list[str] = field(default_factory=list)
    required_mastery: list[str] = field(default_factory=list)
    governance_policy: str = ""
    risk_level: str = "low"
    authority_required: str = ""
    success_criteria: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    proof_requirements: list[str] = field(default_factory=list)
    idempotency_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "intended_state_change": self.intended_state_change,
            "required_capabilities": self.required_capabilities,
            "required_adapters": self.required_adapters,
            "required_environments": self.required_environments,
            "required_workers": self.required_workers,
            "required_mastery": self.required_mastery,
            "governance_policy": self.governance_policy,
            "risk_level": self.risk_level,
            "authority_required": self.authority_required,
            "success_criteria": self.success_criteria,
            "failure_modes": self.failure_modes,
            "proof_requirements": self.proof_requirements,
            "idempotency_key": self.idempotency_key,
        }


@dataclass
class ExecutionBinding:
    action_id: str = ""
    work_packet_id: str = ""
    environment_id: str = ""
    worker_runtime_id: str = ""
    adapter_boundaries: list[str] = field(default_factory=list)
    actuator_type: str = ""
    trace_id: str = ""
    status: str = "pending"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "work_packet_id": self.work_packet_id,
            "environment_id": self.environment_id,
            "worker_runtime_id": self.worker_runtime_id,
            "adapter_boundaries": self.adapter_boundaries,
            "actuator_type": self.actuator_type,
            "trace_id": self.trace_id,
            "status": self.status,
            "notes": self.notes,
        }


def build_action_contract(
    action_id: str,
    action_type: ActionType = ActionType.READ,
    intended_state_change: str = "",
    required_capabilities: list[str] | None = None,
    required_adapters: list[str] | None = None,
    required_environments: list[str] | None = None,
    required_workers: list[str] | None = None,
    required_mastery: list[str] | None = None,
    governance_policy: str = "",
    risk_level: str = "low",
    authority_required: str = "",
    success_criteria: list[str] | None = None,
    failure_modes: list[str] | None = None,
    proof_requirements: list[str] | None = None,
    idempotency_key: str = "",
) -> ActionContract:
    return ActionContract(
        action_id=action_id,
        action_type=action_type,
        intended_state_change=intended_state_change,
        required_capabilities=required_capabilities or [],
        required_adapters=required_adapters or [],
        required_environments=required_environments or [],
        required_workers=required_workers or [],
        required_mastery=required_mastery or [],
        governance_policy=governance_policy,
        risk_level=risk_level,
        authority_required=authority_required,
        success_criteria=success_criteria or [],
        failure_modes=failure_modes or [],
        proof_requirements=proof_requirements or [],
        idempotency_key=idempotency_key,
    )


def build_execution_binding(
    action_id: str,
    work_packet_id: str = "",
    environment_id: str = "",
    worker_runtime_id: str = "",
    adapter_boundaries: list[str] | None = None,
    actuator_type: str = "",
    trace_id: str = "",
) -> ExecutionBinding:
    return ExecutionBinding(
        action_id=action_id,
        work_packet_id=work_packet_id,
        environment_id=environment_id,
        worker_runtime_id=worker_runtime_id,
        adapter_boundaries=adapter_boundaries or [],
        actuator_type=actuator_type,
        trace_id=trace_id,
    )


def action_contract_is_complete(action: ActionContract) -> bool:
    return all(
        [
            bool(action.action_id),
            bool(action.intended_state_change),
            len(action.required_capabilities) > 0,
            len(action.proof_requirements) > 0,
            bool(action.governance_policy),
        ]
    )


def execution_binding_is_complete(binding: ExecutionBinding) -> bool:
    return all(
        [
            bool(binding.action_id),
            bool(binding.environment_id),
            bool(binding.worker_runtime_id),
            len(binding.adapter_boundaries) > 0,
        ]
    )


def validate_action_execution_separation(
    action: ActionContract,
    binding: ExecutionBinding,
) -> ExecutionSeparationStatus:
    if not action.action_id:
        return ExecutionSeparationStatus.ACTION_MISSING
    if not action.required_capabilities:
        return ExecutionSeparationStatus.CAPABILITY_MISSING
    if not binding.environment_id:
        return ExecutionSeparationStatus.ENVIRONMENT_MISSING
    if not binding.worker_runtime_id:
        return ExecutionSeparationStatus.WORKER_MISSING
    if not binding.adapter_boundaries:
        return ExecutionSeparationStatus.ADAPTER_BOUNDARY_MISSING
    if not action.governance_policy:
        return ExecutionSeparationStatus.GOVERNANCE_MISSING
    if not action.proof_requirements:
        return ExecutionSeparationStatus.PROOF_MISSING
    return ExecutionSeparationStatus.VALID


def summarize_action_execution_contract(
    action: ActionContract,
    binding: ExecutionBinding,
) -> dict[str, Any]:
    status = validate_action_execution_separation(action, binding)
    return {
        "action_id": action.action_id,
        "action_type": action.action_type.value,
        "binding_environment": binding.environment_id,
        "binding_worker": binding.worker_runtime_id,
        "adapter_boundaries": binding.adapter_boundaries,
        "separation_status": status.value,
        "action_complete": action_contract_is_complete(action),
        "binding_complete": execution_binding_is_complete(binding),
    }
