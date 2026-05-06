"""Execution Binding Validator for the Environment Bridge.

Validates that an ExecutionBinding has all 6 layers properly bound
before execution is allowed. Rejects ambiguous, incomplete, or
architecturally invalid bindings.

Rules enforced:
- All 6 layers must be present and non-empty
- Chrome actions reject explorer/default-browser/generic shell routing
- Google Drive/Docs actions require google_workspace target_service_family
- WSL/tmux cannot be final GUI authority (gui_actuator role)
- W0 visible Chrome launch requires founder_visual_confirmation or
  trusted desktop adapter proof
- process_exists_only and window_metadata_only are blocked evidence

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .execution_binding_contracts import (
    DISALLOWED_CHROME_LAUNCH_METHODS,
    WSL_TMUX_SURFACE_TYPES,
    ApplicationLaunchMethod,
    EvidenceType,
    ExecutionBinding,
    ExecutionSurfaceRole,
    ExecutionSurfaceType,
    ProofLevel,
    TargetServiceFamily,
)


@dataclass
class BindingValidationResult:
    valid: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def validate_execution_binding(binding: ExecutionBinding) -> BindingValidationResult:
    """Validate a complete execution binding across all 6 layers."""
    result = BindingValidationResult()

    _validate_environment(binding, result)
    _validate_execution_surfaces(binding, result)
    _validate_application(binding, result)
    _validate_target_services(binding, result)
    _validate_capabilities(binding, result)
    _validate_proof(binding, result)
    _validate_cross_layer_rules(binding, result)

    if not result.errors:
        result.valid = True

    return result


def validate_execution_binding_dict(binding_dict: dict[str, Any]) -> BindingValidationResult:
    """Validate an execution binding from its dict representation."""
    result = BindingValidationResult()

    if not binding_dict:
        result.errors.append("MISSING_EXECUTION_BINDING: binding is empty or None")
        return result

    if not binding_dict.get("environment"):
        result.errors.append("MISSING_ENVIRONMENT: environment binding required")

    if not binding_dict.get("execution_surfaces"):
        result.errors.append("MISSING_EXECUTION_SURFACES: at least one execution surface required")

    if not binding_dict.get("application"):
        result.errors.append("MISSING_APPLICATION: application binding required")

    if not binding_dict.get("target_services"):
        result.errors.append("MISSING_TARGET_SERVICES: at least one target service required")

    if not binding_dict.get("capabilities"):
        result.errors.append("MISSING_CAPABILITIES: at least one capability required")

    if not binding_dict.get("proof"):
        result.errors.append("MISSING_PROOF: proof binding required")

    env = binding_dict.get("environment", {})
    if env and not env.get("environment_id"):
        result.errors.append("MISSING_ENVIRONMENT_ID: environment_id required")
    if env and not env.get("environment_type"):
        result.errors.append("MISSING_ENVIRONMENT_TYPE: environment_type required")

    app = binding_dict.get("application", {})
    if app:
        launch = app.get("launch_method", "")
        disallowed = app.get("disallowed_launch_methods", [])
        if launch and launch in disallowed:
            result.errors.append(f"DISALLOWED_LAUNCH_METHOD: {launch} is in disallowed list")
        if launch:
            try:
                method = ApplicationLaunchMethod(launch)
                if method in DISALLOWED_CHROME_LAUNCH_METHODS:
                    result.errors.append(
                        f"CHROME_LAUNCH_METHOD_BLOCKED: {launch} is not allowed for Chrome actions"
                    )
            except ValueError:
                pass

    for svc in binding_dict.get("target_services", []):
        svc_id = svc.get("target_service_id", "")
        svc_family = svc.get("target_service_family", "")
        if (
            svc_id in ("google_drive", "google_docs")
            and svc_family != TargetServiceFamily.GOOGLE_WORKSPACE.value
        ):
            result.errors.append(
                f"SERVICE_FAMILY_MISMATCH: {svc_id} requires google_workspace family, got {svc_family}"
            )

    for surf in binding_dict.get("execution_surfaces", []):
        surf_type = surf.get("execution_surface_type", "")
        surf_role = surf.get("execution_surface_role", "")
        try:
            st = ExecutionSurfaceType(surf_type)
            if (
                st in WSL_TMUX_SURFACE_TYPES
                and surf_role == ExecutionSurfaceRole.GUI_ACTUATOR.value
            ):
                result.errors.append(
                    f"WSL_TMUX_NOT_GUI_AUTHORITY: {surf_type} cannot be gui_actuator"
                )
        except ValueError:
            pass

    proof = binding_dict.get("proof", {})
    if proof:
        blocked = proof.get("blocked_evidence", [])
        allowed = proof.get("allowed_evidence", [])
        overlap = set(blocked) & set(allowed)
        if overlap:
            result.errors.append(
                f"PROOF_EVIDENCE_CONFLICT: {sorted(overlap)} in both allowed and blocked"
            )

    if not result.errors:
        result.valid = True

    return result


def _validate_environment(binding: ExecutionBinding, result: BindingValidationResult) -> None:
    env = binding.environment
    if not env.environment_id:
        result.errors.append("MISSING_ENVIRONMENT_ID: environment_id required")
    if not env.environment_type:
        result.errors.append("MISSING_ENVIRONMENT_TYPE: environment_type required")
    if not env.environment_authority:
        result.errors.append("MISSING_ENVIRONMENT_AUTHORITY: environment_authority required")


def _validate_execution_surfaces(
    binding: ExecutionBinding, result: BindingValidationResult
) -> None:
    if not binding.execution_surfaces:
        result.errors.append("MISSING_EXECUTION_SURFACES: at least one execution surface required")
        return

    for surf in binding.execution_surfaces:
        if not surf.execution_surface_id:
            result.errors.append("MISSING_EXECUTION_SURFACE_ID: execution_surface_id required")
        if not surf.execution_surface_type:
            result.errors.append("MISSING_EXECUTION_SURFACE_TYPE: execution_surface_type required")
        if not surf.execution_surface_role:
            result.errors.append("MISSING_EXECUTION_SURFACE_ROLE: execution_surface_role required")


def _validate_application(binding: ExecutionBinding, result: BindingValidationResult) -> None:
    app = binding.application
    if not app.application_id:
        result.errors.append("MISSING_APPLICATION_ID: application_id required")
    if not app.application_name:
        result.errors.append("MISSING_APPLICATION_NAME: application_name required")
    if not app.launch_method:
        result.errors.append("MISSING_LAUNCH_METHOD: launch_method required")


def _validate_target_services(binding: ExecutionBinding, result: BindingValidationResult) -> None:
    if not binding.target_services:
        result.errors.append("MISSING_TARGET_SERVICES: at least one target service required")
        return

    for svc in binding.target_services:
        if not svc.target_service_id:
            result.errors.append("MISSING_TARGET_SERVICE_ID: target_service_id required")
        if not svc.target_service_family:
            result.errors.append("MISSING_TARGET_SERVICE_FAMILY: target_service_family required")


def _validate_capabilities(binding: ExecutionBinding, result: BindingValidationResult) -> None:
    if not binding.capabilities:
        result.errors.append("MISSING_CAPABILITIES: at least one capability required")
        return

    for cap in binding.capabilities:
        if not cap.capability_id:
            result.errors.append("MISSING_CAPABILITY_ID: capability_id required")


def _validate_proof(binding: ExecutionBinding, result: BindingValidationResult) -> None:
    proof = binding.proof
    if not proof.proof_level_required:
        result.errors.append("MISSING_PROOF_LEVEL: proof_level_required required")
    if not proof.proof_source:
        result.errors.append("MISSING_PROOF_SOURCE: proof_source required")


def _validate_cross_layer_rules(binding: ExecutionBinding, result: BindingValidationResult) -> None:
    app = binding.application
    if app.launch_method:
        try:
            method = ApplicationLaunchMethod(app.launch_method)
            if method in DISALLOWED_CHROME_LAUNCH_METHODS:
                result.errors.append(
                    f"CHROME_LAUNCH_METHOD_BLOCKED: {app.launch_method} is not allowed"
                )
        except ValueError:
            pass

        if app.launch_method in [
            m.value for m in app.disallowed_launch_methods if isinstance(m, ApplicationLaunchMethod)
        ]:
            result.errors.append(
                f"LAUNCH_METHOD_IN_DISALLOWED: {app.launch_method} is in application's disallowed list"
            )
        if app.launch_method in app.disallowed_launch_methods:
            result.errors.append(
                f"LAUNCH_METHOD_IN_DISALLOWED: {app.launch_method} is in application's disallowed list"
            )

    for surf in binding.execution_surfaces:
        try:
            st = ExecutionSurfaceType(surf.execution_surface_type)
            if st in WSL_TMUX_SURFACE_TYPES:
                if surf.execution_surface_role == ExecutionSurfaceRole.GUI_ACTUATOR.value:
                    result.errors.append(
                        f"WSL_TMUX_NOT_GUI_AUTHORITY: {surf.execution_surface_type} "
                        f"cannot have role gui_actuator"
                    )
        except ValueError:
            pass

    for svc in binding.target_services:
        if svc.target_service_id in ("google_drive", "google_docs"):
            if svc.target_service_family != TargetServiceFamily.GOOGLE_WORKSPACE.value:
                result.errors.append(
                    f"SERVICE_FAMILY_MISMATCH: {svc.target_service_id} requires "
                    f"google_workspace family, got {svc.target_service_family}"
                )

    proof = binding.proof
    if proof.blocked_evidence and proof.allowed_evidence:
        overlap = set(proof.blocked_evidence) & set(proof.allowed_evidence)
        if overlap:
            result.errors.append(
                f"PROOF_EVIDENCE_CONFLICT: {sorted(overlap)} in both allowed and blocked"
            )

    if proof.proof_level_required == ProofLevel.FOUNDER_VISUAL_CONFIRMATION.value:
        if not proof.founder_confirmation_required:
            result.errors.append(
                "FOUNDER_CONFIRMATION_MISMATCH: proof_level requires founder confirmation "
                "but founder_confirmation_required is False"
            )
