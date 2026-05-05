"""
Interactive shell executor for Phase 94D.8.

Routes approved actions through an interactive tmux shell environment
on the local PC. Dispatches commands via tmux send-keys so they
execute within the user's interactive session.

Key rules:
- Command dispatch success ≠ visible GUI success.
- Status after dispatch: WAITING_FOR_FOUNDER_VISUAL_CONFIRMATION.
- Only founder confirmation or approved observation backend proves visibility.
- No Playwright. No credential capture. No silent fallback.
"""

from __future__ import annotations

from typing import Any

from eos_ai.substrate.visible_gui_success_criteria import VisibleGuiStatus


CHROME_PATH_CONFIRMED = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DRIVE_URL = "https://drive.google.com/"
WO_001_ID = "WO-LOCAL-PILOT-GDRIVE-GDOCS-001"
WO_001_ACCOUNT = "antonyfm@empyreanstudios.co"


def build_open_drive_in_chrome_script() -> str:
    """Build the shell script content for opening Drive in Chrome.

    This script is written to a file on the local PC and then
    executed via tmux send-keys from an interactive shell.
    """
    return (
        '#!/bin/bash\n'
        '# Phase 94D.8: Open Google Drive in Chrome (interactive session)\n'
        '# This must run from an interactive terminal/tmux pane.\n'
        'powershell.exe -NoProfile -Command "'
        "Start-Process -FilePath "
        f"'{CHROME_PATH_CONFIRMED}' "
        f"-ArgumentList '{DRIVE_URL}'"
        '"\n'
        'echo "CHROME_LAUNCH_ATTEMPTED: exit_code=$?"\n'
    )


def build_send_open_drive_to_tmux_command(tmux_target: str) -> str:
    """Build the full command to send the Chrome launch into a tmux pane.

    Uses 'bash ~/umh_local_worker/open_drive_chrome.sh' as the dispatched command.
    """
    from eos_ai.substrate.tmux_environment_manager import build_tmux_send_keys_command

    return build_tmux_send_keys_command(
        target=tmux_target,
        command="bash ~/umh_local_worker/open_drive_chrome.sh",
    )


def build_founder_confirmation_prompt() -> dict[str, Any]:
    """Build the prompt for founder visual confirmation."""
    return {
        "message_type": "VISUAL_CONFIRMATION_NEEDED",
        "work_order_id": WO_001_ID,
        "question": "Did Chrome visibly open Google Drive on the local PC?",
        "valid_responses": [
            VisibleGuiStatus.CONFIRMED_VISIBLE,
            VisibleGuiStatus.NOT_VISIBLE,
            VisibleGuiStatus.LOGIN_REQUIRED,
            VisibleGuiStatus.WRONG_ACCOUNT,
            VisibleGuiStatus.CANCEL,
        ],
        "context": (
            "A command was sent into an interactive tmux shell pane to launch "
            "Chrome with Google Drive. Please look at the local PC screen and "
            "report what you see."
        ),
        "do_not": [
            "Do not type credentials",
            "Do not capture/screenshot without separate approval",
            "Do not switch accounts",
            "Do not open documents or folders",
        ],
    }


def classify_visual_confirmation_response(response: str) -> dict[str, Any]:
    """Classify the founder's visual confirmation response.

    Returns action/status dict based on response.
    """
    response = response.strip().upper()

    if response == VisibleGuiStatus.CONFIRMED_VISIBLE:
        return {
            "visible_success": True,
            "status": VisibleGuiStatus.CONFIRMED_VISIBLE,
            "next_gate": "VERIFY_ACTIVE_GOOGLE_ACCOUNT",
            "blocks_automation": False,
        }

    if response == VisibleGuiStatus.NOT_VISIBLE:
        return {
            "visible_success": False,
            "status": "FALSE_POSITIVE",
            "next_gate": None,
            "blocks_automation": True,
            "next_action": "MARK_ENVIRONMENT_NOT_GUI_CAPABLE",
        }

    if response == VisibleGuiStatus.LOGIN_REQUIRED:
        return {
            "visible_success": True,
            "status": VisibleGuiStatus.LOGIN_REQUIRED,
            "next_gate": "LOGIN_REQUIRED_MANUAL_INTERVENTION",
            "blocks_automation": True,
            "credential_capture_allowed": False,
        }

    if response == VisibleGuiStatus.WRONG_ACCOUNT:
        return {
            "visible_success": True,
            "status": VisibleGuiStatus.WRONG_ACCOUNT,
            "next_gate": "WRONG_ACCOUNT_PAUSE",
            "blocks_automation": True,
            "account_switching_allowed": False,
        }

    if response == VisibleGuiStatus.CANCEL:
        return {
            "visible_success": False,
            "status": VisibleGuiStatus.CANCEL,
            "next_gate": None,
            "blocks_automation": True,
        }

    return {
        "visible_success": False,
        "status": "UNKNOWN_RESPONSE",
        "next_gate": None,
        "blocks_automation": True,
    }


def visible_success_requires_confirmation() -> bool:
    """Visible success always requires founder confirmation."""
    return True


def build_next_gate_message(
    confirmation: str,
    work_order_id: str = WO_001_ID,
    target_account: str = WO_001_ACCOUNT,
) -> dict[str, Any] | None:
    """Build the appropriate next gate message based on confirmation."""
    result = classify_visual_confirmation_response(confirmation)

    if not result.get("next_gate"):
        return None

    gate_action = result["next_gate"]

    descriptions = {
        "VERIFY_ACTIVE_GOOGLE_ACCOUNT": (
            f"Chrome opened Google Drive visibly. Verify active account is {target_account}."
        ),
        "LOGIN_REQUIRED_MANUAL_INTERVENTION": (
            f"Chrome opened but login is required for {target_account}. "
            "Please log in manually. Worker will NOT capture credentials."
        ),
        "WRONG_ACCOUNT_PAUSE": (
            f"Chrome opened but wrong account is active. Target is {target_account}. "
            "Do NOT switch accounts automatically."
        ),
    }

    return {
        "message_type": "APPROVAL_NEEDED",
        "work_order_id": work_order_id,
        "sender": "node:local_pc_worker",
        "recipient": "advisor",
        "priority": "HIGH",
        "requires_response": True,
        "payload": {
            "action": gate_action,
            "target": target_account,
            "description": descriptions.get(gate_action, gate_action),
            "risk_level": "LOW",
            "backend": "HUMAN_VISUAL_CONFIRMATION",
            "blocked_until_approved": True,
        },
    }
