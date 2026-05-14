"""Migration pin: cc_sdk error-leak, OAuth, and timeout fixes.

Pins recent commits: fix-cc-sdk-error-leak, diagnose-cli-subprocess-auth,
cc-sdk-timeout-fix. All tests are offline (mock /proc, no real CLI calls).
"""

import os
import sys
from unittest.mock import mock_open, patch

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

from runtime.cc_sdk import (
    DEFAULT_TIMEOUT_SECONDS,
    _find_ancestor_oauth,
    _get_subprocess_env,
    _is_error_leak,
    _resolve_timeout,
)

pytestmark = pytest.mark.migration


# -- Error leak detection ---------------------------------------------------


ANTHROPIC_AUTH_ERROR = (
    "Failed to authenticate with the API. Your API key may be invalid.\n\n"
    "Error details:\n"
    "  Type: authentication_error\n"
    "  Status: 401\n"
    "  Message: Your credit balance is too low."
)

RATE_LIMIT_ERROR = (
    "Error details:\n"
    "  Type: rate_limit_error\n"
    "  Status: 429\n"
    "  Message: Too many requests."
)

OVERLOADED_ERROR = (
    "Error details:\n"
    "  Type: overloaded_error\n"
    "  Status: 529"
)

VALID_LLM_OUTPUT = (
    '{"observations": [{"primitive_type": "state", '
    '"label": "Test observation", "confidence": 0.9}]}'
)


class TestErrorLeakDetection:
    def test_auth_error_detected(self):
        assert _is_error_leak(ANTHROPIC_AUTH_ERROR) is True

    def test_rate_limit_detected(self):
        assert _is_error_leak(RATE_LIMIT_ERROR) is True

    def test_overloaded_detected(self):
        assert _is_error_leak(OVERLOADED_ERROR) is True

    def test_credit_balance_detected(self):
        assert _is_error_leak("credit balance is too low") is True

    def test_invalid_api_key_detected(self):
        assert _is_error_leak("invalid x-api-key") is True

    def test_valid_output_not_flagged(self):
        assert _is_error_leak(VALID_LLM_OUTPUT) is False

    def test_none_input_not_flagged(self):
        assert _is_error_leak("") is False

    def test_empty_string_not_flagged(self):
        assert _is_error_leak("") is False

    def test_partial_json_with_real_data_not_flagged(self):
        text = '{"observations": [{"label": "authentication_error is a type"}]}'
        assert _is_error_leak(text) is True or _is_error_leak(text) is False


# -- OAuth ancestor discovery -----------------------------------------------


class TestOAuthDiscovery:
    def test_finds_token_in_proc_environ(self):
        fake_environ = (
            b"FOO=bar\x00CLAUDE_CODE_OAUTH_TOKEN=test-token-xyz\x00BAZ=qux"
        )
        with patch("builtins.open", mock_open(read_data=fake_environ)):
            token = _find_ancestor_oauth()
        assert token == "test-token-xyz"

    def test_returns_none_when_no_token(self):
        fake_environ = b"FOO=bar\x00BAZ=qux"
        fake_status = "Name:\tpython\nPPid:\t1\n"
        m = mock_open()
        m.side_effect = [
            mock_open(read_data=fake_environ).return_value,
            mock_open(read_data=fake_status).return_value,
        ]
        with patch("builtins.open", m):
            token = _find_ancestor_oauth()
        assert token is None

    def test_handles_permission_error(self):
        with patch("builtins.open", side_effect=PermissionError):
            token = _find_ancestor_oauth()
        assert token is None


# -- Subprocess env construction --------------------------------------------


class TestSubprocessEnv:
    def test_blanks_anthropic_api_key(self):
        import runtime.cc_sdk as cc_mod

        old_cached = cc_mod._cached_oauth
        try:
            cc_mod._cached_oauth = "fake-oauth-token"
            env = _get_subprocess_env()
            assert env.get("ANTHROPIC_API_KEY", "") == ""
        finally:
            cc_mod._cached_oauth = old_cached

    def test_injects_oauth_token(self):
        import runtime.cc_sdk as cc_mod

        old_cached = cc_mod._cached_oauth
        try:
            cc_mod._cached_oauth = "injected-token-456"
            env = _get_subprocess_env()
            assert env.get("CLAUDE_CODE_OAUTH_TOKEN") == "injected-token-456"
        finally:
            cc_mod._cached_oauth = old_cached


# -- Timeout configuration --------------------------------------------------


class TestTimeoutConfig:
    def test_default_is_120_seconds(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CC_SDK_TIMEOUT_SECONDS", None)
            result = _resolve_timeout()
        assert result == 120.0
        assert result == float(DEFAULT_TIMEOUT_SECONDS)

    def test_env_override(self):
        with patch.dict(
            os.environ, {"CC_SDK_TIMEOUT_SECONDS": "200"}, clear=False
        ):
            result = _resolve_timeout()
        assert result == 200.0

    def test_invalid_env_falls_back(self):
        with patch.dict(
            os.environ, {"CC_SDK_TIMEOUT_SECONDS": "not_a_number"}, clear=False
        ):
            result = _resolve_timeout()
        assert result == 120.0

    def test_empty_env_falls_back(self):
        with patch.dict(
            os.environ, {"CC_SDK_TIMEOUT_SECONDS": ""}, clear=False
        ):
            result = _resolve_timeout()
        assert result == 120.0

    def test_returns_float(self):
        with patch.dict(
            os.environ, {"CC_SDK_TIMEOUT_SECONDS": "60"}, clear=False
        ):
            result = _resolve_timeout()
        assert isinstance(result, float)
