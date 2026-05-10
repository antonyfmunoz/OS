"""
Chrome accessibility launch backend for Phase 95.1.

Launches Chrome with --force-renderer-accessibility so that
Windows UI Automation / accessibility tree can read web page content.

This is NOT CDP. This is NOT Playwright. This is NOT hidden automation.
This makes Chrome's web content visible to screen readers and
accessibility inspection tools — the same data a blind user would get.

Backend class: VISIBLE_CHROME_ACCESSIBILITY_LAUNCH
"""

from __future__ import annotations

import os
from typing import Any


BACKEND_CLASS = "VISIBLE_CHROME_ACCESSIBILITY_LAUNCH"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DRIVE_URL = "https://drive.google.com/drive/my-drive"

SSH_KEY = "/root/.ssh/id_ed25519"
SSH_USER = r"DESKTOP-LVGUIQ9\antonys beast pc"
SSH_HOST = os.getenv("EOS_LOCAL_BRIDGE_IP", "100.74.199.102")
TASK_NAME = "UMH_ChromeA11yLaunch"

ALLOWED_FLAGS: frozenset[str] = frozenset(
    {
        "--force-renderer-accessibility",
        "--profile-directory",
    }
)

BLOCKED_FLAGS: frozenset[str] = frozenset(
    {
        "--remote-debugging-port",
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--enable-automation",
        "--disable-extensions",
        "--user-data-dir",
        "--remote-allow-origins",
        "--auto-open-devtools-for-tabs",
    }
)


def classify_backend() -> str:
    """Return backend classification."""
    return BACKEND_CLASS


def validate_accessibility_flags(flags: list[str]) -> list[str]:
    """Validate that only allowed Chrome flags are used."""
    errors: list[str] = []
    for flag in flags:
        flag_name = flag.split("=")[0] if "=" in flag else flag
        if flag_name in BLOCKED_FLAGS:
            errors.append(f"Blocked flag: {flag_name}")
        elif flag_name not in ALLOWED_FLAGS and not flag_name.startswith("https://"):
            errors.append(f"Unknown flag (not in allowed list): {flag_name}")
    return errors


def build_chrome_accessibility_launch_command(
    chrome_path: str = CHROME_PATH,
    profile_directory: str = "Profile 5",
    url: str = DRIVE_URL,
) -> str:
    """Build Chrome launch command with accessibility flag.

    Includes --force-renderer-accessibility so UIAutomation can read
    the web page content (file list, navigation, buttons).
    """
    return (
        f'"{chrome_path}" '
        f'--profile-directory="{profile_directory}" '
        f"--force-renderer-accessibility "
        f'"{url}"'
    )


def build_task_scheduler_accessibility_launch(
    profile_directory: str = "Profile 5",
    chrome_path: str = CHROME_PATH,
    url: str = DRIVE_URL,
    task_name: str = TASK_NAME,
) -> dict[str, str]:
    """Build Task Scheduler commands for accessibility-enabled Chrome launch."""
    tr_value = (
        f'\\"{chrome_path}\\" '
        f'--profile-directory=\\"{profile_directory}\\" '
        f"--force-renderer-accessibility "
        f"{url}"
    )

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


def build_ssh_accessibility_launch_sequence(
    profile_directory: str = "Profile 5",
) -> list[str]:
    """Build SSH commands to launch Chrome with accessibility in interactive session."""
    cmds = build_task_scheduler_accessibility_launch(profile_directory=profile_directory)

    ssh_prefix = (
        f"ssh -i {SSH_KEY} -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=8 "
        f"'{SSH_USER}'@{SSH_HOST}"
    )

    return [
        f"{ssh_prefix} '{cmds['create']}'",
        f"{ssh_prefix} '{cmds['run']}'",
        f"{ssh_prefix} '{cmds['delete']}'",
    ]
