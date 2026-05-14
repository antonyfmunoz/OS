"""Tests for Phase 94D.9 — Chrome Profile Resolver."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.chrome_profile_resolver import (
    BLOCKED_FILES,
    build_no_match_options,
    build_profile_inventory_command,
    build_safe_profile_inventory_result,
    classify_profile_resolution_status,
    find_profiles_for_email,
    is_file_allowed,
    is_file_blocked,
    parse_local_state_profile_info,
    parse_profile_preferences_metadata,
)

SAMPLE_LOCAL_STATE = """
{
  "Default": {
    "name": "Personal",
    "user_name": "personal@gmail.com",
    "gaia_name": "Personal User",
    "gaia_id": "123",
    "is_using_default_name": false,
    "is_consented_primary_account": true
  },
  "Profile 1": {
    "name": "Work",
    "user_name": "antonyfm@empyreanstudios.co",
    "gaia_name": "Antony Munoz",
    "gaia_id": "456",
    "is_using_default_name": false,
    "is_consented_primary_account": true
  },
  "Profile 2": {
    "name": "Other",
    "user_name": "other@example.com",
    "gaia_name": "Other Person",
    "gaia_id": "789",
    "is_using_default_name": false,
    "is_consented_primary_account": false
  }
}
"""

SAMPLE_PREFERENCES = """
{
  "account_info": [
    {"email": "antonyfm@empyreanstudios.co", "gaia_id": "456"}
  ],
  "profile": {
    "name": "Work"
  }
}
"""


class TestParseLocalState:
    def test_parses_profiles(self) -> None:
        profiles = parse_local_state_profile_info(SAMPLE_LOCAL_STATE)
        assert len(profiles) == 3

    def test_extracts_user_name(self) -> None:
        profiles = parse_local_state_profile_info(SAMPLE_LOCAL_STATE)
        assert profiles["Profile 1"]["user_name"] == "antonyfm@empyreanstudios.co"

    def test_extracts_display_name(self) -> None:
        profiles = parse_local_state_profile_info(SAMPLE_LOCAL_STATE)
        assert profiles["Default"]["name"] == "Personal"

    def test_handles_invalid_json(self) -> None:
        result = parse_local_state_profile_info("not json")
        assert result == {}

    def test_handles_empty(self) -> None:
        result = parse_local_state_profile_info("")
        assert result == {}


class TestParsePreferences:
    def test_parses_email(self) -> None:
        result = parse_profile_preferences_metadata(SAMPLE_PREFERENCES)
        assert "antonyfm@empyreanstudios.co" in result["emails"]

    def test_parses_profile_name(self) -> None:
        result = parse_profile_preferences_metadata(SAMPLE_PREFERENCES)
        assert result["profile_name"] == "Work"

    def test_handles_invalid_json(self) -> None:
        result = parse_profile_preferences_metadata("not json")
        assert result == {}


class TestFindProfiles:
    def test_target_email_match_found(self) -> None:
        profiles = parse_local_state_profile_info(SAMPLE_LOCAL_STATE)
        matches = find_profiles_for_email(profiles, "antonyfm@empyreanstudios.co")
        assert matches == ["Profile 1"]

    def test_multiple_matches_detected(self) -> None:
        profiles = {
            "Default": {"user_name": "antonyfm@empyreanstudios.co", "gaia_name": "", "name": ""},
            "Profile 1": {"user_name": "antonyfm@empyreanstudios.co", "gaia_name": "", "name": ""},
        }
        matches = find_profiles_for_email(profiles, "antonyfm@empyreanstudios.co")
        assert len(matches) == 2

    def test_no_match_detected(self) -> None:
        profiles = parse_local_state_profile_info(SAMPLE_LOCAL_STATE)
        matches = find_profiles_for_email(profiles, "nobody@nowhere.com")
        assert matches == []

    def test_case_insensitive(self) -> None:
        profiles = parse_local_state_profile_info(SAMPLE_LOCAL_STATE)
        matches = find_profiles_for_email(profiles, "ANTONYFM@EMPYREANSTUDIOS.CO")
        assert matches == ["Profile 1"]


class TestBlockedFiles:
    def test_cookies_blocked(self) -> None:
        assert is_file_blocked("Cookies")

    def test_login_data_blocked(self) -> None:
        assert is_file_blocked("Login Data")

    def test_history_blocked(self) -> None:
        assert is_file_blocked("History")

    def test_web_data_blocked(self) -> None:
        assert is_file_blocked("Web Data")

    def test_local_state_allowed(self) -> None:
        assert is_file_allowed("Local State")

    def test_preferences_allowed(self) -> None:
        assert is_file_allowed("Preferences")

    def test_cookies_never_allowed(self) -> None:
        assert not is_file_allowed("Cookies")


class TestInventoryResult:
    def test_result_has_no_credentials(self) -> None:
        profiles = parse_local_state_profile_info(SAMPLE_LOCAL_STATE)
        matches = find_profiles_for_email(profiles, "antonyfm@empyreanstudios.co")
        result = build_safe_profile_inventory_result(profiles, "antonyfm@empyreanstudios.co", matches)
        assert result["sensitive_data_included"] is False
        assert result["credentials_captured"] is False
        assert result["cookies_read"] is False

    def test_result_does_not_include_tokens(self) -> None:
        profiles = parse_local_state_profile_info(SAMPLE_LOCAL_STATE)
        matches = find_profiles_for_email(profiles, "antonyfm@empyreanstudios.co")
        result = build_safe_profile_inventory_result(profiles, "antonyfm@empyreanstudios.co", matches)
        result_str = str(result).lower()
        assert "token" not in result_str
        assert "cookie" not in result_str or "cookies_read" in result_str
        assert "password" not in result_str


class TestClassifyStatus:
    def test_single_match(self) -> None:
        assert classify_profile_resolution_status(["Profile 1"]) == "PROFILE_MATCH_FOUND"

    def test_multiple_matches(self) -> None:
        assert classify_profile_resolution_status(["Default", "Profile 1"]) == "MULTIPLE_MATCHES_FOUND"

    def test_no_match(self) -> None:
        assert classify_profile_resolution_status([]) == "NO_MATCH_FOUND"

    def test_no_profiles(self) -> None:
        assert classify_profile_resolution_status([], {}) == "CHROME_USER_DATA_NOT_FOUND"
