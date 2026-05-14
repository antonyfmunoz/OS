"""Tests for Windows Interactive Desktop Adapter contracts — Phase 96.8H.

Verifies:
1. Action types are defined.
2. Adapter statuses are defined.
3. Proof statuses are defined.
4. Blocked launch methods match canonical set.
5. Action request serializes correctly.
6. Action result serializes correctly.
7. Proof artifact serializes correctly.
8. Relay paths can be created and serialized.
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest

from execution.environments.windows_desktop_adapter_contracts import (
    BLOCKED_LAUNCH_METHODS,
    WindowsDesktopActionRequest,
    WindowsDesktopActionResult,
    WindowsDesktopActionType,
    WindowsDesktopAdapterStatus,
    WindowsDesktopProofArtifact,
    WindowsDesktopProofStatus,
    WindowsDesktopRelayPaths,
)


class TestActionTypes(unittest.TestCase):
    def test_ping_exists(self):
        self.assertEqual(WindowsDesktopActionType.PING.value, "ping")

    def test_open_application_url_exists(self):
        self.assertEqual(
            WindowsDesktopActionType.OPEN_APPLICATION_URL.value,
            "open_application_url",
        )

    def test_focus_application_exists(self):
        self.assertEqual(WindowsDesktopActionType.FOCUS_APPLICATION.value, "focus_application")

    def test_request_founder_confirmation_exists(self):
        self.assertEqual(
            WindowsDesktopActionType.REQUEST_FOUNDER_VISUAL_CONFIRMATION.value,
            "request_founder_visual_confirmation",
        )


class TestAdapterStatuses(unittest.TestCase):
    def test_pong_status(self):
        self.assertEqual(WindowsDesktopAdapterStatus.PONG.value, "pong")

    def test_pending_confirmation_status(self):
        self.assertEqual(
            WindowsDesktopAdapterStatus.PENDING_FOUNDER_VISUAL_CONFIRMATION.value,
            "pending_founder_visual_confirmation",
        )


class TestBlockedLaunchMethods(unittest.TestCase):
    def test_explorer_url_blocked(self):
        self.assertIn("explorer_url", BLOCKED_LAUNCH_METHODS)

    def test_default_browser_blocked(self):
        self.assertIn("default_browser", BLOCKED_LAUNCH_METHODS)

    def test_shell_url_open_blocked(self):
        self.assertIn("shell_url_open", BLOCKED_LAUNCH_METHODS)

    def test_generic_start_url_blocked(self):
        self.assertIn("generic_start_url", BLOCKED_LAUNCH_METHODS)

    def test_unknown_browser_blocked(self):
        self.assertIn("unknown_browser", BLOCKED_LAUNCH_METHODS)

    def test_direct_executable_not_blocked(self):
        self.assertNotIn("direct_executable", BLOCKED_LAUNCH_METHODS)


class TestActionRequestSerialization(unittest.TestCase):
    def test_to_dict_includes_all_fields(self):
        req = WindowsDesktopActionRequest(
            request_id="REQ-001",
            trace_id="TR-001",
            action_type="open_application_url",
            environment_id="local_windows_desktop",
            application_id="google_chrome_windows",
            launch_method="direct_executable",
            url="https://drive.google.com",
        )
        d = req.to_dict()
        self.assertEqual(d["request_id"], "REQ-001")
        self.assertEqual(d["environment_id"], "local_windows_desktop")
        self.assertTrue(d["no_secret_capture"])
        self.assertTrue(d["no_mutation"])


class TestActionResultSerialization(unittest.TestCase):
    def test_to_dict_includes_proof_status(self):
        result = WindowsDesktopActionResult(
            request_id="REQ-001",
            adapter_status="completed",
            visible_proof_status=WindowsDesktopProofStatus.PENDING_FOUNDER_VISUAL_CONFIRMATION.value,
        )
        d = result.to_dict()
        self.assertEqual(d["visible_proof_status"], "pending_founder_visual_confirmation")
        self.assertTrue(d["founder_visual_confirmation_required"])


class TestProofArtifact(unittest.TestCase):
    def test_default_proof_is_no_proof(self):
        proof = WindowsDesktopProofArtifact()
        self.assertEqual(proof.proof_status, WindowsDesktopProofStatus.NO_PROOF.value)
        self.assertTrue(proof.founder_visual_confirmation_required)
        self.assertFalse(proof.founder_confirmed)


class TestRelayPaths(unittest.TestCase):
    def test_to_dict(self):
        paths = WindowsDesktopRelayPaths()
        d = paths.to_dict()
        self.assertIn("relay_inbox", d)
        self.assertIn("relay_outbox", d)


if __name__ == "__main__":
    unittest.main()
