"""
Visible GUI success criteria for Phase 94D.7S.

Defines what constitutes a successful visible GUI action.
Command exit code 0 alone is NOT sufficient for visible GUI success.

Key rule: A visible GUI action is not successful unless it appears
in the active user desktop session AND receives explicit founder
visual confirmation.
"""

from __future__ import annotations

from typing import Any


class VisibleGuiStatus:
    """Status constants for visible GUI actions."""

    ACTION_ATTEMPTED = "ACTION_ATTEMPTED"
    WAITING_FOR_FOUNDER_VISUAL_CONFIRMATION = "WAITING_FOR_FOUNDER_VISUAL_CONFIRMATION"
    CONFIRMED_VISIBLE = "CONFIRMED_VISIBLE"
    NOT_VISIBLE = "NOT_VISIBLE"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    WRONG_ACCOUNT = "WRONG_ACCOUNT"
    CANCEL = "CANCEL"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class LaunchContext:
    """Classification of the execution context for GUI launches."""

    NON_INTERACTIVE_WINDOWS_SSH = "NON_INTERACTIVE_WINDOWS_SSH_LAUNCH"
    INTERACTIVE_WINDOWS_DESKTOP = "INTERACTIVE_WINDOWS_DESKTOP_LAUNCH"
    INTERACTIVE_WSL_TERMINAL = "INTERACTIVE_WSL_TERMINAL_LAUNCH"
    UNKNOWN = "UNKNOWN_CONTEXT"


RELIABLE_CONTEXTS_FOR_VISIBLE_GUI: frozenset[str] = frozenset(
    {
        LaunchContext.INTERACTIVE_WINDOWS_DESKTOP,
        LaunchContext.INTERACTIVE_WSL_TERMINAL,
    }
)

UNRELIABLE_CONTEXTS_FOR_VISIBLE_GUI: frozenset[str] = frozenset(
    {
        LaunchContext.NON_INTERACTIVE_WINDOWS_SSH,
    }
)


def is_context_reliable_for_gui(context: str) -> bool:
    """Check if the execution context reliably shows GUI windows."""
    return context in RELIABLE_CONTEXTS_FOR_VISIBLE_GUI


def classify_ssh_launch_context() -> str:
    """SSH-based command execution is non-interactive on Windows."""
    return LaunchContext.NON_INTERACTIVE_WINDOWS_SSH


def is_exit_code_sufficient_for_visible_success() -> bool:
    """Command exit code 0 is NOT sufficient for visible GUI success."""
    return False


def build_action_attempted_status(
    action: str,
    backend: str,
    command_exit_code: int,
    launch_context: str,
    chrome_path: str | None = None,
) -> dict[str, Any]:
    """Build ACTION_ATTEMPTED status (not yet confirmed visible)."""
    return {
        "status": VisibleGuiStatus.ACTION_ATTEMPTED,
        "action": action,
        "backend": backend,
        "command_exit_code": command_exit_code,
        "launch_context": launch_context,
        "chrome_path": chrome_path,
        "visible_confirmed": False,
        "requires_founder_confirmation": True,
        "exit_code_sufficient_for_visible": False,
        "note": (
            "Command may have returned success but visible GUI confirmation is required. "
            "SSH-launched processes run in non-interactive context and may not appear "
            "on the active desktop session."
        ),
    }


def build_waiting_for_confirmation_message(
    work_order_id: str,
    action: str,
    target_account: str = "antonyfm@empyreanstudios.co",
) -> dict[str, Any]:
    """Build the WAITING_FOR_FOUNDER_VISUAL_CONFIRMATION message."""
    return {
        "message_type": "VISUAL_CONFIRMATION_NEEDED",
        "work_order_id": work_order_id,
        "sender": "node:local_pc_worker",
        "recipient": "advisor",
        "status": VisibleGuiStatus.WAITING_FOR_FOUNDER_VISUAL_CONFIRMATION,
        "payload": {
            "action": action,
            "target_account": target_account,
            "question": "Did Chrome visibly open Google Drive on the local PC?",
            "valid_responses": [
                VisibleGuiStatus.CONFIRMED_VISIBLE,
                VisibleGuiStatus.NOT_VISIBLE,
                VisibleGuiStatus.LOGIN_REQUIRED,
                VisibleGuiStatus.WRONG_ACCOUNT,
                VisibleGuiStatus.CANCEL,
            ],
            "instructions": (
                "Please look at the local PC screen. "
                "Is Chrome open with Google Drive loaded? "
                "Respond with one of the valid responses above."
            ),
        },
    }


def evaluate_founder_confirmation(
    confirmation: str,
) -> dict[str, Any]:
    """Evaluate the founder's visual confirmation response."""
    confirmation = confirmation.strip().upper()

    if confirmation == VisibleGuiStatus.CONFIRMED_VISIBLE:
        return {
            "visible_success": True,
            "status": VisibleGuiStatus.CONFIRMED_VISIBLE,
            "next_action": "PROCEED_TO_ACCOUNT_VERIFICATION",
            "blocks_automation": False,
        }

    if confirmation == VisibleGuiStatus.NOT_VISIBLE:
        return {
            "visible_success": False,
            "status": VisibleGuiStatus.FALSE_POSITIVE,
            "next_action": "RETRY_INTERACTIVE_LAUNCH",
            "blocks_automation": True,
            "reason": "Command reported success but Chrome not visible on desktop",
        }

    if confirmation == VisibleGuiStatus.LOGIN_REQUIRED:
        return {
            "visible_success": True,
            "status": VisibleGuiStatus.LOGIN_REQUIRED,
            "next_action": "LOGIN_REQUIRED_MANUAL_INTERVENTION",
            "blocks_automation": True,
            "reason": "Chrome opened but login is required. Founder must log in manually.",
        }

    if confirmation == VisibleGuiStatus.WRONG_ACCOUNT:
        return {
            "visible_success": True,
            "status": VisibleGuiStatus.WRONG_ACCOUNT,
            "next_action": "WRONG_ACCOUNT_PAUSE",
            "blocks_automation": True,
            "reason": "Chrome opened but wrong account is active.",
        }

    if confirmation == VisibleGuiStatus.CANCEL:
        return {
            "visible_success": False,
            "status": VisibleGuiStatus.CANCEL,
            "next_action": "CANCEL_TEST",
            "blocks_automation": True,
        }

    return {
        "visible_success": False,
        "status": "UNKNOWN_RESPONSE",
        "next_action": "ASK_AGAIN",
        "blocks_automation": True,
        "reason": f"Unrecognized response: {confirmation}",
    }


def demote_ssh_launch_to_attempted(
    previous_result: dict[str, Any],
) -> dict[str, Any]:
    """Demote a previous SSH launch 'success' to ACTION_ATTEMPTED.

    Used to correct false positives from 94D.7R.
    """
    return {
        "original_result": previous_result,
        "corrected_status": VisibleGuiStatus.ACTION_ATTEMPTED,
        "reason": "SSH-launched commands run in non-interactive Windows session. "
        "Exit code 0 does not guarantee Chrome appeared on active desktop.",
        "launch_context": LaunchContext.NON_INTERACTIVE_WINDOWS_SSH,
        "visible_confirmed": False,
        "correction_phase": "94D.7S",
    }
