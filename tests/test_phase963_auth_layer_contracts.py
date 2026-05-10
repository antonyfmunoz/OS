"""Tests for eos_ai/substrate/auth_layer_contracts.py (Phase 96.3)."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest

from eos_ai.substrate.auth_layer_contracts import (
    AuthMaterialHandling,
    AuthMethodType,
    AuthProfile,
    is_auth_not_backend,
    is_browser_profile_auth_not_backend,
    secret_must_not_enter_model_context,
)


class TestAuthMethodType(unittest.TestCase):
    def test_has_16_values(self) -> None:
        self.assertEqual(len(AuthMethodType), 16)


class TestAuthMaterialHandling(unittest.TestCase):
    def test_has_7_values(self) -> None:
        self.assertEqual(len(AuthMaterialHandling), 7)


class TestAuthFunctions(unittest.TestCase):
    def test_oauth_is_auth_not_backend(self) -> None:
        """OAuth is auth layer, not backend."""
        self.assertTrue(is_auth_not_backend(AuthMethodType.OAUTH_USER_CONSENT))

    def test_any_method_is_auth_not_backend(self) -> None:
        for method in AuthMethodType:
            self.assertTrue(is_auth_not_backend(method))

    def test_browser_profile_is_auth_not_backend(self) -> None:
        self.assertTrue(is_browser_profile_auth_not_backend(AuthMethodType.BROWSER_SESSION_PROFILE))

    def test_api_key_is_not_browser_profile_auth(self) -> None:
        self.assertFalse(is_browser_profile_auth_not_backend(AuthMethodType.API_KEY))

    def test_secret_must_not_enter_model_context(self) -> None:
        self.assertTrue(secret_must_not_enter_model_context())


class TestAuthProfile(unittest.TestCase):
    def test_defaults_to_model_never_sees_secret(self) -> None:
        profile = AuthProfile(
            auth_id="test-auth",
            method_type=AuthMethodType.OAUTH_USER_CONSENT,
        )
        self.assertEqual(
            profile.secret_handling,
            AuthMaterialHandling.MODEL_NEVER_SEES_SECRET,
        )

    def test_to_dict_serializes_correctly(self) -> None:
        profile = AuthProfile(
            auth_id="test-auth-2",
            method_type=AuthMethodType.SERVICE_ACCOUNT,
            source_system="google_workspace",
            account_scope="read_only",
            allowed_backends=["api-1", "sdk-1"],
            scope_description="Read-only access to Google Docs",
            notes="test auth profile",
        )
        d = profile.to_dict()
        self.assertEqual(d["auth_id"], "test-auth-2")
        self.assertEqual(d["method_type"], "service_account")
        self.assertEqual(d["source_system"], "google_workspace")
        self.assertEqual(d["allowed_backends"], ["api-1", "sdk-1"])
        self.assertEqual(d["secret_handling"], "model_never_sees_secret")
        self.assertFalse(d["token_exposure_allowed"])
        self.assertFalse(d["model_visibility"])
        self.assertFalse(d["rotation_required"])


if __name__ == "__main__":
    unittest.main()
