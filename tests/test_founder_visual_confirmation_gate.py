"""Tests for founder visual confirmation gate — Phase 96.8E.

Verifies the full confirmation flow:
- Confirmation file is parsed correctly
- Confirmed true transitions to FOUNDER_CONFIRMED_VISIBLE
- Confirmed false transitions to FOUNDER_DENIED_VISIBLE
- Invalid confirmation files are rejected
- Confirmation helper builds correct structure
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import json
import tempfile
import unittest
from pathlib import Path

from core.environment_bridge.chrome_visible_launch import (
    ChromeLaunchMethod,
    ChromeProcessSnapshot,
    ChromeVisibleLaunchStatus,
    MetadataEvidence,
    apply_founder_visual_confirmation,
    evaluate_visible_chrome_launch,
    parse_founder_visual_confirmation,
    visible_launch_proof_allows_next_gate,
    CHROME_EXECUTABLE_PATHS_WSL,
)
from eos_ai.substrate.write_founder_gate_confirmation import (
    build_founder_visual_confirmation,
    write_confirmation,
)

VALID_WSL_PATH = CHROME_EXECUTABLE_PATHS_WSL[0]
DRIVE_URL = "https://drive.google.com/drive/my-drive"


class TestConfirmationFileParsing(unittest.TestCase):
    def test_valid_confirmed_true(self):
        data = {
            "response_type": "founder_visual_confirmation",
            "work_order_id": "WO-001",
            "gate": "VISIBLE_CHROME_LAUNCH",
            "confirmed": True,
            "notes": "Chrome is open",
        }
        is_valid, confirmed, notes = parse_founder_visual_confirmation(data)
        self.assertTrue(is_valid)
        self.assertTrue(confirmed)
        self.assertEqual(notes, "Chrome is open")

    def test_valid_confirmed_false(self):
        data = {
            "response_type": "founder_visual_confirmation",
            "work_order_id": "WO-001",
            "gate": "VISIBLE_CHROME_LAUNCH",
            "confirmed": False,
            "notes": "Chrome did not open",
        }
        is_valid, confirmed, notes = parse_founder_visual_confirmation(data)
        self.assertTrue(is_valid)
        self.assertFalse(confirmed)
        self.assertEqual(notes, "Chrome did not open")

    def test_wrong_response_type_rejected(self):
        data = {
            "response_type": "advisor_approval",
            "confirmed": True,
        }
        is_valid, _, _ = parse_founder_visual_confirmation(data)
        self.assertFalse(is_valid)

    def test_missing_confirmed_rejected(self):
        data = {
            "response_type": "founder_visual_confirmation",
            "work_order_id": "WO-001",
        }
        is_valid, _, _ = parse_founder_visual_confirmation(data)
        self.assertFalse(is_valid)

    def test_empty_dict_rejected(self):
        is_valid, _, _ = parse_founder_visual_confirmation({})
        self.assertFalse(is_valid)

    def test_missing_notes_defaults_empty(self):
        data = {
            "response_type": "founder_visual_confirmation",
            "confirmed": True,
        }
        is_valid, confirmed, notes = parse_founder_visual_confirmation(data)
        self.assertTrue(is_valid)
        self.assertEqual(notes, "")


class TestFounderConfirmationTransitions(unittest.TestCase):
    def _pending_proof(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=99999)]
        return evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )

    def test_confirmed_true_transitions_to_confirmed_visible(self):
        proof = self._pending_proof()
        self.assertEqual(
            proof.status, ChromeVisibleLaunchStatus.PENDING_FOUNDER_VISUAL_CONFIRMATION
        )
        proof = apply_founder_visual_confirmation(proof, True)
        self.assertEqual(proof.status, ChromeVisibleLaunchStatus.FOUNDER_CONFIRMED_VISIBLE)

    def test_confirmed_false_transitions_to_denied_visible(self):
        proof = self._pending_proof()
        proof = apply_founder_visual_confirmation(proof, False)
        self.assertEqual(proof.status, ChromeVisibleLaunchStatus.FOUNDER_DENIED_VISIBLE)

    def test_confirmed_true_allows_next_gate(self):
        proof = self._pending_proof()
        proof = apply_founder_visual_confirmation(proof, True)
        self.assertTrue(visible_launch_proof_allows_next_gate(proof))

    def test_confirmed_false_blocks_next_gate(self):
        proof = self._pending_proof()
        proof = apply_founder_visual_confirmation(proof, False)
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))

    def test_pending_blocks_next_gate(self):
        proof = self._pending_proof()
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))


class TestConfirmationHelperBuilder(unittest.TestCase):
    def test_builds_correct_structure(self):
        data = build_founder_visual_confirmation(
            work_order_id="WO-001",
            gate="VISIBLE_CHROME_LAUNCH",
            confirmed=True,
            visible_app="Google Chrome",
            notes="Chrome open",
        )
        self.assertEqual(data["response_type"], "founder_visual_confirmation")
        self.assertEqual(data["work_order_id"], "WO-001")
        self.assertEqual(data["gate"], "VISIBLE_CHROME_LAUNCH")
        self.assertTrue(data["confirmed"])
        self.assertEqual(data["visible_app"], "Google Chrome")
        self.assertIn("timestamp", data)

    def test_denied_structure(self):
        data = build_founder_visual_confirmation(
            work_order_id="WO-001",
            gate="VISIBLE_CHROME_LAUNCH",
            confirmed=False,
            notes="Not visible",
        )
        self.assertFalse(data["confirmed"])
        self.assertEqual(data["visible_app"], "")

    def test_roundtrip_through_parser(self):
        data = build_founder_visual_confirmation(
            work_order_id="WO-001",
            gate="VISIBLE_CHROME_LAUNCH",
            confirmed=True,
        )
        is_valid, confirmed, notes = parse_founder_visual_confirmation(data)
        self.assertTrue(is_valid)
        self.assertTrue(confirmed)


class TestConfirmationHelperWriter(unittest.TestCase):
    def test_writes_file_to_inbox(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inbox = Path(tmpdir) / "inbox"
            path = write_confirmation(
                work_order_id="WO-TEST-001",
                gate="VISIBLE_CHROME_LAUNCH",
                confirmed=True,
                notes="test",
                inbox_dir=inbox,
            )
            self.assertTrue(path.exists())
            data = json.loads(path.read_text())
            self.assertEqual(data["response_type"], "founder_visual_confirmation")
            self.assertTrue(data["confirmed"])
            self.assertEqual(data["work_order_id"], "WO-TEST-001")

    def test_denied_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inbox = Path(tmpdir) / "inbox"
            path = write_confirmation(
                work_order_id="WO-TEST-002",
                gate="VISIBLE_CHROME_LAUNCH",
                confirmed=False,
                notes="not visible",
                inbox_dir=inbox,
            )
            data = json.loads(path.read_text())
            self.assertFalse(data["confirmed"])


class TestFullConfirmationFlow(unittest.TestCase):
    """End-to-end: evaluate → write confirmation → parse → apply → gate check."""

    def test_full_confirmed_flow(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=99999)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))

        conf_data = build_founder_visual_confirmation(
            work_order_id="WO-001",
            gate="VISIBLE_CHROME_LAUNCH",
            confirmed=True,
            notes="Chrome open",
        )
        is_valid, confirmed, notes = parse_founder_visual_confirmation(conf_data)
        self.assertTrue(is_valid)
        self.assertTrue(confirmed)

        proof = apply_founder_visual_confirmation(proof, confirmed, notes)
        self.assertTrue(visible_launch_proof_allows_next_gate(proof))

    def test_full_denied_flow(self):
        procs = [ChromeProcessSnapshot(pid=1, main_window_handle=99999)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE, VALID_WSL_PATH, DRIVE_URL, procs
        )

        conf_data = build_founder_visual_confirmation(
            work_order_id="WO-001",
            gate="VISIBLE_CHROME_LAUNCH",
            confirmed=False,
            notes="Not visible",
        )
        is_valid, confirmed, notes = parse_founder_visual_confirmation(conf_data)
        proof = apply_founder_visual_confirmation(proof, confirmed, notes)
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))
        self.assertEqual(proof.status, ChromeVisibleLaunchStatus.FOUNDER_DENIED_VISIBLE)


if __name__ == "__main__":
    unittest.main()
