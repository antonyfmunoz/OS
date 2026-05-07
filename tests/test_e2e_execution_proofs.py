"""Tests for E2E execution proof artifacts -- Phase 96.8Q.

Validates proof artifact schema shape, required fields,
and absence of secrets.
"""

import sys

sys.path.insert(0, "/opt/OS")

import json
import unittest
from pathlib import Path

PROOF_DIR = Path("/opt/OS/data/runtime/e2e_execution_proofs")


class TestPingProofArtifact(unittest.TestCase):
    def setUp(self):
        path = PROOF_DIR / "phase968q_discord_ping_proof.json"
        with open(path) as f:
            self.proof = json.load(f)

    def test_has_command(self):
        self.assertEqual(self.proof["command"], "!ping")

    def test_has_interface(self):
        self.assertEqual(self.proof["interface"], "discord_interface_adapter_v1")

    def test_has_routing_section(self):
        self.assertIn("routing", self.proof)
        self.assertIn("work_packet", self.proof["routing"])
        self.assertIn("router_decision", self.proof["routing"])

    def test_has_execution_section(self):
        self.assertIn("execution", self.proof)
        self.assertIn("daemon", self.proof["execution"])
        self.assertIn("relay", self.proof["execution"])

    def test_has_proof_section(self):
        self.assertIn("proof", self.proof)
        self.assertEqual(self.proof["proof"]["proof_status"], "completed")

    def test_has_safety_section(self):
        self.assertIn("safety", self.proof)
        self.assertFalse(self.proof["safety"]["secrets_captured"])
        self.assertFalse(self.proof["safety"]["memory_promoted"])

    def test_no_secrets_in_artifact(self):
        raw = json.dumps(self.proof).lower()
        for keyword in ["password", "api_key", "secret_key", "bearer", "token_value"]:
            self.assertNotIn(keyword, raw)


class TestChromeVisibleProofArtifact(unittest.TestCase):
    def setUp(self):
        path = PROOF_DIR / "phase968q_discord_chrome_visible_proof.json"
        with open(path) as f:
            self.proof = json.load(f)

    def test_has_command(self):
        self.assertEqual(self.proof["command"], "!chrome")

    def test_has_routing_with_gui_capability(self):
        cap = self.proof["routing"]["router_decision"]["capability_matched"]
        self.assertEqual(cap, "windows_gui_execution")

    def test_has_founder_confirmation(self):
        self.assertIn("founder_confirmation", self.proof)
        self.assertTrue(self.proof["founder_confirmation"]["chrome_visibly_opened"])
        self.assertTrue(self.proof["founder_confirmation"]["drive_homepage_loaded"])

    def test_drive_contents_not_accessed(self):
        self.assertFalse(self.proof["founder_confirmation"]["drive_contents_accessed"])
        self.assertFalse(self.proof["founder_confirmation"]["docs_contents_accessed"])

    def test_safety_section_complete(self):
        safety = self.proof["safety"]
        self.assertTrue(safety["chrome_opened"])
        self.assertTrue(safety["drive_homepage_visible"])
        self.assertFalse(safety["drive_contents_read"])
        self.assertFalse(safety["docs_contents_read"])
        self.assertFalse(safety["secrets_captured"])
        self.assertFalse(safety["tokens_captured"])
        self.assertFalse(safety["cookies_captured"])
        self.assertFalse(safety["screenshots_captured"])
        self.assertFalse(safety["memory_promoted"])
        self.assertFalse(safety["autonomous_planning"])

    def test_safe_url_in_payload(self):
        url = self.proof["routing"]["work_packet"]["payload_url"]
        self.assertEqual(url, "https://drive.google.com/drive/my-drive")

    def test_no_secrets_in_artifact(self):
        raw = json.dumps(self.proof).lower()
        for keyword in ["password", "api_key", "secret_key", "bearer", "token_value"]:
            self.assertNotIn(keyword, raw)


class TestChainSummaryArtifact(unittest.TestCase):
    def setUp(self):
        path = PROOF_DIR / "phase968q_execution_chain_summary.json"
        with open(path) as f:
            self.summary = json.load(f)

    def test_has_chain_with_six_layers(self):
        self.assertIn("chain", self.summary)
        self.assertEqual(len(self.summary["chain"]), 6)

    def test_all_layers_proven(self):
        for layer in self.summary["chain"]:
            self.assertTrue(layer["proven"], f"layer {layer['layer']} not proven")

    def test_has_commands_proven(self):
        self.assertIn("commands_proven", self.summary)
        self.assertTrue(self.summary["commands_proven"]["ping"]["tested"])
        self.assertTrue(self.summary["commands_proven"]["chrome"]["tested"])
        self.assertTrue(self.summary["commands_proven"]["chrome"]["founder_confirmed"])

    def test_has_environments(self):
        envs = self.summary["environments_used"]
        self.assertIn("vps_tmux", envs)
        self.assertIn("local_wsl", envs)
        self.assertIn("local_windows_desktop", envs)
        self.assertFalse(envs["vps_tmux"]["can_own_gui"])
        self.assertFalse(envs["local_wsl"]["can_own_gui"])
        self.assertTrue(envs["local_windows_desktop"]["can_own_gui"])

    def test_proven_boundaries(self):
        b = self.summary["proven_boundaries"]
        self.assertTrue(b["chrome_opened"])
        self.assertTrue(b["drive_homepage_loaded"])
        self.assertFalse(b["drive_docs_contents_accessed"])
        self.assertFalse(b["secrets_captured"])
        self.assertFalse(b["memory_promoted"])

    def test_next_gate(self):
        self.assertEqual(self.summary["next_gate"], "W0_DRIVE_DOCS_INTERACTION_PROOF")

    def test_no_secrets_in_artifact(self):
        raw = json.dumps(self.summary).lower()
        for keyword in ["password", "api_key", "secret_key", "bearer", "token_value"]:
            self.assertNotIn(keyword, raw)


if __name__ == "__main__":
    unittest.main()
