"""Tests for W0 execution binding integration — Phase 96.8F.

Verifies that:
- W0 packet builder emits full execution_binding with all 6 layers
- Packet validator rejects W0 packets missing execution_binding
- Packet validator rejects W0 packets with invalid execution_binding
- Local worker validates execution_binding from packet
- VERIFY_ACTIVE_GOOGLE_ACCOUNT remains blocked until visible Chrome
  founder confirmation
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest

from execution.environments.w0_packet_builder import (
    build_w0_001_packet,
    w0_001_packet_has_required_routing,
)
from execution.environments.packet_validator import (
    PacketValidationStatus,
    validate_w0_packet_dict,
)
from execution.environments.execution_binding_contracts import (
    ApplicationLaunchMethod,
    DISALLOWED_CHROME_LAUNCH_METHODS,
)
from execution.environments.execution_binding_validator import (
    validate_execution_binding_dict,
)
from runtime.substrate.local_worker_auto_loop import (
    validate_wo_001_packet,
    validate_execution_binding_from_packet,
)
from execution.environments.chrome_visible_launch import (
    ChromeLaunchMethod,
    ChromeProcessSnapshot,
    ChromeVisibleLaunchStatus,
    apply_founder_visual_confirmation,
    evaluate_visible_chrome_launch,
    visible_launch_proof_allows_next_gate,
    CHROME_EXECUTABLE_PATHS_WSL,
)


class TestW0PacketBuilderEmitsBinding(unittest.TestCase):
    def test_packet_has_execution_binding(self):
        pkt = build_w0_001_packet()
        self.assertIn("execution_binding", pkt)
        self.assertIsInstance(pkt["execution_binding"], dict)

    def test_binding_has_environment(self):
        pkt = build_w0_001_packet()
        env = pkt["execution_binding"]["environment"]
        self.assertEqual(env["environment_id"], "local_windows_desktop")
        self.assertEqual(env["environment_type"], "windows_desktop")
        self.assertEqual(env["environment_authority"], "interactive_user_session_required")

    def test_binding_has_execution_surfaces(self):
        pkt = build_w0_001_packet()
        surfaces = pkt["execution_binding"]["execution_surfaces"]
        self.assertEqual(len(surfaces), 2)
        ids = [s["execution_surface_id"] for s in surfaces]
        self.assertIn("wsl_tmux_worker", ids)
        self.assertIn("windows_powershell_relay", ids)

    def test_binding_has_application(self):
        pkt = build_w0_001_packet()
        app = pkt["execution_binding"]["application"]
        self.assertEqual(app["application_id"], "google_chrome_windows")
        self.assertEqual(app["application_name"], "Google Chrome")
        self.assertEqual(app["launch_method"], "direct_executable")
        self.assertIn("explorer_url", app["disallowed_launch_methods"])
        self.assertIn("default_browser", app["disallowed_launch_methods"])

    def test_binding_has_target_services(self):
        pkt = build_w0_001_packet()
        services = pkt["execution_binding"]["target_services"]
        ids = [s["target_service_id"] for s in services]
        self.assertIn("google_drive", ids)
        self.assertIn("google_docs", ids)
        for svc in services:
            self.assertEqual(svc["target_service_family"], "google_workspace")

    def test_binding_has_capabilities(self):
        pkt = build_w0_001_packet()
        caps = pkt["execution_binding"]["capabilities"]
        cap_ids = [c["capability_id"] for c in caps]
        self.assertIn("browser.open_url_in_application", cap_ids)
        self.assertIn("google_drive.read_file_inventory", cap_ids)
        self.assertIn("google_docs.extract_tabs", cap_ids)

    def test_binding_has_proof(self):
        pkt = build_w0_001_packet()
        proof = pkt["execution_binding"]["proof"]
        self.assertEqual(proof["proof_level_required"], "founder_visual_confirmation")
        self.assertTrue(proof["founder_confirmation_required"])
        self.assertIn("process_exists_only", proof["blocked_evidence"])
        self.assertIn("window_metadata_only", proof["blocked_evidence"])

    def test_binding_passes_dict_validation(self):
        pkt = build_w0_001_packet()
        result = validate_execution_binding_dict(pkt["execution_binding"])
        self.assertTrue(result.valid, f"Errors: {result.errors}")

    def test_wsl_tmux_is_orchestrator_not_gui_actuator(self):
        pkt = build_w0_001_packet()
        for surf in pkt["execution_binding"]["execution_surfaces"]:
            if surf["execution_surface_type"] in ("wsl", "tmux"):
                self.assertNotEqual(
                    surf["execution_surface_role"],
                    "gui_actuator",
                    f"{surf['execution_surface_type']} must not be gui_actuator",
                )

    def test_powershell_is_gui_actuator(self):
        pkt = build_w0_001_packet()
        ps_surfaces = [
            s
            for s in pkt["execution_binding"]["execution_surfaces"]
            if s["execution_surface_type"] == "powershell"
        ]
        self.assertTrue(len(ps_surfaces) > 0)
        for s in ps_surfaces:
            self.assertEqual(s["execution_surface_role"], "gui_actuator")


class TestPacketValidatorRejectsInvalidBinding(unittest.TestCase):
    def test_missing_execution_binding_fails(self):
        pkt = build_w0_001_packet()
        del pkt["execution_binding"]
        result = validate_w0_packet_dict(pkt)
        self.assertFalse(result.can_execute)
        self.assertEqual(result.status, PacketValidationStatus.MISSING_EXECUTION_BINDING)

    def test_empty_execution_binding_fails(self):
        pkt = build_w0_001_packet()
        pkt["execution_binding"] = {}
        result = validate_w0_packet_dict(pkt)
        self.assertFalse(result.can_execute)

    def test_missing_application_in_binding_fails(self):
        pkt = build_w0_001_packet()
        pkt["execution_binding"]["application"] = {}
        result = validate_w0_packet_dict(pkt)
        self.assertFalse(result.can_execute)

    def test_missing_target_services_in_binding_fails(self):
        pkt = build_w0_001_packet()
        pkt["execution_binding"]["target_services"] = []
        result = validate_w0_packet_dict(pkt)
        self.assertFalse(result.can_execute)

    def test_missing_capabilities_in_binding_fails(self):
        pkt = build_w0_001_packet()
        pkt["execution_binding"]["capabilities"] = []
        result = validate_w0_packet_dict(pkt)
        self.assertFalse(result.can_execute)

    def test_valid_packet_passes(self):
        pkt = build_w0_001_packet()
        result = validate_w0_packet_dict(pkt)
        self.assertTrue(result.can_execute)


class TestLocalWorkerValidatesBinding(unittest.TestCase):
    def test_packet_with_binding_passes(self):
        pkt = build_w0_001_packet()
        errors = validate_wo_001_packet(pkt)
        self.assertEqual(errors, [])

    def test_packet_without_binding_fails(self):
        pkt = build_w0_001_packet()
        del pkt["execution_binding"]
        errors = validate_wo_001_packet(pkt)
        self.assertTrue(any("execution_binding" in e for e in errors))

    def test_packet_with_empty_binding_fails(self):
        pkt = build_w0_001_packet()
        pkt["execution_binding"] = {}
        errors = validate_wo_001_packet(pkt)
        self.assertTrue(len(errors) > 0)

    def test_binding_with_wsl_gui_actuator_fails(self):
        pkt = build_w0_001_packet()
        pkt["execution_binding"]["execution_surfaces"] = [
            {
                "execution_surface_id": "wsl_worker",
                "execution_surface_type": "wsl",
                "execution_surface_role": "gui_actuator",
            }
        ]
        errors = validate_execution_binding_from_packet(pkt)
        self.assertTrue(any("gui_actuator" in e for e in errors))

    def test_binding_with_wrong_service_family_fails(self):
        pkt = build_w0_001_packet()
        pkt["execution_binding"]["target_services"] = [
            {
                "target_service_id": "google_drive",
                "target_service_family": "local_filesystem",
                "service_url": "https://drive.google.com",
                "service_capabilities": [],
            }
        ]
        errors = validate_execution_binding_from_packet(pkt)
        self.assertTrue(any("google_workspace" in e for e in errors))


class TestVerifyAccountGateStillBlockedWithBinding(unittest.TestCase):
    """VERIFY_ACTIVE_GOOGLE_ACCOUNT remains blocked until founder confirmation,
    even with full execution binding present."""

    def test_metadata_alone_still_blocks(self):
        procs = [ChromeProcessSnapshot(pid=100, main_window_handle=99999)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE,
            CHROME_EXECUTABLE_PATHS_WSL[0],
            "https://drive.google.com/drive/my-drive",
            procs,
        )
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))

    def test_founder_confirmed_advances(self):
        procs = [ChromeProcessSnapshot(pid=100, main_window_handle=99999)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE,
            CHROME_EXECUTABLE_PATHS_WSL[0],
            "https://drive.google.com/drive/my-drive",
            procs,
        )
        proof = apply_founder_visual_confirmation(proof, True, "Chrome open")
        self.assertTrue(visible_launch_proof_allows_next_gate(proof))

    def test_founder_denied_still_blocks(self):
        procs = [ChromeProcessSnapshot(pid=100, main_window_handle=99999)]
        proof = evaluate_visible_chrome_launch(
            ChromeLaunchMethod.DIRECT_EXECUTABLE,
            CHROME_EXECUTABLE_PATHS_WSL[0],
            "https://drive.google.com/drive/my-drive",
            procs,
        )
        proof = apply_founder_visual_confirmation(proof, False, "Not visible")
        self.assertFalse(visible_launch_proof_allows_next_gate(proof))


if __name__ == "__main__":
    unittest.main()
