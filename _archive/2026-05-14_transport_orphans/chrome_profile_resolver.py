"""
Chrome profile resolver for Phase 94D.9.

Safely inspects Chrome profile metadata to find which profile is
associated with a target email/account. Does NOT read credentials,
cookies, tokens, or sensitive browser data.

Allowed: Local State (profile inventory), Preferences (account metadata).
Blocked: Cookies, Login Data, Web Data, History, tokens, secrets.

No credential capture. No cookie reading. No Playwright.
"""

from __future__ import annotations

import json
from typing import Any


CHROME_USER_DATA_DIR_WINDOWS = r"C:\Users\{username}\AppData\Local\Google\Chrome\User Data"
CHROME_LOCAL_STATE_FILE = "Local State"

ALLOWED_METADATA_FILES: frozenset[str] = frozenset(
    {
        "Local State",
        "Preferences",
    }
)

BLOCKED_FILES: frozenset[str] = frozenset(
    {
        "Cookies",
        "Login Data",
        "Web Data",
        "History",
        "Network/Cookies",
        "Bookmarks",
        "Favicons",
        "Top Sites",
        "Visited Links",
        "QuotaManager",
        "TransportSecurity",
        "CURRENT",
        "LOCK",
        "LOG",
    }
)

BLOCKED_EXTRACTION: frozenset[str] = frozenset(
    {
        "passwords",
        "cookies",
        "tokens",
        "api_keys",
        "session_values",
        "2fa_codes",
        "payment_data",
        "credit_cards",
        "autofill",
    }
)


def is_file_allowed(filename: str) -> bool:
    """Check if a Chrome data file is safe to read for metadata."""
    base = filename.split("/")[-1].split("\\")[-1]
    return base in ALLOWED_METADATA_FILES


def is_file_blocked(filename: str) -> bool:
    """Check if a Chrome data file is blocked from reading."""
    base = filename.split("/")[-1].split("\\")[-1]
    return base in BLOCKED_FILES


def get_chrome_user_data_dir(username: str = "") -> str:
    """Return the Chrome User Data directory path.

    Uses %LOCALAPPDATA% expansion on Windows.
    """
    if username:
        return CHROME_USER_DATA_DIR_WINDOWS.format(username=username)
    return r"%LOCALAPPDATA%\Google\Chrome\User Data"


def build_profile_inventory_command() -> str:
    """Build a PowerShell command to read Chrome Local State metadata.

    Reads ONLY the profile info block from Local State.
    Does NOT read cookies, login data, history, or any credential store.
    """
    return (
        'powershell.exe -NoProfile -Command "'
        "$localState = Get-Content -Raw "
        "\\\"$env:LOCALAPPDATA\\Google\\Chrome\\User Data\\Local State\\\" "
        "| ConvertFrom-Json; "
        "$profiles = $localState.profile.info_cache; "
        "$profiles | ConvertTo-Json -Depth 3"
        '"'
    )


def parse_local_state_profile_info(json_text: str) -> dict[str, Any]:
    """Parse the profile info_cache from Chrome Local State.

    Returns dict of profile_directory -> profile_metadata.
    Only extracts safe metadata (name, email, display picture URL).
    """
    try:
        data = json.loads(json_text)
    except (json.JSONDecodeError, TypeError):
        return {}

    if not isinstance(data, dict):
        return {}

    profiles: dict[str, Any] = {}
    for profile_dir, info in data.items():
        if not isinstance(info, dict):
            continue
        profiles[profile_dir] = {
            "directory": profile_dir,
            "name": info.get("name", ""),
            "shortcut_name": info.get("shortcut_name", ""),
            "gaia_name": info.get("gaia_name", ""),
            "user_name": info.get("user_name", ""),
            "gaia_id": info.get("gaia_id", ""),
            "is_using_default_name": info.get("is_using_default_name", True),
            "is_consented_primary_account": info.get("is_consented_primary_account", False),
        }

    return profiles


def parse_profile_preferences_metadata(json_text: str) -> dict[str, Any]:
    """Parse safe metadata from a Chrome profile's Preferences file.

    Extracts ONLY: account_info email, profile name, gaia info.
    Does NOT extract: cookies, tokens, passwords, history.
    """
    try:
        data = json.loads(json_text)
    except (json.JSONDecodeError, TypeError):
        return {}

    result: dict[str, Any] = {"emails": [], "profile_name": ""}

    account_info = data.get("account_info", [])
    if isinstance(account_info, list):
        for account in account_info:
            if isinstance(account, dict):
                email = account.get("email", "")
                if email:
                    result["emails"].append(email.lower())

    profile_section = data.get("profile", {})
    if isinstance(profile_section, dict):
        result["profile_name"] = profile_section.get("name", "")

    return result


def find_profiles_for_email(
    profile_metadata: dict[str, Any],
    target_email: str,
) -> list[str]:
    """Find which profile directories match the target email.

    Searches user_name and gaia_name fields from Local State info_cache.
    Returns list of matching profile directory names.
    """
    target = target_email.lower().strip()
    matches: list[str] = []

    for profile_dir, info in profile_metadata.items():
        user_name = info.get("user_name", "").lower().strip()
        gaia_name = info.get("gaia_name", "").lower().strip()
        name = info.get("name", "").lower().strip()

        if target in (user_name, gaia_name, name):
            matches.append(profile_dir)

    return matches


def build_safe_profile_inventory_result(
    profiles: dict[str, Any],
    target_email: str,
    matches: list[str],
) -> dict[str, Any]:
    """Build the safe profile inventory result.

    Includes only non-sensitive metadata.
    Never includes credentials, cookies, or tokens.
    """
    return {
        "total_profiles": len(profiles),
        "target_email": target_email,
        "matches": matches,
        "match_count": len(matches),
        "status": classify_profile_resolution_status(matches, profiles),
        "profiles_summary": {
            k: {"name": v.get("name", ""), "user_name": v.get("user_name", "")}
            for k, v in profiles.items()
        },
        "sensitive_data_included": False,
        "credentials_captured": False,
        "cookies_read": False,
    }


def classify_profile_resolution_status(
    matches: list[str],
    profiles: dict[str, Any] | None = None,
) -> str:
    """Classify the profile resolution status."""
    if profiles is not None and len(profiles) == 0:
        return "CHROME_USER_DATA_NOT_FOUND"

    if len(matches) == 1:
        return "PROFILE_MATCH_FOUND"
    elif len(matches) > 1:
        return "MULTIPLE_MATCHES_FOUND"
    else:
        return "NO_MATCH_FOUND"


def build_no_match_options() -> dict[str, Any]:
    """Build options when no profile matches the target email."""
    return {
        "status": "NEEDS_FOUNDER_DECISION",
        "options": [
            {"option": "A", "action": "ONE_TIME_MANUAL_LOGIN", "description": "Manually sign into antonyfm@empyreanstudios.co in an existing Chrome profile"},
            {"option": "B", "action": "CREATE_DEDICATED_PROFILE", "description": "Create a dedicated UMH Chrome profile for this account"},
            {"option": "C", "action": "USE_CURRENT_PROFILE", "description": "Use the currently active profile anyway"},
            {"option": "D", "action": "CANCEL", "description": "Cancel this test"},
        ],
        "note": "After one-time setup, future launches will use the resolved profile automatically.",
    }
