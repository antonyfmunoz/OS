"""Adapter boundary validator for the UMH Adapter Engine.

Validates that external interactions have proper adapter boundaries.
Detects direct external use, missing environment adapters, missing
human approval adapters, missing model adapters, and missing data
source adapters.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .adapter_taxonomy import (
    AdapterCategory,
    classify_external_system,
    ExternalSystemType,
    adapter_category_requires_tool_mastery,
)
from .external_interaction_contract import (
    ExternalInteraction,
    external_interaction_has_adapter,
    external_interaction_has_environment_when_required,
    external_interaction_has_governance,
    external_interaction_has_mastery_requirements,
    external_interaction_has_maturity_gate,
    external_interaction_has_proof_requirements,
    external_interaction_has_worker_when_required,
    external_interaction_is_validated,
)


class AdapterBoundaryValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    DIRECT_EXTERNAL_USE_DETECTED = "direct_external_use_detected"
    ADAPTER_MISSING = "adapter_missing"
    ADAPTER_UNMATURED = "adapter_unmatured"
    MASTERY_MISSING = "mastery_missing"
    TOOL_MASTERY_MISSING = "tool_mastery_missing"
    GOVERNANCE_MISSING = "governance_missing"
    PROOF_MISSING = "proof_missing"
    ENVIRONMENT_MISSING = "environment_missing"
    WORKER_MISSING = "worker_missing"


_ENVIRONMENT_SYSTEM_TYPES = frozenset(
    {
        ExternalSystemType.LOCAL_WSL.value,
        ExternalSystemType.LOCAL_WINDOWS_GUI.value,
        ExternalSystemType.VPS.value,
        ExternalSystemType.TMUX.value,
    }
)

_HUMAN_APPROVAL_SYSTEM_TYPES = frozenset(
    {
        ExternalSystemType.FOUNDER_CONFIRMATION.value,
    }
)

_MODEL_SYSTEM_TYPES = frozenset(
    {
        ExternalSystemType.OPENAI_API.value,
        ExternalSystemType.ANTHROPIC_API.value,
    }
)

_DATA_SOURCE_SYSTEM_TYPES = frozenset(
    {
        ExternalSystemType.FILESYSTEM.value,
        ExternalSystemType.DATABASE.value,
    }
)


@dataclass
class AdapterBoundaryValidationResult:
    interaction_id: str = ""
    status: AdapterBoundaryValidationStatus = AdapterBoundaryValidationStatus.INVALID
    can_execute: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_fixes: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "interaction_id": self.interaction_id,
            "status": self.status.value,
            "can_execute": self.can_execute,
            "errors": self.errors,
            "warnings": self.warnings,
            "required_fixes": self.required_fixes,
            "notes": self.notes,
        }


def validate_adapter_boundary(
    interaction: ExternalInteraction,
) -> AdapterBoundaryValidationResult:
    result = AdapterBoundaryValidationResult(
        interaction_id=interaction.interaction_id,
    )

    validate_no_direct_external_use(interaction, result)
    if result.errors:
        result.status = AdapterBoundaryValidationStatus.DIRECT_EXTERNAL_USE_DETECTED
        return result

    sys_type = interaction.external_system_type
    if sys_type in _ENVIRONMENT_SYSTEM_TYPES:
        validate_environment_adapter_present(interaction, result)
    if sys_type in _HUMAN_APPROVAL_SYSTEM_TYPES:
        validate_human_approval_adapter_present(interaction, result)
    if sys_type in _MODEL_SYSTEM_TYPES:
        validate_model_adapter_present(interaction, result)
    if sys_type in _DATA_SOURCE_SYSTEM_TYPES:
        validate_data_source_adapter_present(interaction, result)

    if not external_interaction_has_governance(interaction):
        result.errors.append("GOVERNANCE_MISSING")
        result.required_fixes.append("Add governance_policy")
    if not external_interaction_has_proof_requirements(interaction):
        result.errors.append("PROOF_MISSING")
        result.required_fixes.append("Add proof_requirements")
    if not external_interaction_has_maturity_gate(interaction):
        result.errors.append("MATURITY_GATE_MISSING")
        result.required_fixes.append("Add maturity_gate")
    if not external_interaction_has_mastery_requirements(interaction):
        result.errors.append("MASTERY_MISSING")
        result.required_fixes.append("Add mastery_requirements")
    if not external_interaction_has_environment_when_required(interaction):
        result.errors.append("ENVIRONMENT_MISSING")
        result.required_fixes.append("Add target_environment")
    if not external_interaction_has_worker_when_required(interaction):
        result.errors.append("WORKER_MISSING")
        result.required_fixes.append("Add required_worker_runtime")

    try:
        ext_type = ExternalSystemType(sys_type)
        category = classify_external_system(ext_type)
        if adapter_category_requires_tool_mastery(category):
            if not interaction.notes or not any(
                "tool_mastery" in n.lower() for n in interaction.notes
            ):
                result.warnings.append(f"TOOL_MASTERY_RECOMMENDED for {category.value} adapter")
    except ValueError:
        pass

    if not result.errors:
        result.status = AdapterBoundaryValidationStatus.VALID
        result.can_execute = True
    elif any(
        "ADAPTER_MISSING" in e
        or "ENVIRONMENT_ADAPTER" in e
        or "HUMAN_APPROVAL_ADAPTER" in e
        or "MODEL_ADAPTER" in e
        or "DATA_SOURCE_ADAPTER" in e
        for e in result.errors
    ):
        result.status = AdapterBoundaryValidationStatus.ADAPTER_MISSING
    elif any("GOVERNANCE_MISSING" in e for e in result.errors):
        result.status = AdapterBoundaryValidationStatus.GOVERNANCE_MISSING
    elif any("PROOF_MISSING" in e for e in result.errors):
        result.status = AdapterBoundaryValidationStatus.PROOF_MISSING

    return result


def validate_no_direct_external_use(
    interaction: ExternalInteraction,
    result: AdapterBoundaryValidationResult,
) -> None:
    if not external_interaction_has_adapter(interaction):
        result.errors.append(
            f"DIRECT_EXTERNAL_USE: {interaction.external_system} used without adapter"
        )
        result.required_fixes.append("Add required_adapter_package or required_adapter_family")


def validate_environment_adapter_present(
    interaction: ExternalInteraction,
    result: AdapterBoundaryValidationResult,
) -> None:
    if not external_interaction_has_adapter(interaction):
        result.errors.append(
            f"ENVIRONMENT_ADAPTER_MISSING: {interaction.external_system_type} "
            "requires environment adapter"
        )
        result.required_fixes.append("Add environment adapter package")


def validate_human_approval_adapter_present(
    interaction: ExternalInteraction,
    result: AdapterBoundaryValidationResult,
) -> None:
    if not external_interaction_has_adapter(interaction):
        result.errors.append(
            f"HUMAN_APPROVAL_ADAPTER_MISSING: {interaction.external_system_type} "
            "requires human approval adapter"
        )
        result.required_fixes.append("Add human approval adapter package")


def validate_model_adapter_present(
    interaction: ExternalInteraction,
    result: AdapterBoundaryValidationResult,
) -> None:
    if not external_interaction_has_adapter(interaction):
        result.errors.append(
            f"MODEL_ADAPTER_MISSING: {interaction.external_system_type} requires model adapter"
        )
        result.required_fixes.append("Add model adapter package")


def validate_data_source_adapter_present(
    interaction: ExternalInteraction,
    result: AdapterBoundaryValidationResult,
) -> None:
    if not external_interaction_has_adapter(interaction):
        result.errors.append(
            f"DATA_SOURCE_ADAPTER_MISSING: {interaction.external_system_type} "
            "requires data source adapter"
        )
        result.required_fixes.append("Add data source adapter package")


def validate_mastery_requirements_present(
    interaction: ExternalInteraction,
    result: AdapterBoundaryValidationResult,
) -> None:
    if not external_interaction_has_mastery_requirements(interaction):
        result.errors.append("MASTERY_REQUIREMENTS_MISSING")
        result.required_fixes.append("Add mastery_requirements before execution")


def adapter_boundary_blocks_execution(
    result: AdapterBoundaryValidationResult,
) -> bool:
    return not result.can_execute
