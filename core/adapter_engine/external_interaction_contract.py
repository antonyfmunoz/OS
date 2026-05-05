"""External interaction contract for the UMH Adapter Engine.

Every interaction with an external system must be represented as an
ExternalInteraction record. This contract enforces that all external
interactions have an adapter, governance, proof requirements, and
maturity gate before execution.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExternalInteractionStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    BLOCKED = "blocked"
    EXECUTED = "executed"
    FAILED = "failed"
    COMPLETED = "completed"


class ExternalInteractionRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ExternalInteraction:
    interaction_id: str = ""
    intent_summary: str = ""
    external_system: str = ""
    external_system_type: str = ""
    adapter_category: str = ""
    required_adapter_package: str = ""
    required_adapter_family: str = ""
    capability_contract: str = ""
    target_environment: list[str] = field(default_factory=list)
    work_packet_id: str = ""
    governance_policy: str = ""
    proof_requirements: list[str] = field(default_factory=list)
    maturity_gate: str = ""
    risk_level: ExternalInteractionRisk = ExternalInteractionRisk.LOW
    approval_required: bool = False
    status: ExternalInteractionStatus = ExternalInteractionStatus.DRAFT
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "interaction_id": self.interaction_id,
            "intent_summary": self.intent_summary,
            "external_system": self.external_system,
            "external_system_type": self.external_system_type,
            "adapter_category": self.adapter_category,
            "required_adapter_package": self.required_adapter_package,
            "required_adapter_family": self.required_adapter_family,
            "capability_contract": self.capability_contract,
            "target_environment": self.target_environment,
            "work_packet_id": self.work_packet_id,
            "governance_policy": self.governance_policy,
            "proof_requirements": self.proof_requirements,
            "maturity_gate": self.maturity_gate,
            "risk_level": self.risk_level.value,
            "approval_required": self.approval_required,
            "status": self.status.value,
            "notes": self.notes,
        }


def build_external_interaction(
    interaction_id: str,
    intent_summary: str = "",
    external_system: str = "",
    external_system_type: str = "",
    adapter_category: str = "",
    required_adapter_package: str = "",
    required_adapter_family: str = "",
    capability_contract: str = "",
    target_environment: list[str] | None = None,
    work_packet_id: str = "",
    governance_policy: str = "",
    proof_requirements: list[str] | None = None,
    maturity_gate: str = "",
    risk_level: ExternalInteractionRisk = ExternalInteractionRisk.LOW,
    approval_required: bool = False,
) -> ExternalInteraction:
    return ExternalInteraction(
        interaction_id=interaction_id,
        intent_summary=intent_summary,
        external_system=external_system,
        external_system_type=external_system_type,
        adapter_category=adapter_category,
        required_adapter_package=required_adapter_package,
        required_adapter_family=required_adapter_family,
        capability_contract=capability_contract,
        target_environment=target_environment or [],
        work_packet_id=work_packet_id,
        governance_policy=governance_policy,
        proof_requirements=proof_requirements or [],
        maturity_gate=maturity_gate,
        risk_level=risk_level,
        approval_required=approval_required,
    )


def external_interaction_has_adapter(interaction: ExternalInteraction) -> bool:
    return bool(interaction.required_adapter_package or interaction.required_adapter_family)


def external_interaction_has_governance(interaction: ExternalInteraction) -> bool:
    return bool(interaction.governance_policy)


def external_interaction_has_proof_requirements(
    interaction: ExternalInteraction,
) -> bool:
    return len(interaction.proof_requirements) > 0


def external_interaction_has_maturity_gate(interaction: ExternalInteraction) -> bool:
    return bool(interaction.maturity_gate)


def external_interaction_has_capability_contract(
    interaction: ExternalInteraction,
) -> bool:
    return bool(interaction.capability_contract)


def external_interaction_is_validated(interaction: ExternalInteraction) -> bool:
    return all(
        [
            external_interaction_has_adapter(interaction),
            external_interaction_has_governance(interaction),
            external_interaction_has_proof_requirements(interaction),
            external_interaction_has_maturity_gate(interaction),
            external_interaction_has_capability_contract(interaction),
        ]
    )


def summarize_external_interaction(interaction: ExternalInteraction) -> dict[str, Any]:
    return {
        "interaction_id": interaction.interaction_id,
        "external_system": interaction.external_system,
        "adapter_category": interaction.adapter_category,
        "has_adapter": external_interaction_has_adapter(interaction),
        "has_governance": external_interaction_has_governance(interaction),
        "has_proof": external_interaction_has_proof_requirements(interaction),
        "has_maturity_gate": external_interaction_has_maturity_gate(interaction),
        "has_capability_contract": external_interaction_has_capability_contract(interaction),
        "is_validated": external_interaction_is_validated(interaction),
        "status": interaction.status.value,
        "risk_level": interaction.risk_level.value,
    }
