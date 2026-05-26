"""Windows Interactive Desktop Adapter Validator.

Validates action requests before they are written to the relay inbox.
Rejects requests with wrong environment, wrong execution surface role,
disallowed launch methods, missing proof contracts, or missing trace_id.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .windows_desktop_adapter_contracts import (
    BLOCKED_LAUNCH_METHODS,
    WindowsDesktopActionRequest,
    WindowsDesktopActionType,
)


@dataclass
class AdapterValidationResult:
    valid: bool = False
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


def validate_desktop_action_request(
    request: WindowsDesktopActionRequest,
) -> AdapterValidationResult:
    """Validate a Windows desktop action request."""
    result = AdapterValidationResult()

    if not request.request_id:
        result.errors.append("MISSING_REQUEST_ID")

    if not request.trace_id:
        result.errors.append("MISSING_TRACE_ID")

    if not request.action_type:
        result.errors.append("MISSING_ACTION_TYPE")
    else:
        try:
            WindowsDesktopActionType(request.action_type)
        except ValueError:
            result.errors.append(f"UNKNOWN_ACTION_TYPE: {request.action_type}")

    if request.environment_id != "local_windows_desktop":
        result.errors.append(
            f"WRONG_ENVIRONMENT: expected local_windows_desktop, got {request.environment_id}"
        )

    if request.execution_surface_id not in (
        "windows_interactive_desktop_adapter",
        "windows_powershell_relay",
    ):
        result.errors.append(
            f"WRONG_EXECUTION_SURFACE: {request.execution_surface_id} is not a valid Windows GUI actuator"
        )

    if request.action_type == WindowsDesktopActionType.OPEN_APPLICATION_URL.value:
        _validate_open_url_request(request, result)

    if not request.proof_required:
        result.errors.append("MISSING_PROOF_CONTRACT: proof_required must be set")

    if not result.errors:
        result.valid = True

    return result


def validate_desktop_action_request_dict(
    request_dict: dict[str, Any],
) -> AdapterValidationResult:
    """Validate from dict form."""
    result = AdapterValidationResult()

    if not request_dict.get("request_id"):
        result.errors.append("MISSING_REQUEST_ID")

    if not request_dict.get("trace_id"):
        result.errors.append("MISSING_TRACE_ID")

    action_type = request_dict.get("action_type", "")
    if not action_type:
        result.errors.append("MISSING_ACTION_TYPE")

    env = request_dict.get("environment_id", "")
    if env != "local_windows_desktop":
        result.errors.append(f"WRONG_ENVIRONMENT: expected local_windows_desktop, got {env}")

    surface = request_dict.get("execution_surface_id", "")
    if surface not in (
        "windows_interactive_desktop_adapter",
        "windows_powershell_relay",
    ):
        result.errors.append(f"WRONG_EXECUTION_SURFACE: {surface}")

    if action_type == WindowsDesktopActionType.OPEN_APPLICATION_URL.value:
        app_id = request_dict.get("application_id", "")
        if app_id != "google_chrome_windows":
            result.errors.append(
                f"WRONG_APPLICATION: expected google_chrome_windows for Chrome actions, got {app_id}"
            )

        launch = request_dict.get("launch_method", "")
        if launch != "direct_executable":
            result.errors.append(f"WRONG_LAUNCH_METHOD: expected direct_executable, got {launch}")

        blocked = request_dict.get("blocked_launch_methods", [])
        if launch in blocked:
            result.errors.append(f"LAUNCH_METHOD_IN_BLOCKED: {launch}")

        for method in BLOCKED_LAUNCH_METHODS:
            if method not in blocked:
                result.errors.append(
                    f"MISSING_BLOCKED_METHOD: {method} must be in blocked_launch_methods"
                )

        if not request_dict.get("url"):
            result.errors.append("MISSING_URL: url required for open_application_url")

    if not request_dict.get("proof_required"):
        result.errors.append("MISSING_PROOF_CONTRACT")

    if not result.errors:
        result.valid = True

    return result


def _validate_open_url_request(
    request: WindowsDesktopActionRequest,
    result: AdapterValidationResult,
) -> None:
    """Validate OPEN_APPLICATION_URL-specific fields."""
    if request.application_id != "google_chrome_windows":
        result.errors.append(
            f"WRONG_APPLICATION: expected google_chrome_windows for Chrome actions, got {request.application_id}"
        )

    if request.launch_method != "direct_executable":
        result.errors.append(
            f"WRONG_LAUNCH_METHOD: expected direct_executable, got {request.launch_method}"
        )

    if request.launch_method in request.blocked_launch_methods:
        result.errors.append(f"LAUNCH_METHOD_IN_BLOCKED: {request.launch_method}")

    for method in BLOCKED_LAUNCH_METHODS:
        if method not in request.blocked_launch_methods:
            result.errors.append(
                f"MISSING_BLOCKED_METHOD: {method} must be in blocked_launch_methods"
            )

    if not request.url:
        result.errors.append("MISSING_URL: url required for open_application_url")
