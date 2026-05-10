"""UMH External Boundary Law.

No external system, tool, SaaS, model, runtime, environment, human
approval process, data source, filesystem, browser, operating system,
or physical-world actor may be accessed directly by UMH.

Every external interaction must pass through an Adapter Package,
Adapter Family member, Environment Adapter, Model Adapter, Data Source
Adapter, Human Approval Adapter, or Physical-World Adapter.

Adapters are the universal connection and translation boundary between
UMH's internal model and external reality.

Adapters do NOT independently execute actions. Execution is performed
only by the governed Action System through the Execution Spine, using
an approved worker/runtime in an explicit environment.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .external_interaction_contract import (
    ExternalInteraction,
    external_interaction_has_adapter,
    external_interaction_has_capability_contract,
    external_interaction_has_environment_when_required,
    external_interaction_has_governance,
    external_interaction_has_mastery_requirements,
    external_interaction_has_maturity_gate,
    external_interaction_has_proof_requirements,
    external_interaction_has_worker_when_required,
)


class BoundaryLawStatus(str, Enum):
    COMPLIANT = "compliant"
    VIOLATION = "violation"
    MISSING_ADAPTER = "missing_adapter"
    MISSING_CONTRACT = "missing_contract"
    MISSING_GOVERNANCE = "missing_governance"
    MISSING_PROOF = "missing_proof"
    MISSING_MASTERY = "missing_mastery"
    MISSING_MATURITY_GATE = "missing_maturity_gate"
    MISSING_ENVIRONMENT = "missing_environment"
    MISSING_WORKER = "missing_worker"
    UNKNOWN_EXTERNAL_SYSTEM = "unknown_external_system"


@dataclass
class BoundaryLawDecision:
    interaction_id: str = ""
    external_system: str = ""
    compliant: bool = False
    status: BoundaryLawStatus = BoundaryLawStatus.VIOLATION
    violations: list[str] = field(default_factory=list)
    required_fixes: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "interaction_id": self.interaction_id,
            "external_system": self.external_system,
            "compliant": self.compliant,
            "status": self.status.value,
            "violations": self.violations,
            "required_fixes": self.required_fixes,
            "notes": self.notes,
        }


def evaluate_external_boundary_law(
    interaction: ExternalInteraction,
) -> BoundaryLawDecision:
    decision = BoundaryLawDecision(
        interaction_id=interaction.interaction_id,
        external_system=interaction.external_system,
    )

    if not interaction.external_system_type:
        decision.status = BoundaryLawStatus.UNKNOWN_EXTERNAL_SYSTEM
        decision.violations.append("UNKNOWN_EXTERNAL_SYSTEM_TYPE")
        decision.required_fixes.append("Specify external_system_type")
        return decision

    require_adapter_for_external_system(interaction, decision)
    require_contract_for_external_interaction(interaction, decision)
    require_governance_for_external_interaction(interaction, decision)
    require_proof_for_external_interaction(interaction, decision)
    require_mastery_for_external_interaction(interaction, decision)
    require_maturity_gate_for_external_interaction(interaction, decision)
    require_environment_for_external_interaction(interaction, decision)
    require_worker_for_external_interaction(interaction, decision)

    if not decision.violations:
        decision.compliant = True
        decision.status = BoundaryLawStatus.COMPLIANT
    else:
        first_violation = decision.violations[0]
        if "MISSING_ADAPTER" in first_violation:
            decision.status = BoundaryLawStatus.MISSING_ADAPTER
        elif "MISSING_CONTRACT" in first_violation:
            decision.status = BoundaryLawStatus.MISSING_CONTRACT
        elif "MISSING_GOVERNANCE" in first_violation:
            decision.status = BoundaryLawStatus.MISSING_GOVERNANCE
        elif "MISSING_PROOF" in first_violation:
            decision.status = BoundaryLawStatus.MISSING_PROOF
        elif "MISSING_MASTERY" in first_violation:
            decision.status = BoundaryLawStatus.MISSING_MASTERY
        elif "MISSING_MATURITY" in first_violation:
            decision.status = BoundaryLawStatus.MISSING_MATURITY_GATE
        elif "MISSING_ENVIRONMENT" in first_violation:
            decision.status = BoundaryLawStatus.MISSING_ENVIRONMENT
        elif "MISSING_WORKER" in first_violation:
            decision.status = BoundaryLawStatus.MISSING_WORKER

    return decision


def external_boundary_blocks_execution(decision: BoundaryLawDecision) -> bool:
    return not decision.compliant


def require_adapter_for_external_system(
    interaction: ExternalInteraction,
    decision: BoundaryLawDecision,
) -> None:
    if not external_interaction_has_adapter(interaction):
        decision.violations.append(
            f"MISSING_ADAPTER: {interaction.external_system} has no adapter boundary"
        )
        decision.required_fixes.append("Add required_adapter_package or required_adapter_family")


def require_contract_for_external_interaction(
    interaction: ExternalInteraction,
    decision: BoundaryLawDecision,
) -> None:
    if not external_interaction_has_capability_contract(interaction):
        decision.violations.append(
            f"MISSING_CONTRACT: {interaction.external_system} has no capability contract"
        )
        decision.required_fixes.append("Add capability_contract")


def require_governance_for_external_interaction(
    interaction: ExternalInteraction,
    decision: BoundaryLawDecision,
) -> None:
    if not external_interaction_has_governance(interaction):
        decision.violations.append(
            f"MISSING_GOVERNANCE: {interaction.external_system} has no governance policy"
        )
        decision.required_fixes.append("Add governance_policy")


def require_proof_for_external_interaction(
    interaction: ExternalInteraction,
    decision: BoundaryLawDecision,
) -> None:
    if not external_interaction_has_proof_requirements(interaction):
        decision.violations.append(
            f"MISSING_PROOF: {interaction.external_system} has no proof requirements"
        )
        decision.required_fixes.append("Add proof_requirements")


def require_mastery_for_external_interaction(
    interaction: ExternalInteraction,
    decision: BoundaryLawDecision,
) -> None:
    if not external_interaction_has_mastery_requirements(interaction):
        decision.violations.append(
            f"MISSING_MASTERY: {interaction.external_system} has no mastery requirements"
        )
        decision.required_fixes.append("Add mastery_requirements")


def require_maturity_gate_for_external_interaction(
    interaction: ExternalInteraction,
    decision: BoundaryLawDecision,
) -> None:
    if not external_interaction_has_maturity_gate(interaction):
        decision.violations.append(
            f"MISSING_MATURITY_GATE: {interaction.external_system} has no maturity gate"
        )
        decision.required_fixes.append("Add maturity_gate")


def require_environment_for_external_interaction(
    interaction: ExternalInteraction,
    decision: BoundaryLawDecision,
) -> None:
    if not external_interaction_has_environment_when_required(interaction):
        decision.violations.append(
            f"MISSING_ENVIRONMENT: {interaction.external_system} requires target_environment"
        )
        decision.required_fixes.append("Add target_environment")


def require_worker_for_external_interaction(
    interaction: ExternalInteraction,
    decision: BoundaryLawDecision,
) -> None:
    if not external_interaction_has_worker_when_required(interaction):
        decision.violations.append(
            f"MISSING_WORKER: {interaction.external_system} requires worker_runtime"
        )
        decision.required_fixes.append("Add required_worker_runtime")


def summarize_boundary_law_decision(
    decision: BoundaryLawDecision,
) -> dict[str, Any]:
    return {
        "interaction_id": decision.interaction_id,
        "external_system": decision.external_system,
        "compliant": decision.compliant,
        "status": decision.status.value,
        "violation_count": len(decision.violations),
        "fix_count": len(decision.required_fixes),
    }
