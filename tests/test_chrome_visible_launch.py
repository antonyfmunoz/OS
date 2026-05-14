"""Tests for environment_bridge/chrome_visible_launch.py — Phase 96.8E."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest
from execution.environments.chrome_visible_launch import (
    ChromeLaunchMethod,
    ChromeProcessSnapshot,
    ChromeVisibleLaunchStatus,
    MetadataEvidence,
    apply_founder_visual_confirmation,
    build_chrome_launch_command,
    classify_metadata_evidence,
    evaluate_visible_chrome_launch,
    is_allowed_chrome_launch_method,
    parse_chrome_process_snapshot,
    parse_founder_visual_confirmation,
    required_chrome_executable_paths,
    visible_launch_proof_allows_next_gate,
    CHROME_EXECUTABLE_PATHS_WSL,
    CHROME_EXECUTABLE_PATHS_WINDOWS,
)

VALID_WSL_PATH = CHROME_EXECUTABLE_PATHS_WSL[0]
VALID_WIN_PATH = CHROME_EXECUTABLE_PATHS_WINDOWS[0]
DRIVE_URL = "https://drive.google.com/drive/my-drive"


class TestRequiredPaths(unittest.TestCase):
    def test_returns_both_windows_and_wsl(self):
        paths = required_chrome_executable_paths()
        self.assertTrue(len(paths) >= 4)
        self.assertTrue(any("mnt/c" in p for p in paths))
        self.assertTrue(any("C:\\" in p for p in paths))


class TestAllowedLaunchMethod(unittest.TestCase):
    def test_direct_executable_with_valid_path(self):
        self.assertTrue(
            is_allowed_chrome_launch_method(ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH)
        )

    def test_direct_executable_with_windows_path(self):
        self.assertTrue(
            is_allowed_chrome_launch_method(ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WIN_PATH)
        )

    def test_explorer_default_is_disallowed(self):
        self.assertFalse(
            is_allowed_chrome_launch_method(ChromeLaunchMethod.EXPLORER_DEFAULT, "explorer.exe")
        )

    def test_direct_with_wrong_path_is_disallowed(self):
        self.assertFalse(
            is_allowed_chrome_launch_method(
                ChromeLaunchMethod.DIRECT_EXECUTABLE, "/usr/bin/firefox"
            )
        )

    def test_wsl_interop_with_valid_path(self):
        self.assertTrue(
            is_allowed_chrome_launch_method(ChromeLaunchMethod.WSL_INTEROP, VALID_WSL_PATH)
        )


class TestBuildChromeCommand(unittest.TestCase):
    def test_builds_with_new_window_flag(self):
        cmd = build_chrome_launch_command(DRIVE_URL, VALID_WSL_PATH)
        self.assertIn("--new-window", cmd)
        self.assertIn(DRIVE_URL, cmd)
        self.assertIn(VALID_WSL_PATH, cmd)

    def test_default_path_is_wsl(self):
        cmd = build_chrome_launch_command(DRIVE_URL)
        self.assertIn("mnt/c", cmd)


class TestParseSnapshot(unittest.TestCase):
    def test_parses_dict(self):
        snap = parse_chrome_process_snapshot(
            {
                "pid": 1234,
                "process_name": "chrome",
                "main_window_handle": 12345678,
                "main_window_title": "Google Drive",
            }
        )
        self.assertEqual(snap.pid, 1234)
        self.assertEqual(snap.main_window_handle, 12345678)
        self.assertEqual(snap.main_window_title, "Google Drive")


class TestClassifyMetadataEvidence(unittest.TestCase):
    def test_no_processes_is_none(self):
        self.assertEqual(classify_metadata_evidence([]), MetadataEvidence.NONE)

    def test_process_only_no_window(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=0, main_window_title="")]
        self.assertEqual(classify_metadata_evidence(procs), MetadataEvidence.PROCESS_DETECTED_ONLY)

    def test_nonzero_handle_is_window_metadata(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=99999)]
        self.assertEqual(
            classify_metadata_evidence(procs), MetadataEvidence.WINDOW_METADATA_DETECTED
        )

    def test_nonblank_title_is_window_metadata(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_title="Google Drive")]
        self.assertEqual(
            classify_metadata_evidence(procs), MetadataEvidence.WINDOW_METADATA_DETECTED
        )


class TestProcessMetadataDoesNotPassGate(unittest.TestCase):
    """Process/window metadata alone must NEVER pass the visible Chrome gate."""

    def test_process_existence_does_not_pass(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=0, main_window_title="")]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))
        self.assertEqual(
            proof.status, ChromeVisibleLaunchStatus.PENDING_FOUNDER_VISUAL_CONFIRMATION
        )

    def test_nonzero_handle_does_not_pass(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=99999)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))
        self.assertEqual(
            proof.status, ChromeVisibleLaunchStatus.PENDING_FOUNDER_VISUAL_CONFIRMATION
        )

    def test_nonblank_title_does_not_pass(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_title="Google Drive")]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))
        self.assertEqual(
            proof.status, ChromeVisibleLaunchStatus.PENDING_FOUNDER_VISUAL_CONFIRMATION
        )

    def test_handle_and_title_together_do_not_pass(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=99999, main_window_title="Drive")]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))

    def test_multiple_processes_with_metadata_do_not_pass(self):
        procs = [
            ChromeProcessSnapshot(pid=1, main_window_handle=99999, main_window_title="Drive"),
            ChromeProcessSnapshot(pid=2, main_window_handle=88888, main_window_title="Docs"),
        ]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))


class TestFounderConfirmation(unittest.TestCase):
    def test_founder_confirmed_true_passes(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=99999)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        proof = apply_founder_visual_confirmation(proof, True, "Chrome visible")
        self.assertTrue(visible_launch_proof_allows_next_gate(proof))
        self.assertEqual(proof.status, ChromeVisibleLaunchStatus.FOUNDER_CONFIRMED_VISIBLE)
        self.assertTrue(proof.founder_confirmed)

    def test_founder_confirmed_false_blocks(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=99999)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        proof = apply_founder_visual_confirmation(proof, False, "Not visible")
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))
        self.assertEqual(proof.status, ChromeVisibleLaunchStatus.FOUNDER_DENIED_VISIBLE)

    def test_confirmation_sets_received_flag(self):
        procs = [ChromeProcessSnapshot(pid=1)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertFalse(proof.founder_visual_confirmation_received)
        proof = apply_founder_visual_confirmation(proof, True)
        self.assertTrue(proof.founder_visual_confirmation_received)


class TestParseFounderConfirmation(unittest.TestCase):
    def test_valid_confirmed(self):
        data = {
            "response_type": "founder_visual_confirmation",
            "work_order_id": "WO-001",
            "gate": "VISIBLE_CHROME_LAUNCH",
            "confirmed": True,
            "notes": "Chrome open",
        }
        is_valid, confirmed, notes = parse_founder_visual_confirmation(data)
        self.assertTrue(is_valid)
        self.assertTrue(confirmed)
        self.assertEqual(notes, "Chrome open")

    def test_valid_denied(self):
        data = {
            "response_type": "founder_visual_confirmation",
            "confirmed": False,
            "notes": "Not visible",
        }
        is_valid, confirmed, notes = parse_founder_visual_confirmation(data)
        self.assertTrue(is_valid)
        self.assertFalse(confirmed)

    def test_wrong_response_type(self):
        data = {"response_type": "something_else", "confirmed": True}
        is_valid, _, _ = parse_founder_visual_confirmation(data)
        self.assertFalse(is_valid)

    def test_missing_confirmed_field(self):
        data = {"response_type": "founder_visual_confirmation"}
        is_valid, _, _ = parse_founder_visual_confirmation(data)
        self.assertFalse(is_valid)


class TestEvaluateVisibleChromeLaunch(unittest.TestCase):
    def test_no_processes_is_not_found(self):
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, []
        )
        self.assertEqual(proof.status, ChromeVisibleLaunchStatus.CHROME_NOT_FOUND)

    def test_explorer_launch_is_disallowed(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=12345)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.EXPLORER_DEFAULT, "explorer.exe", DRIVE_URL, procs
        )
        self.assertEqual(proof.status, ChromeVisibleLaunchStatus.LAUNCH_METHOD_DISALLOWED)

    def test_processes_found_goes_to_pending(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=0)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertEqual(
            proof.status, ChromeVisibleLaunchStatus.PENDING_FOUNDER_VISUAL_CONFIRMATION
        )
        self.assertTrue(proof.founder_visual_confirmation_required)

    def test_proof_to_dict_has_all_fields(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=12345)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        d = proof.to_dict()
        self.assertIn("launch_method", d)
        self.assertIn("executable_path", d)
        self.assertIn("requested_url", d)
        self.assertIn("process_ids", d)
        self.assertIn("main_window_handle_values", d)
        self.assertIn("main_window_titles", d)
        self.assertIn("metadata_evidence", d)
        self.assertIn("founder_visual_confirmation_required", d)
        self.assertIn("founder_visual_confirmation_received", d)
        self.assertIn("founder_confirmed", d)
        self.assertIn("status", d)


class TestVisibleLaunchProofGate(unittest.TestCase):
    def test_pending_blocks_next_gate(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=12345)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))

    def test_founder_confirmed_allows_next_gate(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=12345)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        proof = apply_founder_visual_confirmation(proof, True)
        self.assertTrue(visible_launch_proof_allows_next_gate(proof))

    def test_founder_denied_blocks_next_gate(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=12345)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        proof = apply_founder_visual_confirmation(proof, False)
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))

    def test_not_found_blocks_next_gate(self):
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, []
        )
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))

    def test_disallowed_method_blocks_next_gate(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=12345)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.EXPLORER_DEFAULT, "explorer.exe", DRIVE_URL, procs
        )
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))


if __name__ == "__main__":
    unittest.main()
