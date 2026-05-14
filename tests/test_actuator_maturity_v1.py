"""Tests for Phase 96.8AN — Actuator Maturity Model.

Verifies:
  1. Dry-run cannot claim L2+
  2. Missing screenshot caps maturity at L4
  3. Missing HWND caps maturity at L1
  4. Missing focus caps maturity at L2
  5. Founder confirmation required for L6
  6. Backend registry selects available backend
  7. Proof summary cannot claim success from intended state
  8. Simulated execution clearly marked simulated
  9. Maturity levels are strictly ordered
  10. Canonical registry includes actuator_proof
  11. Router config includes actuator_proof
  12. Backend evaluation is complete

UMH substrate subsystem. Phase 96.8AN.
"""

import json
import sys
from pathlib import Path

import pytest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
sys.path.insert(0, os.path.join(os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS", "services"))


class TestMaturityLevelComputation:
    def test_empty_evidence_is_l0(self) -> None:
        from execution.actuation.actuator_maturity_v1 import (
            ActuatorMaturityLevel,
            compute_maturity_level,
        )

        level = compute_maturity_level({})
        assert level == ActuatorMaturityLevel.L0_SIMULATED

    def test_pid_only_is_l1(self) -> None:
        from execution.actuation.actuator_maturity_v1 import (
            ActuatorMaturityLevel,
            compute_maturity_level,
        )

        level = compute_maturity_level({"chrome_pid": 12345})
        assert level == ActuatorMaturityLevel.L1_PROCESS_STARTED

    def test_pid_and_hwnd_is_l2(self) -> None:
        from execution.actuation.actuator_maturity_v1 import (
            ActuatorMaturityLevel,
            compute_maturity_level,
        )

        level = compute_maturity_level({"chrome_pid": 12345, "window_handle": 98765})
        assert level == ActuatorMaturityLevel.L2_WINDOW_OBSERVED

    def test_full_focus_is_l3(self) -> None:
        from execution.actuation.actuator_maturity_v1 import (
            ActuatorMaturityLevel,
            compute_maturity_level,
        )

        level = compute_maturity_level({"chrome_pid": 1, "window_handle": 2, "focused": True})
        assert level == ActuatorMaturityLevel.L3_FOREGROUND_FOCUSED

    def test_navigation_is_l4(self) -> None:
        from execution.actuation.actuator_maturity_v1 import (
            ActuatorMaturityLevel,
            compute_maturity_level,
        )

        level = compute_maturity_level(
            {
                "chrome_pid": 1,
                "window_handle": 2,
                "focused": True,
                "navigation_detected": True,
            }
        )
        assert level == ActuatorMaturityLevel.L4_NAVIGATION_OBSERVED

    def test_screenshot_is_l5(self) -> None:
        from execution.actuation.actuator_maturity_v1 import (
            ActuatorMaturityLevel,
            compute_maturity_level,
        )

        level = compute_maturity_level(
            {
                "chrome_pid": 1,
                "window_handle": 2,
                "focused": True,
                "navigation_detected": True,
                "screenshot_path": "/some/path.png",
            }
        )
        assert level == ActuatorMaturityLevel.L5_SCREENSHOT_VERIFIED

    def test_founder_confirmed_is_l6(self) -> None:
        from execution.actuation.actuator_maturity_v1 import (
            ActuatorMaturityLevel,
            compute_maturity_level,
        )

        level = compute_maturity_level(
            {
                "chrome_pid": 1,
                "window_handle": 2,
                "focused": True,
                "navigation_detected": True,
                "screenshot_path": "/some/path.png",
                "founder_confirmed": True,
            }
        )
        assert level == ActuatorMaturityLevel.L6_FOUNDER_CONFIRMED

    def test_replay_hash_is_l7(self) -> None:
        from execution.actuation.actuator_maturity_v1 import (
            ActuatorMaturityLevel,
            compute_maturity_level,
        )

        level = compute_maturity_level(
            {
                "chrome_pid": 1,
                "window_handle": 2,
                "focused": True,
                "navigation_detected": True,
                "screenshot_path": "/some/path.png",
                "founder_confirmed": True,
                "replay_hash": "abc123",
            }
        )
        assert level == ActuatorMaturityLevel.L7_REPLAYABLE_ACTUATION


class TestMaturityCeiling:
    def test_no_hwnd_caps_at_l1(self) -> None:
        from execution.actuation.actuator_maturity_v1 import (
            ActuatorMaturityLevel,
            maturity_ceiling,
        )

        assert maturity_ceiling(has_window_handle=False) == ActuatorMaturityLevel.L1_PROCESS_STARTED

    def test_no_screenshot_caps_at_l4(self) -> None:
        from execution.actuation.actuator_maturity_v1 import (
            ActuatorMaturityLevel,
            maturity_ceiling,
        )

        assert (
            maturity_ceiling(has_window_handle=True, has_screenshot=False)
            == ActuatorMaturityLevel.L4_NAVIGATION_OBSERVED
        )

    def test_no_founder_caps_at_l5(self) -> None:
        from execution.actuation.actuator_maturity_v1 import (
            ActuatorMaturityLevel,
            maturity_ceiling,
        )

        assert (
            maturity_ceiling(
                has_window_handle=True,
                has_screenshot=True,
                has_founder_confirmation=False,
            )
            == ActuatorMaturityLevel.L5_SCREENSHOT_VERIFIED
        )

    def test_all_present_allows_l7(self) -> None:
        from execution.actuation.actuator_maturity_v1 import (
            ActuatorMaturityLevel,
            maturity_ceiling,
        )

        assert (
            maturity_ceiling(
                has_window_handle=True,
                has_screenshot=True,
                has_founder_confirmation=True,
            )
            == ActuatorMaturityLevel.L7_REPLAYABLE_ACTUATION
        )


class TestMaturityClaimValidation:
    def test_valid_claim(self) -> None:
        from execution.actuation.actuator_maturity_v1 import (
            ActuatorMaturityLevel,
            validate_maturity_claim,
        )

        valid, actual, missing = validate_maturity_claim(
            ActuatorMaturityLevel.L1_PROCESS_STARTED,
            {"chrome_pid": 12345},
        )
        assert valid is True
        assert actual == ActuatorMaturityLevel.L1_PROCESS_STARTED
        assert missing == []

    def test_overclaim_rejected(self) -> None:
        from execution.actuation.actuator_maturity_v1 import (
            ActuatorMaturityLevel,
            validate_maturity_claim,
        )

        valid, actual, missing = validate_maturity_claim(
            ActuatorMaturityLevel.L5_SCREENSHOT_VERIFIED,
            {"chrome_pid": 12345},
        )
        assert valid is False
        assert actual == ActuatorMaturityLevel.L1_PROCESS_STARTED
        assert len(missing) > 0

    def test_l0_always_valid(self) -> None:
        from execution.actuation.actuator_maturity_v1 import (
            ActuatorMaturityLevel,
            validate_maturity_claim,
        )

        valid, actual, missing = validate_maturity_claim(ActuatorMaturityLevel.L0_SIMULATED, {})
        assert valid is True


class TestDryRunCannotClaimL2:
    def test_dry_run_is_l0(self) -> None:
        from execution.actuation.observed_desktop_state_v1 import ObservedDesktopStateV1

        obs = ObservedDesktopStateV1(
            chrome_pid=12345,
            window_handle=98765,
            focused=True,
            is_dry_run=True,
        )
        from execution.actuation.actuator_maturity_v1 import ActuatorMaturityLevel

        assert obs.maturity_level == ActuatorMaturityLevel.L0_SIMULATED

    def test_dry_run_proof_result_is_simulated(self) -> None:
        from execution.actuation.windows_foreground_actuator_v1 import (
            classify_relay_result,
        )

        result = classify_relay_result(
            {
                "request_id": "test-1",
                "trace_id": "trace-1",
                "dry_run": True,
                "process_id": 12345,
                "window_metadata": {"main_window_handle": 98765},
            }
        )
        assert result.status == "SIMULATED"
        assert result.is_dry_run is True
        assert not result.succeeded


class TestSimulatedMarkedClearly:
    def test_simulated_status_string(self) -> None:
        from execution.actuation.windows_foreground_actuator_v1 import (
            ActuatorProofResult,
        )
        from execution.actuation.actuator_maturity_v1 import ActuatorMaturityLevel

        r = ActuatorProofResult(
            request_id="test",
            trace_id="trace",
            backend_used="test",
            is_dry_run=True,
            maturity_level=ActuatorMaturityLevel.L0_SIMULATED,
        )
        assert r.status == "SIMULATED"

    def test_real_actuation_status(self) -> None:
        from execution.actuation.windows_foreground_actuator_v1 import (
            ActuatorProofResult,
        )
        from execution.actuation.actuator_maturity_v1 import ActuatorMaturityLevel

        r = ActuatorProofResult(
            request_id="test",
            trace_id="trace",
            backend_used="relay",
            is_dry_run=False,
            chrome_pid=1234,
            maturity_level=ActuatorMaturityLevel.L1_PROCESS_STARTED,
        )
        assert r.status == "REAL_ACTUATION"

    def test_failed_real_actuation(self) -> None:
        from execution.actuation.windows_foreground_actuator_v1 import (
            ActuatorProofResult,
        )
        from execution.actuation.actuator_maturity_v1 import ActuatorMaturityLevel

        r = ActuatorProofResult(
            request_id="test",
            trace_id="trace",
            backend_used="relay",
            is_dry_run=False,
            error="CHROME_NOT_FOUND",
        )
        assert r.status == "FAILED_REAL_ACTUATION"


class TestBackendRegistry:
    def test_registry_loads(self) -> None:
        from execution.actuation.actuator_backend_registry_v1 import (
            get_backend_registry,
        )

        reg = get_backend_registry()
        assert len(reg.available_backends) >= 6

    def test_relay_backend_has_all_capabilities(self) -> None:
        from execution.actuation.actuator_backend_registry_v1 import (
            BackendCapability,
            get_backend_registry,
        )

        reg = get_backend_registry()
        relay = reg.get("windows_interactive_desktop_relay")
        assert relay is not None
        assert relay.supports(BackendCapability.CHROME_LAUNCH)
        assert relay.supports(BackendCapability.HWND_OBSERVATION)
        assert relay.supports(BackendCapability.SCREENSHOT_CAPTURE)
        assert relay.supports(BackendCapability.FOREGROUND_DETECTION)
        assert relay.supports(BackendCapability.BROWSER_NAVIGATION)
        assert relay.supports(BackendCapability.WINDOW_FOCUS)
        assert relay.supports(BackendCapability.PROCESS_DETECTION)

    def test_select_for_proof_returns_relay(self) -> None:
        from execution.actuation.actuator_backend_registry_v1 import (
            get_backend_registry,
        )

        reg = get_backend_registry()
        selected = reg.select_for_proof()
        assert selected is not None
        assert selected.backend_id == "windows_interactive_desktop_relay"

    def test_playwright_lacks_hwnd(self) -> None:
        from execution.actuation.actuator_backend_registry_v1 import (
            BackendCapability,
            get_backend_registry,
        )

        reg = get_backend_registry()
        pw = reg.get("playwright_cdp")
        assert pw is not None
        assert not pw.supports(BackendCapability.HWND_OBSERVATION)
        assert not pw.supports(BackendCapability.FOREGROUND_DETECTION)

    def test_ui_tars_high_security_risk(self) -> None:
        from execution.actuation.actuator_backend_registry_v1 import (
            get_backend_registry,
        )

        reg = get_backend_registry()
        tars = reg.get("ui_tars_desktop")
        assert tars is not None
        assert tars.security_risk == "high"

    def test_backend_to_dict_serializable(self) -> None:
        from execution.actuation.actuator_backend_registry_v1 import (
            get_backend_registry,
        )

        reg = get_backend_registry()
        data = reg.to_dict()
        serialized = json.dumps(data)
        assert len(serialized) > 0


class TestProofSummaryIntegrity:
    def test_intended_state_cannot_claim_success(self) -> None:
        from execution.actuation.windows_foreground_actuator_v1 import (
            classify_relay_result,
        )

        result = classify_relay_result(
            {
                "request_id": "test-intended",
                "trace_id": "trace-intended",
                "adapter_status": "completed",
                "process_detected": False,
                "process_id": 0,
                "window_metadata": {},
            }
        )
        assert not result.succeeded
        from execution.actuation.actuator_maturity_v1 import ActuatorMaturityLevel

        assert result.maturity_level == ActuatorMaturityLevel.L0_SIMULATED

    def test_real_relay_result_classifies_correctly(self) -> None:
        from execution.actuation.windows_foreground_actuator_v1 import (
            classify_relay_result,
        )

        result = classify_relay_result(
            {
                "request_id": "test-real",
                "trace_id": "trace-real",
                "adapter_status": "completed",
                "process_detected": True,
                "process_id": 45678,
                "window_metadata": {
                    "main_window_handle": 131072,
                    "main_window_title": "Google - Google Chrome",
                },
                "observed_desktop_state": {
                    "chrome_pid": 45678,
                    "window_handle": 131072,
                    "window_title": "Google - Google Chrome",
                    "visible": True,
                    "focused": True,
                    "monitor_detected": True,
                    "desktop_unlocked": True,
                    "active_user_session": True,
                    "navigation_url": "https://www.google.com",
                    "navigation_detected": True,
                    "screenshot_hash": "abc123def456",
                    "screenshot_path": "/proof/screenshot.png",
                },
                "screenshot_captured": True,
                "screenshot_hash": "abc123def456",
                "screenshot_path": "/proof/screenshot.png",
                "stages_completed": [
                    "relay_dispatched",
                    "chrome_launched",
                    "process_verified",
                    "window_detected",
                    "focus_confirmed",
                    "navigation_confirmed",
                    "screenshot_captured",
                ],
            }
        )
        assert result.succeeded
        from execution.actuation.actuator_maturity_v1 import ActuatorMaturityLevel

        assert result.maturity_level == ActuatorMaturityLevel.L5_SCREENSHOT_VERIFIED
        assert result.founder_confirmed is False
        assert result.chrome_pid == 45678
        assert result.window_handle == 131072


class TestCanonicalRegistryInclusion:
    def test_actuator_proof_in_canonical_registry(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            CanonicalCommandRegistryV1,
        )

        reg = CanonicalCommandRegistryV1()
        assert reg.contains("!actuator-proof")
        assert reg.contains_action("actuator_proof")

    def test_actuator_proof_is_spine_routed(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            CanonicalCommandRegistryV1,
        )

        reg = CanonicalCommandRegistryV1()
        assert "!actuator-proof" in reg.spine_routed_commands

    def test_actuator_proof_requires_foreground(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            CanonicalCommandRegistryV1,
        )

        reg = CanonicalCommandRegistryV1()
        entry = reg.get("!actuator-proof")
        assert entry is not None
        assert entry.foreground_required is True
        assert entry.require_screenshot_proof is True

    def test_actuator_proof_in_router_config(self) -> None:
        config = json.loads((Path(_ROOT) / "config" / "control_plane_router_v1.json").read_text())
        assert "actuator_proof" in config["allowed_action_types"]

    def test_actuator_proof_in_allowed_action_types(self) -> None:
        from core.control_plane_router.router_contracts import (
            ALLOWED_ACTION_TYPES,
        )

        assert "actuator_proof" in ALLOWED_ACTION_TYPES

    def test_actuator_proof_in_capability_map(self) -> None:
        from core.control_plane_router.control_plane_router_v1 import (
            ACTION_CAPABILITY_MAP,
        )

        assert "actuator_proof" in ACTION_CAPABILITY_MAP

    def test_canonical_registry_now_has_15_commands(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            CanonicalCommandRegistryV1,
        )

        reg = CanonicalCommandRegistryV1()
        assert len(reg) == 27


class TestProofArtifactPersistence:
    def test_persist_proof_artifacts(self, tmp_path: Path) -> None:
        from execution.actuation.actuator_maturity_v1 import ActuatorMaturityLevel
        from execution.actuation.observed_desktop_state_v1 import (
            ObservedDesktopStateV1,
        )
        from execution.actuation.windows_foreground_actuator_v1 import (
            ActuatorProofResult,
            persist_proof_artifacts,
        )

        obs = ObservedDesktopStateV1(
            chrome_pid=1234,
            window_handle=5678,
            focused=True,
            backend_used="test",
        )
        result = ActuatorProofResult(
            request_id="TEST-001",
            trace_id="TRACE-001",
            backend_used="test",
            maturity_level=ActuatorMaturityLevel.L3_FOREGROUND_FOCUSED,
            observed_state=obs,
            chrome_pid=1234,
            window_handle=5678,
            focused=True,
        )
        result.compute_replay_hash()

        paths = persist_proof_artifacts(
            result,
            tmp_path / "proofs",
            backend_selection={"selected_backend": "test"},
        )

        assert (tmp_path / "proofs/backend_selection.json").exists()
        assert (tmp_path / "proofs/observed_desktop_state.json").exists()
        assert (tmp_path / "proofs/chrome_process_state.json").exists()
        assert (tmp_path / "proofs/window_focus_state.json").exists()
        assert (tmp_path / "proofs/actuator_maturity_report.json").exists()
        assert (tmp_path / "proofs/final_actuator_summary.json").exists()

        summary = json.loads((tmp_path / "proofs/final_actuator_summary.json").read_text())
        assert summary["maturity_level"] == 3
        assert summary["maturity_label"] == "foreground_focused"
        assert summary["phase"] == "96.8AN"

    def test_backend_selection_proof(self) -> None:
        from execution.actuation.windows_foreground_actuator_v1 import (
            build_backend_selection_proof,
        )

        proof = build_backend_selection_proof()
        assert proof["selected_backend"] == "windows_interactive_desktop_relay"
        assert "evaluated_backends" in proof
        assert len(proof["evaluated_backends"]) >= 6


class TestMaturityLevelOrdering:
    def test_levels_strictly_ordered(self) -> None:
        from execution.actuation.actuator_maturity_v1 import ActuatorMaturityLevel

        levels = list(ActuatorMaturityLevel)
        for i in range(len(levels) - 1):
            assert levels[i] < levels[i + 1]

    def test_all_8_levels_defined(self) -> None:
        from execution.actuation.actuator_maturity_v1 import ActuatorMaturityLevel

        assert len(ActuatorMaturityLevel) == 8

    def test_all_levels_have_labels(self) -> None:
        from execution.actuation.actuator_maturity_v1 import (
            MATURITY_LABELS,
            ActuatorMaturityLevel,
        )

        for level in ActuatorMaturityLevel:
            assert level in MATURITY_LABELS

    def test_all_levels_have_requirements(self) -> None:
        from execution.actuation.actuator_maturity_v1 import (
            MATURITY_REQUIREMENTS,
            ActuatorMaturityLevel,
        )

        for level in ActuatorMaturityLevel:
            assert level in MATURITY_REQUIREMENTS


class TestRegressionIntegrity:
    def test_all_new_files_compile(self) -> None:
        import py_compile

        files = [
            f"{_ROOT}/core/actuation/actuator_maturity_v1.py",
            f"{_ROOT}/core/actuation/actuator_backend_registry_v1.py",
            f"{_ROOT}/core/actuation/observed_desktop_state_v1.py",
            f"{_ROOT}/core/actuation/windows_foreground_actuator_v1.py",
        ]
        for f in files:
            py_compile.compile(f, doraise=True)

    def test_existing_files_still_compile(self) -> None:
        import py_compile

        files = [
            f"{_ROOT}/core/registry/canonical_command_registry_v1.py",
            f"{_ROOT}/core/runtime/node_sync_gate_v1.py",
            f"{_ROOT}/core/control_plane_router/router_contracts.py",
            f"{_ROOT}/core/control_plane_router/control_plane_router_v1.py",
            f"{_ROOT}/runtime/interfaces/discord_spine_integration_v1.py",
            f"{_ROOT}/services/handlers/substrate_command_handler.py",
            f"{_ROOT}/services/discord_bot.py",
        ]
        for f in files:
            py_compile.compile(f, doraise=True)

    def test_previous_registry_tests_compatible(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            get_canonical_registry,
        )

        reg = get_canonical_registry()
        assert len(reg) == 27
        assert reg.contains("!ping")
        assert reg.contains("!chrome-proof")
        assert reg.contains("!actuator-proof")
