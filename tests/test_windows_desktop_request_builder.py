"""Tests for Windows Interactive Desktop request builder — Phase 96.8H.

Verifies:
1. W0 Chrome request has exact Chrome executable binding.
2. Request has correct environment.
3. Request has correct execution surface.
4. Request blocks all disallowed launch methods.
5. Request uses direct_executable only.
6. Ping request is valid.
7. Request has trace_id.
8. Request has no_secret_capture and no_mutation.
9. Dict serialization is correct.
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest

from execution.environments.windows_desktop_adapter_contracts import (
    BLOCKED_LAUNCH_METHODS,
    WindowsDesktopActionType,
)
from execution.environments.windows_desktop_request_builder import (
    CHROME_EXECUTABLE_PATH_WINDOWS,
    GOOGLE_DRIVE_URL,
    build_ping_request,
    build_w0_chrome_open_request,
    request_to_json,
)
from execution.environments.windows_desktop_adapter_validator import (
    validate_desktop_action_request,
)


class TestW0ChromeRequestBinding(unittest.TestCase):
    def test_chrome_executable_path(self):
        req = build_w0_chrome_open_request()
        self.assertEqual(req.executable_path, CHROME_EXECUTABLE_PATH_WINDOWS)

    def test_application_id(self):
        req = build_w0_chrome_open_request()
        self.assertEqual(req.application_id, "google_chrome_windows")

    def test_launch_method_is_direct_executable(self):
        req = build_w0_chrome_open_request()
        self.assertEqual(req.launch_method, "direct_executable")

    def test_url_is_google_drive(self):
        req = build_w0_chrome_open_request()
        self.assertEqual(req.url, GOOGLE_DRIVE_URL)

    def test_custom_url(self):
        req = build_w0_chrome_open_request(url="https://docs.google.com")
        self.assertEqual(req.url, "https://docs.google.com")


class TestW0ChromeRequestEnvironment(unittest.TestCase):
    def test_environment_id(self):
        req = build_w0_chrome_open_request()
        self.assertEqual(req.environment_id, "local_windows_desktop")

    def test_execution_surface_id(self):
        req = build_w0_chrome_open_request()
        self.assertEqual(req.execution_surface_id, "windows_interactive_desktop_adapter")


class TestBlockedLaunchMethodsIncluded(unittest.TestCase):
    def test_all_blocked_methods_present(self):
        req = build_w0_chrome_open_request()
        for method in BLOCKED_LAUNCH_METHODS:
            self.assertIn(method, req.blocked_launch_methods)


class TestSafetyFlags(unittest.TestCase):
    def test_no_secret_capture(self):
        req = build_w0_chrome_open_request()
        self.assertTrue(req.no_secret_capture)

    def test_no_mutation(self):
        req = build_w0_chrome_open_request()
        self.assertTrue(req.no_mutation)


class TestTraceId(unittest.TestCase):
    def test_trace_id_present(self):
        req = build_w0_chrome_open_request()
        self.assertTrue(req.trace_id)

    def test_custom_trace_id(self):
        req = build_w0_chrome_open_request(trace_id="TR-CUSTOM")
        self.assertEqual(req.trace_id, "TR-CUSTOM")


class TestPingRequest(unittest.TestCase):
    def test_ping_action_type(self):
        req = build_ping_request()
        self.assertEqual(req.action_type, WindowsDesktopActionType.PING.value)

    def test_ping_environment(self):
        req = build_ping_request()
        self.assertEqual(req.environment_id, "local_windows_desktop")


class TestRequestValidation(unittest.TestCase):
    def test_w0_chrome_request_passes_validation(self):
        req = build_w0_chrome_open_request()
        result = validate_desktop_action_request(req)
        self.assertTrue(result.valid, f"Errors: {result.errors}")


class TestDictSerialization(unittest.TestCase):
    def test_request_to_json(self):
        req = build_w0_chrome_open_request()
        d = request_to_json(req)
        self.assertIsInstance(d, dict)
        self.assertEqual(d["application_id"], "google_chrome_windows")
        self.assertEqual(d["launch_method"], "direct_executable")


if __name__ == "__main__":
    unittest.main()
