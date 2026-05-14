"""Tests for Windows Interactive Desktop Adapter validator — Phase 96.8H.

Verifies:
1. Valid Chrome request passes.
2. Missing environment fails.
3. Wrong environment fails.
4. Missing execution surface fails.
5. WSL/tmux as final GUI authority fails.
6. Windows desktop adapter as GUI actuator passes.
7. Missing application fails.
8. Wrong application fails for W0 Chrome.
9. explorer_url launch method fails.
10. default_browser launch method fails.
11. generic shell URL open fails.
12. direct_executable launch method passes.
13. Missing proof contract fails.
14. Missing trace_id fails.
15. Missing URL for open_application_url fails.
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest

from execution.environments.windows_desktop_adapter_contracts import (
    BLOCKED_LAUNCH_METHODS,
    WindowsDesktopActionRequest,
    WindowsDesktopActionType,
)
from execution.environments.windows_desktop_adapter_validator import (
    validate_desktop_action_request,
    validate_desktop_action_request_dict,
)


def _valid_chrome_request() -> WindowsDesktopActionRequest:
    return WindowsDesktopActionRequest(
        request_id="REQ-TEST-001",
        trace_id="TR-TEST-001",
        work_order_id="WO-TEST",
        action_type=WindowsDesktopActionType.OPEN_APPLICATION_URL.value,
        environment_id="local_windows_desktop",
        execution_surface_id="windows_interactive_desktop_adapter",
        application_id="google_chrome_windows",
        executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        launch_method="direct_executable",
        url="https://drive.google.com/drive/my-drive",
        blocked_launch_methods=sorted(BLOCKED_LAUNCH_METHODS),
        proof_required="founder_visual_confirmation",
    )


class TestValidChromeRequestPasses(unittest.TestCase):
    def test_valid_request_passes(self):
        result = validate_desktop_action_request(_valid_chrome_request())
        self.assertTrue(result.valid, f"Errors: {result.errors}")


class TestEnvironmentValidation(unittest.TestCase):
    def test_missing_environment_fails(self):
        req = _valid_chrome_request()
        req.environment_id = ""
        result = validate_desktop_action_request(req)
        self.assertFalse(result.valid)
        self.assertTrue(any("WRONG_ENVIRONMENT" in e for e in result.errors))

    def test_wrong_environment_fails(self):
        req = _valid_chrome_request()
        req.environment_id = "linux_server"
        result = validate_desktop_action_request(req)
        self.assertFalse(result.valid)
        self.assertTrue(any("WRONG_ENVIRONMENT" in e for e in result.errors))


class TestExecutionSurfaceValidation(unittest.TestCase):
    def test_missing_surface_fails(self):
        req = _valid_chrome_request()
        req.execution_surface_id = ""
        result = validate_desktop_action_request(req)
        self.assertFalse(result.valid)
        self.assertTrue(any("WRONG_EXECUTION_SURFACE" in e for e in result.errors))

    def test_wsl_as_gui_surface_fails(self):
        req = _valid_chrome_request()
        req.execution_surface_id = "wsl_tmux_worker"
        result = validate_desktop_action_request(req)
        self.assertFalse(result.valid)

    def test_windows_adapter_as_gui_surface_passes(self):
        req = _valid_chrome_request()
        req.execution_surface_id = "windows_interactive_desktop_adapter"
        result = validate_desktop_action_request(req)
        self.assertTrue(result.valid, f"Errors: {result.errors}")

    def test_powershell_relay_surface_passes(self):
        req = _valid_chrome_request()
        req.execution_surface_id = "windows_powershell_relay"
        result = validate_desktop_action_request(req)
        self.assertTrue(result.valid, f"Errors: {result.errors}")


class TestApplicationValidation(unittest.TestCase):
    def test_missing_application_fails(self):
        req = _valid_chrome_request()
        req.application_id = ""
        result = validate_desktop_action_request(req)
        self.assertFalse(result.valid)
        self.assertTrue(any("WRONG_APPLICATION" in e for e in result.errors))

    def test_wrong_application_fails(self):
        req = _valid_chrome_request()
        req.application_id = "microsoft_edge"
        result = validate_desktop_action_request(req)
        self.assertFalse(result.valid)
        self.assertTrue(any("WRONG_APPLICATION" in e for e in result.errors))


class TestLaunchMethodValidation(unittest.TestCase):
    def test_explorer_url_fails(self):
        req = _valid_chrome_request()
        req.launch_method = "explorer_url"
        result = validate_desktop_action_request(req)
        self.assertFalse(result.valid)

    def test_default_browser_fails(self):
        req = _valid_chrome_request()
        req.launch_method = "default_browser"
        result = validate_desktop_action_request(req)
        self.assertFalse(result.valid)

    def test_generic_shell_url_open_fails(self):
        req = _valid_chrome_request()
        req.launch_method = "shell_url_open"
        result = validate_desktop_action_request(req)
        self.assertFalse(result.valid)

    def test_generic_start_url_fails(self):
        req = _valid_chrome_request()
        req.launch_method = "generic_start_url"
        result = validate_desktop_action_request(req)
        self.assertFalse(result.valid)

    def test_direct_executable_passes(self):
        req = _valid_chrome_request()
        result = validate_desktop_action_request(req)
        self.assertTrue(result.valid, f"Errors: {result.errors}")


class TestProofContractValidation(unittest.TestCase):
    def test_missing_proof_contract_fails(self):
        req = _valid_chrome_request()
        req.proof_required = ""
        result = validate_desktop_action_request(req)
        self.assertFalse(result.valid)
        self.assertTrue(any("MISSING_PROOF_CONTRACT" in e for e in result.errors))


class TestTraceIdValidation(unittest.TestCase):
    def test_missing_trace_id_fails(self):
        req = _valid_chrome_request()
        req.trace_id = ""
        result = validate_desktop_action_request(req)
        self.assertFalse(result.valid)
        self.assertTrue(any("MISSING_TRACE_ID" in e for e in result.errors))


class TestMissingUrlForOpenApplication(unittest.TestCase):
    def test_missing_url_fails(self):
        req = _valid_chrome_request()
        req.url = ""
        result = validate_desktop_action_request(req)
        self.assertFalse(result.valid)
        self.assertTrue(any("MISSING_URL" in e for e in result.errors))


class TestDictValidation(unittest.TestCase):
    def test_valid_dict_passes(self):
        result = validate_desktop_action_request_dict(_valid_chrome_request().to_dict())
        self.assertTrue(result.valid, f"Errors: {result.errors}")

    def test_invalid_dict_fails(self):
        d = _valid_chrome_request().to_dict()
        d["environment_id"] = "wrong"
        result = validate_desktop_action_request_dict(d)
        self.assertFalse(result.valid)


if __name__ == "__main__":
    unittest.main()
