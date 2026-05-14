"""Tests for execution binding contracts — Phase 96.8F.

Verifies the 6-layer typed execution binding model:
environment, execution surface, application, target service,
capability, and proof.
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest

from execution.environments.execution_binding_contracts import (
    ApplicationBinding,
    ApplicationLaunchMethod,
    CapabilityBinding,
    CapabilityMutability,
    DISALLOWED_CHROME_LAUNCH_METHODS,
    EnvironmentBinding,
    EnvironmentType,
    EvidenceType,
    ExecutionBinding,
    ExecutionSurfaceBinding,
    ExecutionSurfaceRole,
    ExecutionSurfaceType,
    ProofBinding,
    ProofLevel,
    TargetServiceBinding,
    TargetServiceFamily,
    build_w0_chrome_gws_binding,
)


class TestEnvironmentBinding(unittest.TestCase):
    def test_environment_binding_fields(self):
        env = EnvironmentBinding(
            environment_id="local_windows_desktop",
            environment_type=EnvironmentType.WINDOWS_DESKTOP.value,
            environment_authority="interactive_user_session_required",
        )
        self.assertEqual(env.environment_id, "local_windows_desktop")
        self.assertEqual(env.environment_type, "windows_desktop")

    def test_environment_binding_to_dict(self):
        env = EnvironmentBinding(
            environment_id="test",
            environment_type="windows_desktop",
            environment_authority="required",
        )
        d = env.to_dict()
        self.assertEqual(d["environment_id"], "test")
        self.assertIn("environment_authority", d)


class TestExecutionSurfaceBinding(unittest.TestCase):
    def test_surface_binding_fields(self):
        surf = ExecutionSurfaceBinding(
            execution_surface_id="wsl_tmux_worker",
            execution_surface_type=ExecutionSurfaceType.TMUX.value,
            execution_surface_role=ExecutionSurfaceRole.ORCHESTRATOR.value,
        )
        self.assertEqual(surf.execution_surface_type, "tmux")
        self.assertEqual(surf.execution_surface_role, "orchestrator")

    def test_gui_actuator_surface(self):
        surf = ExecutionSurfaceBinding(
            execution_surface_id="windows_powershell_relay",
            execution_surface_type=ExecutionSurfaceType.POWERSHELL.value,
            execution_surface_role=ExecutionSurfaceRole.GUI_ACTUATOR.value,
        )
        self.assertEqual(surf.execution_surface_role, "gui_actuator")


class TestApplicationBinding(unittest.TestCase):
    def test_chrome_application_binding(self):
        app = ApplicationBinding(
            application_id="google_chrome_windows",
            application_name="Google Chrome",
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            wsl_executable_path="/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
            launch_method=ApplicationLaunchMethod.DIRECT_EXECUTABLE.value,
            disallowed_launch_methods=[m.value for m in DISALLOWED_CHROME_LAUNCH_METHODS],
        )
        self.assertEqual(app.application_id, "google_chrome_windows")
        self.assertEqual(app.launch_method, "direct_executable")
        self.assertIn("explorer_url", app.disallowed_launch_methods)
        self.assertIn("default_browser", app.disallowed_launch_methods)
        self.assertIn("shell_url_open", app.disallowed_launch_methods)
        self.assertIn("generic_start_url", app.disallowed_launch_methods)
        self.assertIn("unknown_browser", app.disallowed_launch_methods)


class TestTargetServiceBinding(unittest.TestCase):
    def test_google_drive_binding(self):
        svc = TargetServiceBinding(
            target_service_id="google_drive",
            target_service_family=TargetServiceFamily.GOOGLE_WORKSPACE.value,
            service_url="https://drive.google.com/drive/my-drive",
            service_capabilities=["drive_open_my_drive", "drive_read_file_inventory"],
        )
        self.assertEqual(svc.target_service_family, "google_workspace")
        self.assertIn("drive_read_file_inventory", svc.service_capabilities)

    def test_google_docs_binding(self):
        svc = TargetServiceBinding(
            target_service_id="google_docs",
            target_service_family=TargetServiceFamily.GOOGLE_WORKSPACE.value,
            service_capabilities=["docs_open_document", "docs_detect_tabs"],
        )
        self.assertEqual(svc.target_service_id, "google_docs")


class TestCapabilityBinding(unittest.TestCase):
    def test_browser_open_capability(self):
        cap = CapabilityBinding(
            capability_id="browser.open_url_in_application",
            inputs=["url", "application_id"],
            outputs=["browser_window_visible"],
            authority_required="interactive_user_session_required",
            mutability=CapabilityMutability.READ_ONLY.value,
            proof_required=True,
            adapter_package_required="W-GWS-CORE-001",
        )
        self.assertEqual(cap.capability_id, "browser.open_url_in_application")
        self.assertEqual(cap.mutability, "read_only")
        self.assertTrue(cap.proof_required)


class TestProofBinding(unittest.TestCase):
    def test_founder_confirmation_proof(self):
        proof = ProofBinding(
            proof_level_required=ProofLevel.FOUNDER_VISUAL_CONFIRMATION.value,
            proof_source="founder",
            founder_confirmation_required=True,
            allowed_evidence=[
                EvidenceType.FOUNDER_VISUAL_CONFIRMATION.value,
                EvidenceType.DESKTOP_ADAPTER_FOREGROUND_CHECK.value,
            ],
            blocked_evidence=[
                EvidenceType.PROCESS_EXISTS_ONLY.value,
                EvidenceType.WINDOW_METADATA_ONLY.value,
            ],
        )
        self.assertTrue(proof.founder_confirmation_required)
        self.assertIn("process_exists_only", proof.blocked_evidence)
        self.assertIn("window_metadata_only", proof.blocked_evidence)
        self.assertIn("founder_visual_confirmation", proof.allowed_evidence)


class TestExecutionBindingComposite(unittest.TestCase):
    def test_empty_binding_has_defaults(self):
        binding = ExecutionBinding()
        self.assertEqual(binding.environment.environment_id, "")
        self.assertEqual(binding.execution_surfaces, [])
        self.assertEqual(binding.application.application_id, "")
        self.assertEqual(binding.target_services, [])
        self.assertEqual(binding.capabilities, [])

    def test_to_dict_structure(self):
        binding = build_w0_chrome_gws_binding()
        d = binding.to_dict()
        self.assertIn("environment", d)
        self.assertIn("execution_surfaces", d)
        self.assertIn("application", d)
        self.assertIn("target_services", d)
        self.assertIn("capabilities", d)
        self.assertIn("proof", d)
        self.assertEqual(len(d["execution_surfaces"]), 2)
        self.assertEqual(len(d["target_services"]), 2)
        self.assertEqual(len(d["capabilities"]), 3)


class TestW0ChromeGWSPreset(unittest.TestCase):
    def test_preset_environment(self):
        binding = build_w0_chrome_gws_binding()
        self.assertEqual(binding.environment.environment_id, "local_windows_desktop")
        self.assertEqual(binding.environment.environment_type, "windows_desktop")
        self.assertEqual(
            binding.environment.environment_authority, "interactive_user_session_required"
        )

    def test_preset_execution_surfaces(self):
        binding = build_w0_chrome_gws_binding()
        ids = [s.execution_surface_id for s in binding.execution_surfaces]
        self.assertIn("wsl_tmux_worker", ids)
        self.assertIn("windows_powershell_relay", ids)

        for surf in binding.execution_surfaces:
            if surf.execution_surface_id == "wsl_tmux_worker":
                self.assertEqual(surf.execution_surface_role, "orchestrator")
            if surf.execution_surface_id == "windows_powershell_relay":
                self.assertEqual(surf.execution_surface_role, "gui_actuator")

    def test_preset_application(self):
        binding = build_w0_chrome_gws_binding()
        self.assertEqual(binding.application.application_id, "google_chrome_windows")
        self.assertEqual(binding.application.launch_method, "direct_executable")
        self.assertIn("explorer_url", binding.application.disallowed_launch_methods)
        self.assertIn("default_browser", binding.application.disallowed_launch_methods)

    def test_preset_target_services(self):
        binding = build_w0_chrome_gws_binding()
        ids = [s.target_service_id for s in binding.target_services]
        self.assertIn("google_drive", ids)
        self.assertIn("google_docs", ids)
        for svc in binding.target_services:
            self.assertEqual(svc.target_service_family, "google_workspace")

    def test_preset_capabilities(self):
        binding = build_w0_chrome_gws_binding()
        cap_ids = [c.capability_id for c in binding.capabilities]
        self.assertIn("browser.open_url_in_application", cap_ids)
        self.assertIn("google_drive.read_file_inventory", cap_ids)
        self.assertIn("google_docs.extract_tabs", cap_ids)

    def test_preset_proof(self):
        binding = build_w0_chrome_gws_binding()
        self.assertEqual(binding.proof.proof_level_required, "founder_visual_confirmation")
        self.assertTrue(binding.proof.founder_confirmation_required)
        self.assertIn("process_exists_only", binding.proof.blocked_evidence)
        self.assertIn("window_metadata_only", binding.proof.blocked_evidence)


class TestDisallowedChromeLaunchMethods(unittest.TestCase):
    def test_all_five_disallowed(self):
        expected = {
            ApplicationLaunchMethod.EXPLORER_URL,
            ApplicationLaunchMethod.DEFAULT_BROWSER,
            ApplicationLaunchMethod.SHELL_URL_OPEN,
            ApplicationLaunchMethod.GENERIC_START_URL,
            ApplicationLaunchMethod.UNKNOWN_BROWSER,
        }
        self.assertEqual(DISALLOWED_CHROME_LAUNCH_METHODS, expected)

    def test_direct_executable_not_disallowed(self):
        self.assertNotIn(
            ApplicationLaunchMethod.DIRECT_EXECUTABLE,
            DISALLOWED_CHROME_LAUNCH_METHODS,
        )


if __name__ == "__main__":
    unittest.main()
