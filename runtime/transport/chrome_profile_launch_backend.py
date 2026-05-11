"""
Chrome profile launch backend for Phase 94D.9.

Launches Google Drive in a specific Chrome profile using the
--profile-directory flag. Uses the proven Task Scheduler /IT path
for visible desktop execution.

Backend class: VISIBLE_CHROME_PROFILE_LAUNCH
Not: Playwright, Explorer/default, account-switching UI.

No credential capture. No cookies. No Gmail.
"""

from __future__ import annotations

import os
from typing import Any


BACKEND_CLASS = "VISIBLE_CHROME_PROFILE_LAUNCH"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DRIVE_URL = "https://drive.google.com/"
TASK_NAME_PREFIX = "UMH_ChromeProfileLaunch"

WO_001_ID = "WO-LOCAL-PILOT-GDRIVE-GDOCS-001"
WO_001_ACCOUNT = "antonyfm@empyreanstudios.co"

SSH_KEY = "/root/.ssh/id_ed25519"
SSH_USER = r"DESKTOP-LVGUIQ9\antonys beast pc"
SSH_HOST = os.getenv("EOS_LOCAL_BRIDGE_IP", "100.74.199.102")

ALLOWED_DOMAINS: frozenset[str] = frozenset({"drive.google.com"})

BLOCKED_DOMAINS: frozenset[str] = frozenset(
    {
        "mail.google.com",
        "accounts.google.com",
        "calendar.google.com",
        "contacts.google.com",
        "photos.google.com",
        "youtube.com",
        "www.youtube.com",
    }
)


def classify_backend() -> str:
    """Return backend classification."""
    return BACKEND_CLASS


def validate_profile_directory(profile_directory: str) -> list[str]:
    """Validate that a profile directory name is safe.

    Must be: 'Default', 'Profile 1', 'Profile 2', etc.
    Blocks path traversal and injection.
    """
    errors: list[str] = []
    if not profile_directory:
        errors.append("Profile directory is empty")
        return errors

    if ".." in profile_directory or "/" in profile_directory or "\\" in profile_directory:
        errors.append(f"Profile directory contains path traversal: {profile_directory}")

    if not (
        profile_directory == "Default"
        or profile_directory.startswith("Profile ")
        or profile_directory == "System Profile"
        or profile_directory == "Guest Profile"
    ):
        errors.append(f"Unrecognized profile directory format: {profile_directory}")

    if len(profile_directory) > 50:
        errors.append("Profile directory name too long")

    return errors


def validate_drive_url(url: str) -> list[str]:
    """Validate URL for Chrome profile launch."""
    errors: list[str] = []

    if not url.startswith("https://"):
        errors.append(f"URL must use HTTPS: {url}")
        return errors

    url_host = url.replace("https://", "").split("/")[0].split(":")[0]

    if url_host in BLOCKED_DOMAINS:
        errors.append(f"Domain is blocked: {url_host}")

    if url_host not in ALLOWED_DOMAINS:
        errors.append(f"Domain not in allowed list: {url_host}")

    return errors


def build_chrome_profile_drive_launch_command(
    chrome_path: str = CHROME_PATH,
    profile_directory: str = "Default",
    url: str = DRIVE_URL,
) -> str:
    """Build the Chrome launch command with --profile-directory flag.

    This opens Chrome with the specified profile directly.
    No account switching UI. No credential entry.
    """
    return f'"{chrome_path}" --profile-directory="{profile_directory}" "{url}"'


def build_task_scheduler_profile_launch(
    profile_directory: str = "Default",
    chrome_path: str = CHROME_PATH,
    url: str = DRIVE_URL,
    task_name: str = TASK_NAME_PREFIX,
) -> dict[str, str]:
    """Build Task Scheduler commands for profile-specific Chrome launch.

    Returns dict with 'create', 'run', and 'delete' commands.
    Uses /IT for interactive user session.
    """
    tr_value = f'\\"{chrome_path}\\" --profile-directory=\\"{profile_directory}\\" {url}'

    create_cmd = (
        f'schtasks /create /tn "{task_name}" /tr "{tr_value}" /sc once /st 00:00 /f /rl highest /it'
    )

    run_cmd = f'schtasks /run /tn "{task_name}"'
    delete_cmd = f'schtasks /delete /tn "{task_name}" /f'

    return {
        "create": create_cmd,
        "run": run_cmd,
        "delete": delete_cmd,
    }


def build_ssh_profile_launch_sequence(
    profile_directory: str = "Default",
) -> list[str]:
    """Build the full SSH command sequence for profile-specific Chrome launch.

    Returns list of SSH commands to execute in order:
    1. Create scheduled task
    2. Run scheduled task
    (Cleanup is separate)
    """
    cmds = build_task_scheduler_profile_launch(profile_directory=profile_directory)

    ssh_prefix = (
        f"ssh -i {SSH_KEY} -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=8 "
        f"'{SSH_USER}'@{SSH_HOST}"
    )

    return [
        f"{ssh_prefix} '{cmds['create']}'",
        f"{ssh_prefix} '{cmds['run']}'",
    ]


def build_ssh_cleanup_command() -> str:
    """Build SSH command to delete the scheduled task after use."""
    cmds = build_task_scheduler_profile_launch()
    return (
        f"ssh -i {SSH_KEY} -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=8 "
        f"'{SSH_USER}'@{SSH_HOST} '{cmds['delete']}'"
    )


def build_action_attempted_message(
    profile_directory: str,
    exit_code: int = 0,
) -> dict[str, Any]:
    """Build ACTION_ATTEMPTED message for profile-specific launch."""
    return {
        "message_type": "ACTION_ATTEMPTED",
        "work_order_id": WO_001_ID,
        "sender": "node:vps_orchestrator",
        "recipient": "advisor",
        "payload": {
            "action": "OPEN_GOOGLE_DRIVE",
            "backend": BACKEND_CLASS,
            "launch_method": "WINDOWS_TASK_SCHEDULER_INTERACTIVE",
            "chrome_path": CHROME_PATH,
            "profile_directory": profile_directory,
            "url": DRIVE_URL,
            "target_account": WO_001_ACCOUNT,
            "command_exit_code": exit_code,
            "visible_confirmed": False,
            "status": "WAITING_FOR_FOUNDER_VISUAL_CONFIRMATION",
            "credentials_used": False,
            "cookies_read": False,
            "account_switched_via_ui": False,
        },
    }
