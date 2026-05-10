"""
Interactive GUI worker contracts for Phase 94D.7S.

Defines the contract between VPS advisor and the local interactive GUI worker
that runs in the founder's active Windows desktop session.

Key constraint: SSH-launched commands run in a non-interactive service session
and cannot reliably display GUI windows. The interactive worker must be
started by the user in their active desktop session.

Acceptable MVP paths for starting the interactive worker:
A. Founder runs worker script from a local terminal (VS Code, Windows Terminal, WSL)
B. Windows Task Scheduler starts worker at user logon
C. Local desktop daemon started at login
D. Existing Claude/worker terminal acts as the interactive GUI worker

For Phase 94D.7S: Path A (manual start from local terminal).
"""

from __future__ import annotations

from typing import Any

from eos_ai.transport.visible_gui_success_criteria import (
    LaunchContext,
    VisibleGuiStatus,
)


INTERACTIVE_WORKER_VERSION = "94D.7S"

WO_001_ID = "WO-LOCAL-PILOT-GDRIVE-GDOCS-001"
WO_001_ACCOUNT = "antonyfm@empyreanstudios.co"

CHROME_PATH_CONFIRMED = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DRIVE_URL = "https://drive.google.com/"


def build_interactive_chrome_launch_command(
    url: str = DRIVE_URL,
    chrome_path: str = CHROME_PATH_CONFIRMED,
) -> str:
    """Build the PowerShell command for interactive Chrome launch.

    This command must be run from an interactive Windows session,
    NOT via SSH from the VPS.
    """
    return (
        f"powershell.exe -NoProfile -Command \""
        f"Start-Process -FilePath '{chrome_path}' "
        f"-ArgumentList '{url}'\""
    )


def build_interactive_launch_intent(
    work_order_id: str = WO_001_ID,
    target_account: str = WO_001_ACCOUNT,
) -> dict[str, Any]:
    """Build the intent message that the VPS sends to the local worker.

    The local interactive worker reads this and executes the Chrome launch
    from its interactive desktop context.
    """
    return {
        "message_type": "LAUNCH_INTENT",
        "work_order_id": work_order_id,
        "action": "OPEN_GOOGLE_DRIVE",
        "url": DRIVE_URL,
        "chrome_path": CHROME_PATH_CONFIRMED,
        "target_account": target_account,
        "backend": "VISIBLE_CHROME_LAUNCH",
        "launch_context_required": LaunchContext.INTERACTIVE_WINDOWS_DESKTOP,
        "command": build_interactive_chrome_launch_command(),
        "success_criteria": {
            "exit_code_sufficient": False,
            "requires_founder_visual_confirmation": True,
            "valid_confirmations": [
                VisibleGuiStatus.CONFIRMED_VISIBLE,
                VisibleGuiStatus.NOT_VISIBLE,
                VisibleGuiStatus.LOGIN_REQUIRED,
                VisibleGuiStatus.WRONG_ACCOUNT,
                VisibleGuiStatus.CANCEL,
            ],
        },
        "notes": [
            "Must run from interactive Windows desktop session",
            "SSH execution is non-interactive and unreliable for GUI",
            "Do not mark success until founder confirms visibility",
        ],
    }


def build_action_attempted_outbox(
    work_order_id: str = WO_001_ID,
    command_exit_code: int = 0,
    launch_context: str = LaunchContext.INTERACTIVE_WINDOWS_DESKTOP,
    chrome_path: str = CHROME_PATH_CONFIRMED,
) -> dict[str, Any]:
    """Build the ACTION_ATTEMPTED outbox message.

    Written by the interactive worker AFTER running the command.
    Does NOT claim visible success — waits for founder confirmation.
    """
    return {
        "message_type": "ACTION_ATTEMPTED",
        "work_order_id": work_order_id,
        "sender": "node:local_pc_interactive_worker",
        "recipient": "advisor",
        "payload": {
            "action": "OPEN_GOOGLE_DRIVE",
            "backend": "VISIBLE_CHROME_LAUNCH",
            "chrome_path": chrome_path,
            "command_exit_code": command_exit_code,
            "launch_context": launch_context,
            "visible_confirmed": False,
            "status": VisibleGuiStatus.ACTION_ATTEMPTED,
            "awaiting": VisibleGuiStatus.WAITING_FOR_FOUNDER_VISUAL_CONFIRMATION,
        },
    }


def build_visible_confirmed_outbox(
    work_order_id: str = WO_001_ID,
    confirmation: str = VisibleGuiStatus.CONFIRMED_VISIBLE,
) -> dict[str, Any]:
    """Build the outbox message AFTER founder confirms visibility."""
    return {
        "message_type": "ACTION_EXECUTED_VISIBLE",
        "work_order_id": work_order_id,
        "sender": "node:local_pc_interactive_worker",
        "recipient": "advisor",
        "payload": {
            "action": "OPEN_GOOGLE_DRIVE",
            "backend": "VISIBLE_CHROME_LAUNCH",
            "visible_confirmed": True,
            "confirmation": confirmation,
            "launch_context": LaunchContext.INTERACTIVE_WINDOWS_DESKTOP,
        },
    }


def get_recommended_mvp_path() -> dict[str, Any]:
    """Return the recommended MVP path for the interactive GUI worker."""
    return {
        "recommended": "A",
        "description": "Founder starts worker from local terminal",
        "steps": [
            "1. Open Windows Terminal / VS Code terminal / WSL terminal on local PC",
            "2. Navigate to ~/umh_local_worker/",
            "3. Run: python3 local_worker_auto_loop.py ~/eos_advisor_messages/wo_001_relay_packet.json",
            "4. Worker reads pending launch intent from inbox",
            "5. Worker executes Chrome launch in THIS interactive session",
            "6. Worker writes ACTION_ATTEMPTED to outbox",
            "7. Worker waits for founder visual confirmation via advisor",
        ],
        "why_this_works": (
            "A terminal opened by the logged-in user runs in Session 1 (interactive desktop). "
            "Processes launched from this context inherit the desktop session and can display "
            "GUI windows visibly. SSH runs in Session 0 (service) which cannot."
        ),
        "alternatives": [
            "B: Windows Task Scheduler at user logon (more automated, same session)",
            "C: Desktop daemon (more complex, same result)",
            "D: Existing terminal (simplest if one is already open)",
        ],
    }


def classify_current_ssh_path() -> dict[str, Any]:
    """Classify the current SSH-based execution path correctly."""
    return {
        "classification": LaunchContext.NON_INTERACTIVE_WINDOWS_SSH,
        "reliable_for_gui": False,
        "reliable_for_commands": True,
        "reason": (
            "Windows OpenSSH server runs in Session 0 (SYSTEM/service context). "
            "Commands executed via SSH inherit this non-interactive session. "
            "PowerShell Start-Process may return exit code 0 but the launched "
            "process is invisible to the user logged into the desktop (Session 1). "
            "This is a Windows session isolation feature, not a bug."
        ),
        "allowed_uses": [
            "File operations (read/write/delete)",
            "Process queries (tasklist, Get-Process)",
            "System information",
            "Non-GUI commands",
            "Writing intent files for interactive worker to consume",
        ],
        "not_allowed_for": [
            "Visible browser launch",
            "Any GUI window display",
            "Screenshot (cannot see interactive desktop)",
            "Mouse/keyboard automation",
        ],
    }
