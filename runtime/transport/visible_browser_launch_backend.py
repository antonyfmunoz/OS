"""
Visible browser launch backend for Phase 94D.7R.

Opens a visible URL in Google Chrome on the local machine.
This is NOT Playwright. This does NOT scrape, control DOM, or read content.
It only launches a URL visibly in Chrome.

Backend classification: VISIBLE_CHROME_LAUNCH
Not: Playwright, GUI_COMPUTER_USE, Explorer/default handler, or browser automation.

No Playwright. No scraping. No Gmail. No account switching.
No credential capture. No silent fallback to Explorer/default browser.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any


BACKEND_CLASS = "VISIBLE_CHROME_LAUNCH"
BACKEND_CLASS_DEFAULT = "VISIBLE_DEFAULT_BROWSER_LAUNCH"

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

DRIVE_URL = "https://drive.google.com/"

CHROME_WINDOWS_PATHS: list[str] = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
]


def classify_backend() -> str:
    """Return the backend classification. Not Playwright. Not Explorer."""
    return BACKEND_CLASS


def find_chrome_candidates() -> list[str]:
    """Return list of possible Chrome executable paths on Windows."""
    return list(CHROME_WINDOWS_PATHS)


def build_chrome_detection_command() -> str:
    """Build a PowerShell command that finds Chrome on Windows.

    Returns the PowerShell command string that tests each candidate path
    and returns the first existing one, or throws if Chrome is not found.
    """
    return (
        'powershell.exe -NoProfile -Command "'
        "$chromeCandidates = @("
        "'$env:ProgramFiles\\Google\\Chrome\\Application\\chrome.exe', "
        "'${env:ProgramFiles(x86)}\\Google\\Chrome\\Application\\chrome.exe', "
        "'$env:LOCALAPPDATA\\Google\\Chrome\\Application\\chrome.exe'"
        "); "
        "$chrome = $chromeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1; "
        "if (-not $chrome) { Write-Output 'CHROME_NOT_FOUND'; exit 1 }; "
        'Write-Output $chrome"'
    )


def build_open_url_in_chrome_command(url: str) -> str:
    """Build the PowerShell command to open a URL in Chrome specifically.

    Uses Start-Process with -FilePath pointing to the located chrome.exe.
    Does NOT fall back to explorer.exe or default browser.
    """
    return (
        'powershell.exe -NoProfile -Command "'
        "$chromeCandidates = @("
        "'$env:ProgramFiles\\Google\\Chrome\\Application\\chrome.exe', "
        "'${env:ProgramFiles(x86)}\\Google\\Chrome\\Application\\chrome.exe', "
        "'$env:LOCALAPPDATA\\Google\\Chrome\\Application\\chrome.exe'"
        "); "
        "$chrome = $chromeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1; "
        "if (-not $chrome) { Write-Output 'CHROME_NOT_FOUND'; exit 1 }; "
        f"Start-Process -FilePath $chrome -ArgumentList '{url}'; "
        'Write-Output $chrome"'
    )


def validate_url_allowed(url: str, allowed_domains: frozenset[str] | None = None) -> list[str]:
    """Validate that a URL is allowed for launch.

    Returns list of errors. Empty = allowed.
    """
    errors: list[str] = []
    domains = allowed_domains if allowed_domains is not None else ALLOWED_DOMAINS

    if not url.startswith("https://"):
        errors.append(f"URL must use HTTPS: {url}")
        return errors

    url_host = url.replace("https://", "").split("/")[0].split(":")[0]

    if url_host in BLOCKED_DOMAINS:
        errors.append(f"Domain is blocked: {url_host}")
        return errors

    if url_host not in domains:
        errors.append(f"Domain not in allowed list: {url_host}")

    return errors


def build_open_url_command(url: str) -> list[list[str]]:
    """Build commands to open a URL in the default visible browser.

    DEPRECATED for W0-001. Use build_open_url_in_chrome_command() instead.
    Kept for fallback if advisor explicitly approves default browser.

    Returns a list of candidate commands as argv lists (no shell=True).
    """
    commands: list[list[str]] = []

    if _is_wsl():
        commands.append(["powershell.exe", "Start-Process", url])
        commands.append(["cmd.exe", "/c", "start", "", url])
    elif os.name == "nt":
        commands.append(["cmd.exe", "/c", "start", "", url])
    else:
        commands.append(["xdg-open", url])

    return commands


def _is_wsl() -> bool:
    """Detect if running inside WSL."""
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except (FileNotFoundError, OSError):
        return False


def build_drive_open_action(
    target_account: str = "antonyfm@empyreanstudios.co",
) -> dict[str, Any]:
    """Build the action payload for opening Google Drive in Chrome."""
    return {
        "action": "OPEN_GOOGLE_DRIVE",
        "url": DRIVE_URL,
        "target_account": target_account,
        "backend": BACKEND_CLASS,
        "chrome_command": build_open_url_in_chrome_command(DRIVE_URL),
        "chrome_candidates": find_chrome_candidates(),
        "allowed_domains": sorted(ALLOWED_DOMAINS),
        "blocked_domains": sorted(BLOCKED_DOMAINS),
    }


def build_backend_missing_message(reason: str) -> dict[str, Any]:
    """Build a BACKEND_MISSING message when Chrome cannot be found.

    Does NOT silently fall back to Explorer/default browser.
    Asks advisor for decision.
    """
    return {
        "message_type": "BACKEND_MISSING",
        "backend": BACKEND_CLASS,
        "reason": reason,
        "fallback_options": [
            {"option": "A", "action": "LOCATE_CHROME_MANUALLY", "description": "Locate Chrome manually on this machine"},
            {"option": "B", "action": "APPROVE_DEFAULT_BROWSER_FALLBACK", "description": "Approve default browser fallback (not Chrome-specific)"},
            {"option": "C", "action": "APPROVE_EDGE_FALLBACK", "description": "Approve Microsoft Edge fallback"},
            {"option": "D", "action": "APPROVE_PLAYWRIGHT_FALLBACK", "description": "Approve Playwright / structured automation"},
            {"option": "E", "action": "CANCEL_TEST", "description": "Cancel this test"},
        ],
        "silent_fallback_allowed": False,
        "next_action_required": "ADVISOR_DECISION",
    }


def execute_chrome_launch(url: str) -> dict[str, Any]:
    """Execute a Chrome-specific browser launch. Returns result dict.

    Uses the PowerShell command that locates chrome.exe and launches it.
    Does NOT fall back to Explorer/default browser on failure.
    """
    errors = validate_url_allowed(url)
    if errors:
        return {
            "success": False,
            "backend": BACKEND_CLASS,
            "url": url,
            "detail": f"URL validation failed: {errors}",
            "command_used": None,
            "chrome_path": None,
        }

    chrome_cmd = build_open_url_in_chrome_command(url)

    try:
        result = subprocess.run(
            chrome_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        stdout = result.stdout.strip()

        if result.returncode != 0 or "CHROME_NOT_FOUND" in stdout:
            return {
                "success": False,
                "backend": BACKEND_CLASS,
                "url": url,
                "detail": "CHROME_NOT_FOUND",
                "command_used": chrome_cmd,
                "chrome_path": None,
                "backend_missing": build_backend_missing_message("Chrome executable not found on this machine"),
            }

        return {
            "success": True,
            "backend": BACKEND_CLASS,
            "url": url,
            "detail": f"Chrome launched: {stdout}",
            "command_used": chrome_cmd,
            "chrome_path": stdout,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "backend": BACKEND_CLASS,
            "url": url,
            "detail": "Chrome launch command timed out",
            "command_used": chrome_cmd,
            "chrome_path": None,
        }
    except OSError as e:
        return {
            "success": False,
            "backend": BACKEND_CLASS,
            "url": url,
            "detail": f"OS error: {e}",
            "command_used": chrome_cmd,
            "chrome_path": None,
        }


def execute_browser_launch(url: str) -> dict[str, Any]:
    """Execute a visible browser launch — CHROME PREFERRED.

    Tries Chrome first. If Chrome is not found, returns BACKEND_MISSING
    instead of silently falling back to Explorer/default browser.
    """
    return execute_chrome_launch(url)


def parse_launch_result(result: dict[str, Any]) -> str:
    """Parse a launch result into a human-readable status line."""
    if result.get("success"):
        chrome_path = result.get("chrome_path", "")
        path_info = f" (path: {chrome_path})" if chrome_path else ""
        return f"Chrome opened {result.get('url', '')} via {result.get('backend', BACKEND_CLASS)}{path_info}"

    detail = result.get("detail", "unknown error")
    if "CHROME_NOT_FOUND" in detail:
        return f"Chrome not found — backend missing. No silent fallback. Advisor decision required."
    return f"Browser launch failed: {detail}"
