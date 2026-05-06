"""Tests for local worker visible Chrome gate — Phase 96.8D.

Verifies that:
- VERIFY_ACTIVE_GOOGLE_ACCOUNT cannot be reached without visible Chrome proof
- Chrome process with MainWindowHandle=0 does NOT pass
- Direct Chrome executable is the required method
- explorer/default-browser launch is rejected
- Worker validates packet routing fields before execution
"""

import sys

sys.path.insert(0, "/opt/OS")

import unittest
from core.environment_bridge.chrome_visible_launch import (
    ChromeLaunchMethod,
    ChromeProcessSnapshot,
    ChromeVisibleLaunchStatus,
    evaluate_visible_chrome_launch,
    visible_launch_proof_allows_next_gate,
    CHROME_EXECUTABLE_PATHS_WSL,
)
from eos_ai.substrate.local_worker_auto_loop import (
    validate_wo_001_packet,
    WO_001_ID,
    WO_001_ACCOUNT,
)

VALID_WSL_PATH = CHROME_EXECUTABLE_PATHS_WSL[0]
DRIVE_URL = "https://drive.google.com/drive/my-drive"


class TestVerifyAccountGateRequiresVisibleChrome(unittest.TestCase):
    """VERIFY_ACTIVE_GOOGLE_ACCOUNT must not be reachable without visible window proof."""

    def test_visible_window_allows_account_gate(self):
        procs = [ChromeProcessSnapshot(pid=100, main_window_handle=99999)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertTrue(visible_launch_proof_allows_next_gate(proof))

    def test_background_process_blocks_account_gate(self):
        procs = [
            ChromeProcessSnapshot(pid=100, main_window_handle=0, main_window_title=""),
            ChromeProcessSnapshot(pid=101, main_window_handle=0, main_window_title=""),
        ]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))
        self.assertEqual(proof.status, ChromeVisibleLaunchStatus.CHROME_BACKGROUND_PROCESS_ONLY)

    def test_no_chrome_blocks_account_gate(self):
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, []
        )
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))
        self.assertEqual(proof.status, ChromeVisibleLaunchStatus.CHROME_NOT_FOUND)


class TestExplorerDefaultBrowserNotValid(unittest.TestCase):
    """explorer.exe / default-browser routing must not pass for W0-001."""

    def test_explorer_blocked_even_with_visible_window(self):
        procs = [ChromeProcessSnapshot(pid=100, main_window_handle=99999)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.EXPLORER_DEFAULT, "explorer.exe", DRIVE_URL, procs
        )
        self.assertEqual(proof.status, ChromeVisibleLaunchStatus.LAUNCH_METHOD_DISALLOWED)
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))

    def test_powershell_start_without_chrome_path_blocked(self):
        procs = [ChromeProcessSnapshot(pid=100, main_window_handle=99999)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.POWERSHELL_START, "Start-Process", DRIVE_URL, procs
        )
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))


class TestDirectChromeExecutableRequired(unittest.TestCase):
    """Only direct Chrome executable path is the required method."""

    def test_direct_executable_with_correct_path(self):
        procs = [ChromeProcessSnapshot(pid=100, main_window_handle=99999)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertEqual(proof.status, ChromeVisibleLaunchStatus.VISIBLE_CHROME_LAUNCH)

    def test_direct_executable_with_wrong_path_blocked(self):
        procs = [ChromeProcessSnapshot(pid=100, main_window_handle=99999)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, "/usr/bin/chromium", DRIVE_URL, procs
        )
        self.assertEqual(proof.status, ChromeVisibleLaunchStatus.LAUNCH_METHOD_DISALLOWED)


class TestWorkerPacketValidation(unittest.TestCase):
    """Worker must reject packets missing required routing fields."""

    def _valid_packet(self) -> dict:
        return {
            "work_order_id": WO_001_ID,
            "target_account": WO_001_ACCOUNT,
            "worker_mode": "auto",
            "playwright_enabled": False,
            "approval_routing": "advisor_relay",
            "preferred_backend": "GUI_COMPUTER_USE",
        }

    def test_valid_packet_passes(self):
        errors = validate_wo_001_packet(self._valid_packet())
        self.assertEqual(errors, [])

    def test_missing_target_account_fails(self):
        pkt = self._valid_packet()
        del pkt["target_account"]
        errors = validate_wo_001_packet(pkt)
        self.assertTrue(any("target_account" in e for e in errors))

    def test_missing_worker_mode_fails(self):
        pkt = self._valid_packet()
        del pkt["worker_mode"]
        errors = validate_wo_001_packet(pkt)
        self.assertTrue(any("Worker mode" in e for e in errors))

    def test_missing_approval_routing_fails(self):
        pkt = self._valid_packet()
        del pkt["approval_routing"]
        errors = validate_wo_001_packet(pkt)
        self.assertTrue(any("approval routing" in e for e in errors))

    def test_missing_preferred_backend_fails(self):
        pkt = self._valid_packet()
        del pkt["preferred_backend"]
        errors = validate_wo_001_packet(pkt)
        self.assertTrue(any("backend" in e.lower() for e in errors))

    def test_playwright_enabled_fails(self):
        pkt = self._valid_packet()
        pkt["playwright_enabled"] = True
        errors = validate_wo_001_packet(pkt)
        self.assertTrue(any("Playwright" in e for e in errors))

    def test_worker_stops_safely_when_proof_missing(self):
        """Worker's evaluate_visible_chrome_launch returns non-passing status
        when no visible window exists, preventing VERIFY_ACTIVE_GOOGLE_ACCOUNT."""
        procs = [ChromeProcessSnapshot(pid=100, main_window_handle=0)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))
        self.assertIn("BACKGROUND", proof.status.value.upper())


if __name__ == "__main__":
    unittest.main()
