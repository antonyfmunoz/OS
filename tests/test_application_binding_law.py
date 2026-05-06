"""Tests for Application Binding Law — Phase 96.8F.

Verifies that:
- explorer_url launch method fails for W0 Chrome
- default_browser launch method fails for W0 Chrome
- shell_url_open launch method fails for W0 Chrome
- generic_start_url launch method fails for W0 Chrome
- unknown_browser launch method fails for W0 Chrome
- direct_executable passes application binding
- WSL/tmux can be relay/orchestrator but NOT gui_actuator
- PowerShell can be gui_actuator
- Google Drive/Docs require google_workspace family
"""

import sys

sys.path.insert(0, "/opt/OS")

import unittest

from core.environment_bridge.execution_binding_contracts import (
    ApplicationBinding,
    ApplicationLaunchMethod,
    DISALLOWED_CHROME_LAUNCH_METHODS,
    EnvironmentBinding,
    EnvironmentType,
    ExecutionBinding,
    ExecutionSurfaceBinding,
    ExecutionSurfaceRole,
    ExecutionSurfaceType,
    CapabilityBinding,
    ProofBinding,
    ProofLevel,
    EvidenceType,
    TargetServiceBinding,
    TargetServiceFamily,
    WSL_TMUX_SURFACE_TYPES,
    build_w0_chrome_gws_binding,
)
from core.environment_bridge.execution_binding_validator import (
    validate_execution_binding,
    validate_execution_binding_dict,
)


class TestDisallowedLaunchMethodsFailValidation(unittest.TestCase):
    def _binding_with_launch_method(self, method: str) -> ExecutionBinding:
        binding = build_w0_chrome_gws_binding()
        binding.application.launch_method = method
        return binding

    def test_explorer_url_fails(self):
        binding = self._binding_with_launch_method(ApplicationLaunchMethod.EXPLORER_URL.value)
        result = validate_execution_binding(binding)
        self.assertFalse(result.valid)
        self.assertTrue(any("CHROME_LAUNCH_METHOD_BLOCKED" in e for e in result.errors))

    def test_default_browser_fails(self):
        binding = self._binding_with_launch_method(ApplicationLaunchMethod.DEFAULT_BROWSER.value)
        result = validate_execution_binding(binding)
        self.assertFalse(result.valid)
        self.assertTrue(
            any("CHROME_LAUNCH_METHOD_BLOCKED" in e or "DISALLOWED" in e for e in result.errors)
        )

    def test_shell_url_open_fails(self):
        binding = self._binding_with_launch_method(ApplicationLaunchMethod.SHELL_URL_OPEN.value)
        result = validate_execution_binding(binding)
        self.assertFalse(result.valid)

    def test_generic_start_url_fails(self):
        binding = self._binding_with_launch_method(ApplicationLaunchMethod.GENERIC_START_URL.value)
        result = validate_execution_binding(binding)
        self.assertFalse(result.valid)

    def test_unknown_browser_fails(self):
        binding = self._binding_with_launch_method(ApplicationLaunchMethod.UNKNOWN_BROWSER.value)
        result = validate_execution_binding(binding)
        self.assertFalse(result.valid)

    def test_direct_executable_passes(self):
        binding = build_w0_chrome_gws_binding()
        result = validate_execution_binding(binding)
        self.assertTrue(result.valid)


class TestWSLTmuxNotGUIAuthority(unittest.TestCase):
    def test_wsl_as_gui_actuator_fails(self):
        binding = build_w0_chrome_gws_binding()
        binding.execution_surfaces = [
            ExecutionSurfaceBinding(
                execution_surface_id="wsl_worker",
                execution_surface_type=ExecutionSurfaceType.WSL.value,
                execution_surface_role=ExecutionSurfaceRole.GUI_ACTUATOR.value,
            ),
        ]
        result = validate_execution_binding(binding)
        self.assertFalse(result.valid)
        self.assertTrue(any("WSL_TMUX_NOT_GUI_AUTHORITY" in e for e in result.errors))

    def test_tmux_as_gui_actuator_fails(self):
        binding = build_w0_chrome_gws_binding()
        binding.execution_surfaces = [
            ExecutionSurfaceBinding(
                execution_surface_id="tmux_worker",
                execution_surface_type=ExecutionSurfaceType.TMUX.value,
                execution_surface_role=ExecutionSurfaceRole.GUI_ACTUATOR.value,
            ),
        ]
        result = validate_execution_binding(binding)
        self.assertFalse(result.valid)
        self.assertTrue(any("WSL_TMUX_NOT_GUI_AUTHORITY" in e for e in result.errors))

    def test_wsl_as_orchestrator_passes(self):
        binding = build_w0_chrome_gws_binding()
        result = validate_execution_binding(binding)
        self.assertTrue(result.valid)

    def test_powershell_as_gui_actuator_passes(self):
        binding = build_w0_chrome_gws_binding()
        result = validate_execution_binding(binding)
        ps_surfaces = [
            s
            for s in binding.execution_surfaces
            if s.execution_surface_type == ExecutionSurfaceType.POWERSHELL.value
        ]
        self.assertTrue(len(ps_surfaces) > 0)
        for s in ps_surfaces:
            self.assertEqual(s.execution_surface_role, ExecutionSurfaceRole.GUI_ACTUATOR.value)
        self.assertTrue(result.valid)


class TestGoogleWorkspaceServiceFamily(unittest.TestCase):
    def test_google_drive_wrong_family_fails(self):
        binding = build_w0_chrome_gws_binding()
        for svc in binding.target_services:
            if svc.target_service_id == "google_drive":
                svc.target_service_family = "local_filesystem"
        result = validate_execution_binding(binding)
        self.assertFalse(result.valid)
        self.assertTrue(any("SERVICE_FAMILY_MISMATCH" in e for e in result.errors))

    def test_google_docs_wrong_family_fails(self):
        binding = build_w0_chrome_gws_binding()
        for svc in binding.target_services:
            if svc.target_service_id == "google_docs":
                svc.target_service_family = "microsoft_365"
        result = validate_execution_binding(binding)
        self.assertFalse(result.valid)

    def test_correct_google_workspace_family_passes(self):
        binding = build_w0_chrome_gws_binding()
        result = validate_execution_binding(binding)
        self.assertTrue(result.valid)


class TestMissingLayersFail(unittest.TestCase):
    def test_missing_environment_fails(self):
        binding = build_w0_chrome_gws_binding()
        binding.environment = EnvironmentBinding()
        result = validate_execution_binding(binding)
        self.assertFalse(result.valid)

    def test_missing_execution_surfaces_fails(self):
        binding = build_w0_chrome_gws_binding()
        binding.execution_surfaces = []
        result = validate_execution_binding(binding)
        self.assertFalse(result.valid)

    def test_missing_application_fails(self):
        binding = build_w0_chrome_gws_binding()
        binding.application = ApplicationBinding()
        result = validate_execution_binding(binding)
        self.assertFalse(result.valid)

    def test_missing_target_services_fails(self):
        binding = build_w0_chrome_gws_binding()
        binding.target_services = []
        result = validate_execution_binding(binding)
        self.assertFalse(result.valid)

    def test_missing_capabilities_fails(self):
        binding = build_w0_chrome_gws_binding()
        binding.capabilities = []
        result = validate_execution_binding(binding)
        self.assertFalse(result.valid)

    def test_missing_proof_fails(self):
        binding = build_w0_chrome_gws_binding()
        binding.proof = ProofBinding()
        result = validate_execution_binding(binding)
        self.assertFalse(result.valid)


class TestProofBindingValidation(unittest.TestCase):
    def test_founder_confirmation_level_without_flag_fails(self):
        binding = build_w0_chrome_gws_binding()
        binding.proof.founder_confirmation_required = False
        result = validate_execution_binding(binding)
        self.assertFalse(result.valid)
        self.assertTrue(any("FOUNDER_CONFIRMATION_MISMATCH" in e for e in result.errors))

    def test_blocked_and_allowed_evidence_overlap_fails(self):
        binding = build_w0_chrome_gws_binding()
        binding.proof.allowed_evidence.append("process_exists_only")
        result = validate_execution_binding(binding)
        self.assertFalse(result.valid)
        self.assertTrue(any("PROOF_EVIDENCE_CONFLICT" in e for e in result.errors))


class TestDictValidation(unittest.TestCase):
    def test_empty_dict_fails(self):
        result = validate_execution_binding_dict({})
        self.assertFalse(result.valid)

    def test_none_binding_fails(self):
        result = validate_execution_binding_dict(None)
        self.assertFalse(result.valid)

    def test_valid_preset_dict_passes(self):
        binding = build_w0_chrome_gws_binding()
        result = validate_execution_binding_dict(binding.to_dict())
        self.assertTrue(result.valid)

    def test_missing_environment_in_dict_fails(self):
        d = build_w0_chrome_gws_binding().to_dict()
        d["environment"] = {}
        result = validate_execution_binding_dict(d)
        self.assertFalse(result.valid)


if __name__ == "__main__":
    unittest.main()
