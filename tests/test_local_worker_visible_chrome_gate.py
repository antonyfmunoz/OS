"""Tests for local worker visible Chrome gate — Phase 96.8E.

Verifies that:
- VERIFY_ACTIVE_GOOGLE_ACCOUNT cannot be reached without founder confirmation
- Process metadata alone does not pass the gate
- MainWindowHandle nonzero does not pass the gate
- MainWindowTitle nonblank does not pass the gate
- Founder confirmed=true passes the gate
- Founder confirmed=false blocks the gate
- Worker validates packet routing fields before execution
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest
from execution.environments.chrome_visible_launch import (
    ChromeLaunchMethod,
    ChromeProcessSnapshot,
    ChromeVisibleLaunchStatus,
    apply_founder_visual_confirmation,
    evaluate_visible_chrome_launch,
    visible_launch_proof_allows_next_gate,
    CHROME_EXECUTABLE_PATHS_WSL,
)
from runtime.substrate.local_worker_auto_loop import (
    validate_wo_001_packet,
    WO_001_ID,
    WO_001_ACCOUNT,
)
from execution.environments.execution_binding_contracts import build_w0_chrome_gws_binding
from execution.environments.w0_packet_builder import build_w0_001_packet

VALID_WSL_PATH = CHROME_EXECUTABLE_PATHS_WSL[0]
DRIVE_URL = "https://drive.google.com/drive/my-drive"


class TestVerifyAccountGateRequiresFounderConfirmation(unittest.TestCase):
    """VERIFY_ACTIVE_GOOGLE_ACCOUNT must not be reachable without founder confirmation."""

    def test_metadata_alone_blocks_account_gate(self):
        procs = [ChromeProcessSnapshot(pid=100, main_window_handle=99999)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))
        self.assertEqual(
            proof.status, ChromeVisibleLaunchStatus.PENDING_FOUNDER_VISUAL_CONFIRMATION
        )

    def test_founder_confirmed_allows_account_gate(self):
        procs = [ChromeProcessSnapshot(pid=100, main_window_handle=99999)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        proof = apply_founder_visual_confirmation(proof, True, "Chrome open")
        self.assertTrue(visible_launch_proof_allows_next_gate(proof))

    def test_founder_denied_blocks_account_gate(self):
        procs = [ChromeProcessSnapshot(pid=100, main_window_handle=99999)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        proof = apply_founder_visual_confirmation(proof, False, "Not visible")
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))

    def test_background_process_blocks_account_gate(self):
        procs = [
            ChromeProcessSnapshot(pid=100, main_window_handle=0, main_window_title=""),
            ChromeProcessSnapshot(pid=101, main_window_handle=0, main_window_title=""),
        ]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))

    def test_no_chrome_blocks_account_gate(self):
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, []
        )
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))


class TestExplorerDefaultBrowserNotValid(unittest.TestCase):
    def test_explorer_blocked_even_with_visible_metadata(self):
        procs = [ChromeProcessSnapshot(pid=100, main_window_handle=99999)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.EXPLORER_DEFAULT, "explorer.exe", DRIVE_URL, procs
        )
        self.assertEqual(proof.status, ChromeVisibleLaunchStatus.LAUNCH_METHOD_DISALLOWED)
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))


class TestDirectChromeExecutableRequired(unittest.TestCase):
    def test_direct_executable_with_correct_path_goes_to_pending(self):
        procs = [ChromeProcessSnapshot(pid=100, main_window_handle=99999)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertEqual(
            proof.status, ChromeVisibleLaunchStatus.PENDING_FOUNDER_VISUAL_CONFIRMATION
        )

    def test_direct_executable_with_wrong_path_blocked(self):
        procs = [ChromeProcessSnapshot(pid=100, main_window_handle=99999)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, "/usr/bin/chromium", DRIVE_URL, procs
        )
        self.assertEqual(proof.status, ChromeVisibleLaunchStatus.LAUNCH_METHOD_DISALLOWED)


class TestWorkerPacketValidation(unittest.TestCase):
    def _valid_packet(self) -> dict:
        full = build_w0_001_packet()
        return {
            "work_order_id": WO_001_ID,
            "target_account": WO_001_ACCOUNT,
            "worker_mode": "auto",
            "playwright_enabled": False,
            "approval_routing": "advisor_relay",
            "preferred_backend": "GUI_COMPUTER_USE",
            "execution_binding": build_w0_chrome_gws_binding().to_dict(),
            "coherence_envelope": full["coherence_envelope"],
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


class TestWorkerWritesPendingConfirmationGate(unittest.TestCase):
    """Worker must stop at pending_founder_visual_confirmation after launch."""

    def test_evaluate_always_returns_pending_when_processes_found(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=99999, main_window_title="Drive")]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertEqual(
            proof.status, ChromeVisibleLaunchStatus.PENDING_FOUNDER_VISUAL_CONFIRMATION
        )
        self.assertTrue(proof.founder_visual_confirmation_required)
        self.assertFalse(proof.founder_visual_confirmation_received)


if __name__ == "__main__":
    unittest.main()
