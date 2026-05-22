"""Tests for cc_sdk subprocess environment construction."""

import os
import sys
from unittest.mock import mock_open, patch

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

from adapters.models.cc_sdk import _find_ancestor_oauth, _get_subprocess_env


class TestFindAncestorOauth:
    def test_finds_token_in_current_process(self):
        fake_environ = b"FOO=bar\x00CLAUDE_CODE_OAUTH_TOKEN=test-token-123\x00BAZ=qux"
        pid = os.getpid()
        with patch("builtins.open", mock_open(read_data=fake_environ)):
            token = _find_ancestor_oauth()
        assert token == "test-token-123"

    def test_returns_none_when_no_token_in_ancestry(self):
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

    def test_handles_missing_proc(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            token = _find_ancestor_oauth()
        assert token is None


class TestGetSubprocessEnv:
    def test_loads_oauth_when_missing_from_environ(self):
        import adapters.models.cc_sdk as cc_mod

        old_cached = cc_mod._cached_oauth
        try:
            cc_mod._cached_oauth = None
            with (
                patch.dict(os.environ, {}, clear=False),
                patch.object(cc_mod, "_find_ancestor_oauth", return_value="found-token"),
            ):
                os.environ.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
                env = _get_subprocess_env()
            assert env.get("CLAUDE_CODE_OAUTH_TOKEN") == "found-token"
        finally:
            cc_mod._cached_oauth = old_cached

    def test_preserves_existing_oauth(self):
        import adapters.models.cc_sdk as cc_mod

        old_cached = cc_mod._cached_oauth
        try:
            cc_mod._cached_oauth = None
            with (
                patch.dict(
                    os.environ,
                    {"CLAUDE_CODE_OAUTH_TOKEN": "existing-token"},
                    clear=False,
                ),
                patch.object(cc_mod, "_find_ancestor_oauth") as mock_find,
            ):
                env = _get_subprocess_env()
            assert "CLAUDE_CODE_OAUTH_TOKEN" not in env
            mock_find.assert_not_called()
        finally:
            cc_mod._cached_oauth = old_cached

    def test_strips_anthropic_api_key(self):
        import adapters.models.cc_sdk as cc_mod

        old_cached = cc_mod._cached_oauth
        try:
            cc_mod._cached_oauth = None
            with patch.dict(
                os.environ,
                {"ANTHROPIC_API_KEY": "sk-ant-test", "CLAUDE_CODE_OAUTH_TOKEN": "x"},
                clear=False,
            ):
                env = _get_subprocess_env()
            assert env.get("ANTHROPIC_API_KEY") == ""
        finally:
            cc_mod._cached_oauth = old_cached

    def test_handles_missing_sessions_file(self):
        import adapters.models.cc_sdk as cc_mod

        old_cached = cc_mod._cached_oauth
        try:
            cc_mod._cached_oauth = None
            with (
                patch.dict(os.environ, {}, clear=False),
                patch.object(cc_mod, "_find_ancestor_oauth", return_value=None),
            ):
                os.environ.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
                env = _get_subprocess_env()
            assert "CLAUDE_CODE_OAUTH_TOKEN" not in env
        finally:
            cc_mod._cached_oauth = old_cached

    def test_caches_oauth_token(self):
        import adapters.models.cc_sdk as cc_mod

        old_cached = cc_mod._cached_oauth
        try:
            cc_mod._cached_oauth = None
            with (
                patch.dict(os.environ, {}, clear=False),
                patch.object(
                    cc_mod, "_find_ancestor_oauth", return_value="cached-token"
                ) as mock_find,
            ):
                os.environ.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
                env1 = _get_subprocess_env()
                env2 = _get_subprocess_env()
            assert env1.get("CLAUDE_CODE_OAUTH_TOKEN") == "cached-token"
            assert env2.get("CLAUDE_CODE_OAUTH_TOKEN") == "cached-token"
            mock_find.assert_called_once()
        finally:
            cc_mod._cached_oauth = old_cached
