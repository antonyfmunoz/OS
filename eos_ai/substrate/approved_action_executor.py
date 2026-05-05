"""
Approved action executor for Phase 94D.7R.

Validates advisor approval responses and dispatches only the single
named approved action. Rejects anything not explicitly approved.

Supported actions for this phase: OPEN_GOOGLE_DRIVE only.
Preferred backend for W0-001: VISIBLE_CHROME_LAUNCH.

No Playwright. No scraping. No Gmail. No account switching.
No document access. No export/download. No credential capture.
No silent fallback to Explorer/default browser.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


WO_001_ID = "WO-LOCAL-PILOT-GDRIVE-GDOCS-001"
WO_001_ACCOUNT = "antonyfm@empyreanstudios.co"
WO_001_PREFERRED_BACKEND = "VISIBLE_CHROME_LAUNCH"

SUPPORTED_ACTIONS: frozenset[str] = frozenset({"OPEN_GOOGLE_DRIVE"})

BLOCKED_ACTIONS: frozenset[str] = frozenset(
    {
        "OPEN_GMAIL",
        "SWITCH_ACCOUNT",
        "OPEN_DOCUMENT",
        "EXPORT_DOCUMENT",
        "DOWNLOAD_FILE",
        "EDIT_DOCUMENT",
        "DELETE_FILE",
        "MOVE_FILE",
        "SHARE_FILE",
        "CHANGE_PERMISSIONS",
        "CAPTURE_CREDENTIALS",
        "SCREENSHOT",
        "PROMOTE_MEMORY",
        "RUN_PLAYWRIGHT",
    }
)

ACTION_BACKEND_MAP: dict[str, str] = {
    "OPEN_GOOGLE_DRIVE": "VISIBLE_CHROME_LAUNCH",
}


def normalize_decision(decision: str) -> str:
    """Normalize APPROVED/APPROVE variants."""
    normalized = decision.strip().upper()
    if normalized == "APPROVED":
        return "APPROVE"
    return normalized


def extract_approved_action(response: dict[str, Any]) -> str:
    """Extract the approved action from an advisor response."""
    action = response.get("payload", {}).get("approved_action", "")
    if not action:
        action = response.get("approved_action", "")
    return action.strip().upper()


def extract_decision(response: dict[str, Any]) -> str:
    """Extract and normalize decision from response."""
    decision = response.get("payload", {}).get("decision", "")
    if not decision:
        decision = response.get("decision", "")
    return normalize_decision(decision)


def extract_work_order_id(response: dict[str, Any]) -> str:
    """Extract work order ID from response."""
    return response.get("work_order_id", "")


def get_preferred_backend(action: str) -> str:
    """Get the preferred backend for an action."""
    return ACTION_BACKEND_MAP.get(action.strip().upper(), "UNKNOWN")


def validate_approval_for_action(
    response: dict[str, Any],
    expected_action: str,
    expected_work_order_id: str = WO_001_ID,
) -> list[str]:
    """Validate that the approval response authorizes the expected action.

    Returns list of errors. Empty list = valid.
    """
    errors: list[str] = []

    wo_id = extract_work_order_id(response)
    if wo_id != expected_work_order_id:
        errors.append(f"Wrong work_order_id: {wo_id}")

    decision = extract_decision(response)
    if decision != "APPROVE":
        errors.append(f"Decision is not APPROVE: {decision}")

    approved_action = extract_approved_action(response)
    if approved_action and approved_action != expected_action.upper():
        errors.append(
            f"Approved action mismatch: approved={approved_action}, expected={expected_action}"
        )

    if expected_action.upper() in BLOCKED_ACTIONS:
        errors.append(f"Action is permanently blocked: {expected_action}")

    if expected_action.upper() not in SUPPORTED_ACTIONS:
        errors.append(f"Action not supported in this phase: {expected_action}")

    return errors


def is_action_blocked(action: str) -> bool:
    """Check if an action is permanently blocked."""
    return action.strip().upper() in BLOCKED_ACTIONS


def is_action_supported(action: str) -> bool:
    """Check if an action is supported in this phase."""
    return action.strip().upper() in SUPPORTED_ACTIONS


def build_action_executed_result(
    work_order_id: str,
    action: str,
    backend: str,
    success: bool,
    detail: str = "",
    target_account: str = WO_001_ACCOUNT,
    chrome_path: str | None = None,
) -> dict[str, Any]:
    """Build an ACTION_EXECUTED result message for the outbox."""
    payload: dict[str, Any] = {
        "action": action,
        "backend": backend,
        "success": success,
        "detail": detail,
        "target_account": target_account,
    }
    if chrome_path:
        payload["chrome_path"] = chrome_path
    return {
        "message_type": "ACTION_EXECUTED",
        "work_order_id": work_order_id,
        "sender": "node:local_pc_worker",
        "recipient": "advisor",
        "timestamp": _now_iso(),
        "payload": payload,
    }


def build_backend_missing_result(
    work_order_id: str,
    action: str,
    reason: str,
) -> dict[str, Any]:
    """Build a BACKEND_MISSING result when Chrome is not found."""
    return {
        "message_type": "BACKEND_MISSING",
        "work_order_id": work_order_id,
        "sender": "node:local_pc_worker",
        "recipient": "advisor",
        "timestamp": _now_iso(),
        "payload": {
            "action": action,
            "preferred_backend": WO_001_PREFERRED_BACKEND,
            "reason": reason,
            "silent_fallback_allowed": False,
            "fallback_options": [
                "A: LOCATE_CHROME_MANUALLY",
                "B: APPROVE_DEFAULT_BROWSER_FALLBACK",
                "C: APPROVE_EDGE_FALLBACK",
                "D: APPROVE_PLAYWRIGHT_FALLBACK",
                "E: CANCEL_TEST",
            ],
        },
    }


def build_next_gate_request(
    work_order_id: str,
    gate_action: str,
    description: str,
    target_account: str = WO_001_ACCOUNT,
    possible_states: list[str] | None = None,
) -> dict[str, Any]:
    """Build a NEXT_GATE_REQUIRED approval request."""
    payload: dict[str, Any] = {
        "approval_request_id": f"apr_next_gate_{int(time.time())}",
        "work_order_id": work_order_id,
        "node_id": "local_pc_worker",
        "action": gate_action,
        "target": target_account,
        "description": description,
        "risk_level": "LOW",
        "backend": "HUMAN_VISUAL_CONFIRMATION",
        "blocked_until_approved": True,
    }
    if possible_states:
        payload["possible_states"] = possible_states
    return {
        "message_type": "APPROVAL_NEEDED",
        "work_order_id": work_order_id,
        "sender": "node:local_pc_worker",
        "recipient": "advisor",
        "timestamp": _now_iso(),
        "priority": "HIGH",
        "requires_response": True,
        "payload": payload,
    }


def build_login_required_gate(
    work_order_id: str,
    target_account: str = WO_001_ACCOUNT,
) -> dict[str, Any]:
    """Build a LOGIN_REQUIRED_MANUAL_INTERVENTION gate request."""
    return build_next_gate_request(
        work_order_id=work_order_id,
        gate_action="LOGIN_REQUIRED_MANUAL_INTERVENTION",
        description=(
            f"Google Drive requires login for {target_account}. "
            "Please log in manually on the local PC. "
            "Worker will NOT type, capture, store, or observe credentials. "
            "Confirm when login is complete."
        ),
        target_account=target_account,
        possible_states=[
            "LOGIN_REQUIRED_MANUAL_INTERVENTION",
            "WRONG_ACCOUNT_PAUSE",
            "CORRECT_ACCOUNT_CONFIRMED",
            "UNKNOWN_VISUAL_STATE",
        ],
    )


def execute_approved_action(
    response: dict[str, Any],
    action: str,
    executor_fn: Any = None,
    work_order_id: str = WO_001_ID,
) -> dict[str, Any]:
    """Execute a single approved action after full validation.

    Returns a result dict with success/failure and messages to write.
    """
    result: dict[str, Any] = {
        "action": action,
        "validated": False,
        "executed": False,
        "success": False,
        "error": None,
        "messages_to_write": [],
    }

    errors = validate_approval_for_action(response, action, work_order_id)
    if errors:
        result["error"] = f"Validation failed: {errors}"
        return result
    result["validated"] = True

    if executor_fn is not None:
        try:
            exec_result = executor_fn()
            result["executed"] = True
            result["success"] = exec_result.get("success", False)
            result["detail"] = exec_result.get("detail", "")
            result["backend"] = exec_result.get("backend", "UNKNOWN")
            result["chrome_path"] = exec_result.get("chrome_path")

            if exec_result.get("detail") == "CHROME_NOT_FOUND":
                result["success"] = False
                result["backend_missing"] = True
                backend_msg = build_backend_missing_result(
                    work_order_id=work_order_id,
                    action=action,
                    reason="Chrome executable not found",
                )
                result["messages_to_write"].append(
                    (f"backend_missing_{work_order_id}.json", backend_msg)
                )
                result["error"] = "CHROME_NOT_FOUND — no silent fallback allowed"
                return result

        except Exception as e:
            result["executed"] = True
            result["success"] = False
            result["error"] = f"Execution failed: {e}"
            return result
    else:
        result["executed"] = False
        result["error"] = "No executor function provided"
        return result

    action_msg = build_action_executed_result(
        work_order_id=work_order_id,
        action=action,
        backend=result.get("backend", "UNKNOWN"),
        success=result["success"],
        detail=result.get("detail", ""),
        chrome_path=result.get("chrome_path"),
    )
    result["messages_to_write"].append((f"action_result_{work_order_id}.json", action_msg))

    if result["success"] and action == "OPEN_GOOGLE_DRIVE":
        next_gate = build_next_gate_request(
            work_order_id=work_order_id,
            gate_action="VERIFY_ACTIVE_GOOGLE_ACCOUNT",
            description=(
                f"Verify active Google account is {WO_001_ACCOUNT}. "
                "Visual confirmation required — is the correct account active in Chrome? "
                "If login required, respond with LOGIN_REQUIRED_MANUAL_INTERVENTION. "
                "If wrong account, respond with WRONG_ACCOUNT_PAUSE."
            ),
            possible_states=[
                "DRIVE_OPEN_ACCOUNT_VISIBLE",
                "LOGIN_REQUIRED_MANUAL_INTERVENTION",
                "WRONG_ACCOUNT_PAUSE",
                "CORRECT_ACCOUNT_CONFIRMED",
                "UNKNOWN_VISUAL_STATE",
            ],
        )
        result["messages_to_write"].append((f"next_gate_{work_order_id}.json", next_gate))
        result["next_gate"] = "VERIFY_ACTIVE_GOOGLE_ACCOUNT"

    return result
