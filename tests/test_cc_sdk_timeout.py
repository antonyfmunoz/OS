"""Tests for cc_sdk timeout configuration."""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

from adapters.models.cc_sdk import DEFAULT_TIMEOUT_SECONDS, _resolve_timeout


class TestResolveTimeout:
    def test_default_timeout_is_120_seconds(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CC_SDK_TIMEOUT_SECONDS", None)
            result = _resolve_timeout()
        assert result == 120.0
        assert result == float(DEFAULT_TIMEOUT_SECONDS)

    def test_env_var_override_takes_effect(self):
        with patch.dict(os.environ, {"CC_SDK_TIMEOUT_SECONDS": "200"}, clear=False):
            result = _resolve_timeout()
        assert result == 200.0

    def test_invalid_env_value_falls_back_to_default(self):
        with patch.dict(
            os.environ, {"CC_SDK_TIMEOUT_SECONDS": "not_a_number"}, clear=False
        ):
            result = _resolve_timeout()
        assert result == 120.0

    def test_empty_env_value_falls_back_to_default(self):
        with patch.dict(os.environ, {"CC_SDK_TIMEOUT_SECONDS": ""}, clear=False):
            result = _resolve_timeout()
        assert result == 120.0

    def test_returns_float(self):
        with patch.dict(os.environ, {"CC_SDK_TIMEOUT_SECONDS": "60"}, clear=False):
            result = _resolve_timeout()
        assert isinstance(result, float)
