"""
Windows user-session launcher for Phase 94D.8B.

Uses Windows Task Scheduler to execute commands in the interactive
user desktop session. This is the correct way to launch visible GUI
applications from a remote/service context on Windows.

The /IT flag on schtasks forces the task to run only when the user is
logged in AND in the interactive (desktop) session.

Key facts:
- SSH runs in Session 0 (service) — GUI invisible
- Task Scheduler with /IT runs in user's Session 1+ — GUI visible
- This is Microsoft's documented solution for this exact problem

No Playwright. No credential capture. No Gmail.
"""

from __future__ import annotations

import os
from typing import Any


CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DRIVE_URL = "https://drive.google.com/"
TASK_NAME = "UMH_ChromeDriveLaunch"
WO_001_ID = "WO-LOCAL-PILOT-GDRIVE-GDOCS-001"

SSH_KEY = "/root/.ssh/id_ed25519"
SSH_USER = r"DESKTOP-LVGUIQ9\antonys beast pc"
SSH_HOST = os.getenv("EOS_LOCAL_BRIDGE_IP", "100.74.199.102")


def build_create_scheduled_task_command(
    task_name: str = TASK_NAME,
    chrome_path: str = CHROME_PATH,
    url: str = DRIVE_URL,
) -> str:
    """Build the schtasks command to create an interactive user-session task.

    /IT = run only when user is logged on interactively
    /RL HIGHEST = run with highest available privileges
    /SC ONCE /ST 00:00 = one-time trigger (we'll run it manually)
    /F = force create (overwrite if exists)
    """
    return (
        f'schtasks /create /tn "{task_name}" '
        f'/tr "\\"{chrome_path}\\" {url}" '
        f"/sc once /st 00:00 /f /rl highest /it"
    )


def build_run_scheduled_task_command(task_name: str = TASK_NAME) -> str:
    """Build the schtasks command to run the task immediately."""
    return f'schtasks /run /tn "{task_name}"'


def build_delete_scheduled_task_command(task_name: str = TASK_NAME) -> str:
    """Build the schtasks command to clean up the task after use."""
    return f'schtasks /delete /tn "{task_name}" /f'


def build_query_scheduled_task_command(task_name: str = TASK_NAME) -> str:
    """Build command to check task status."""
    return f'schtasks /query /tn "{task_name}" /fo list'


def build_full_launch_sequence() -> list[str]:
    """Build the complete sequence of commands for Chrome launch via Task Scheduler.

    Returns list of commands to execute in order via SSH.
    """
    return [
        build_create_scheduled_task_command(),
        build_run_scheduled_task_command(),
    ]


def build_cleanup_command() -> str:
    """Build cleanup command to remove the task after test."""
    return build_delete_scheduled_task_command()


def build_ssh_create_and_run_command() -> str:
    """Build the full SSH command that creates and runs the scheduled task.

    This is the single command the VPS sends to the local PC.
    Creates the task, then immediately runs it.
    """
    create_cmd = build_create_scheduled_task_command()
    run_cmd = build_run_scheduled_task_command()
    return (
        f"ssh -i {SSH_KEY} -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=8 "
        f"'{SSH_USER}'@{SSH_HOST} "
        f"'{create_cmd} && {run_cmd}'"
    )


def build_ssh_cleanup_command() -> str:
    """Build the SSH command to delete the scheduled task."""
    delete_cmd = build_delete_scheduled_task_command()
    return (
        f"ssh -i {SSH_KEY} -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=8 "
        f"'{SSH_USER}'@{SSH_HOST} "
        f"'{delete_cmd}'"
    )


def classify_launch_context() -> str:
    """Classify this launch method."""
    return "WINDOWS_TASK_SCHEDULER_INTERACTIVE"


def build_action_attempted_message(
    exit_code: int,
    task_output: str = "",
) -> dict[str, Any]:
    """Build ACTION_ATTEMPTED message after task scheduler execution."""
    return {
        "message_type": "ACTION_ATTEMPTED",
        "work_order_id": WO_001_ID,
        "sender": "node:vps_orchestrator",
        "recipient": "advisor",
        "payload": {
            "action": "OPEN_GOOGLE_DRIVE",
            "backend": "VISIBLE_CHROME_LAUNCH",
            "launch_method": "WINDOWS_TASK_SCHEDULER_INTERACTIVE",
            "task_name": TASK_NAME,
            "chrome_path": CHROME_PATH,
            "url": DRIVE_URL,
            "command_exit_code": exit_code,
            "task_output": task_output,
            "visible_confirmed": False,
            "status": "WAITING_FOR_FOUNDER_VISUAL_CONFIRMATION",
            "why_this_method": (
                "SSH direct = Session 0 (invisible). "
                "SSH tmux = no interop socket. "
                "Task Scheduler /IT = runs in interactive user session."
            ),
            "demoted_paths": [
                "NON_INTERACTIVE_WINDOWS_SSH_LAUNCH",
                "SSH_ORIGINATED_TMUX_LAUNCH",
            ],
        },
    }


def get_why_task_scheduler() -> str:
    """Explain why Task Scheduler is the correct path."""
    return (
        "Windows Task Scheduler with the /IT flag is Microsoft's documented "
        "solution for launching GUI applications from a service/remote context. "
        "The /IT flag ensures the task runs ONLY when the user is interactively "
        "logged in, and it runs in the user's desktop session (Session 1+), "
        "not the service session (Session 0). This is the correct answer to "
        "'how do I open a visible window from SSH on Windows.'"
    )
