"""Tests for environment_bridge/chrome_visible_launch.py — Phase 96.8D."""

import sys

sys.path.insert(0, "/opt/OS")

import unittest
from core.environment_bridge.chrome_visible_launch import (
    ChromeLaunchMethod,
    ChromeProcessSnapshot,
    ChromeVisibleLaunchStatus,
    build_chrome_launch_command,
    evaluate_visible_chrome_launch,
    is_allowed_chrome_launch_method,
    parse_chrome_process_snapshot,
    required_chrome_executable_paths,
    visible_chrome_window_detected,
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


class TestVisibleWindowDetection(unittest.TestCase):
    def test_nonzero_handle_is_visible(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=999)]
        self.assertTrue(visible_chrome_window_detected(procs))

    def test_nonblank_title_is_visible(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_title="Google Drive")]
        self.assertTrue(visible_chrome_window_detected(procs))

    def test_zero_handle_blank_title_is_not_visible(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=0, main_window_title="")]
        self.assertFalse(visible_chrome_window_detected(procs))

    def test_empty_list_is_not_visible(self):
        self.assertFalse(visible_chrome_window_detected([]))

    def test_multiple_background_processes_not_visible(self):
        procs = [
            ChromeProcessSnapshot(pid=1, main_window_handle=0, main_window_title=""),
            ChromeProcessSnapshot(pid=2, main_window_handle=0, main_window_title=""),
            ChromeProcessSnapshot(pid=3, main_window_handle=0, main_window_title=""),
        ]
        self.assertFalse(visible_chrome_window_detected(procs))


class TestEvaluateVisibleChromeLaunch(unittest.TestCase):
    def test_visible_window_passes(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=12345)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertEqual(proof.status, ChromeVisibleLaunchStatus.VISIBLE_CHROME_LAUNCH)
        self.assertTrue(proof.visible_window_detected)

    def test_background_only_fails(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=0, main_window_title="")]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertEqual(proof.status, ChromeVisibleLaunchStatus.CHROME_BACKGROUND_PROCESS_ONLY)
        self.assertFalse(proof.visible_window_detected)
        self.assertTrue(proof.founder_visual_confirmation_required)

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
        self.assertIn("visible_window_detected", d)
        self.assertIn("founder_visual_confirmation_required", d)
        self.assertIn("status", d)


class TestVisibleLaunchProofGate(unittest.TestCase):
    def test_visible_allows_next_gate(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=12345)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertTrue(visible_launch_proof_allows_next_gate(proof))

    def test_background_blocks_next_gate(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=0)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
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
