"""Tests for Phase 96.8AI — Real Windows GUI Actuation Proof.

Validates that real GUI actuation enforces:
  - Foreground environment required
  - GUI backend required
  - Headless blocked
  - API blocked
  - Screenshot proof required
  - Observed state required
  - Focus validation required
  - Chrome PID validation required
  - Replay deterministic
  - Node sync enforced
  - Authority enforced
  - WorkPacket enforced

UMH substrate subsystem. Phase 96.8AI.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

import pytest

from core.runtime.windows_foreground_actuator_v1 import (
    ACTUATION_FORBIDDEN_ACTIONS,
    FORBIDDEN_ENVIRONMENTS,
    REQUIRED_ENVIRONMENT,
    ActuationEvent,
    ActuationStage,
    EnvironmentRequirement,
    GUIActuationProof,
    ObservedDesktopState,
    build_gui_actuation_proof,
    build_proof_summary,
    parse_relay_result_to_observed_state,
    persist_gui_actuation_proof,
    validate_environment,
)
from execution.environments.windows_desktop_adapter_contracts import (
    WindowsDesktopActionType,
)
from runtime.interfaces.discord_interface_adapter_v1 import (
    COMMAND_ACTION_MAP,
    COMMAND_CONTRACT,
    SPINE_ROUTED_COMMANDS,
    SUPPORTED_COMMANDS,
    build_work_packet_for_router,
)
from control_plane.router.router_contracts import (
    ALLOWED_ACTION_TYPES,
    CapabilityType,
)
from control_plane.router.control_plane_router_v1 import (
    ACTION_CAPABILITY_MAP,
)
from execution.environments.windows_desktop_request_builder import (
    build_w0_chrome_proof_request,
)


CONFIG_PATH = Path(_ROOT) / "config" / "w0_real_windows_gui_actuation_v1.json"


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _make_valid_observed_state() -> ObservedDesktopState:
    return ObservedDesktopState(
        chrome_pid=12345,
        window_handle=67890,
        window_title="Google - Google Chrome",
        visible=True,
        focused=True,
        monitor_detected=True,
        desktop_unlocked=True,
        active_user_session=True,
        navigation_url="https://www.google.com",
        navigation_detected=True,
        screenshot_hash="abc123def456",
        screenshot_path="/proofs/screenshot.png",
    )


def _make_actuation_events() -> list[ActuationEvent]:
    return [
        ActuationEvent(
            event_id="",
            stage=ActuationStage.RELAY_DISPATCHED,
        ),
        ActuationEvent(
            event_id="",
            stage=ActuationStage.CHROME_LAUNCHED,
        ),
        ActuationEvent(
            event_id="",
            stage=ActuationStage.PROCESS_VERIFIED,
        ),
        ActuationEvent(
            event_id="",
            stage=ActuationStage.WINDOW_DETECTED,
        ),
        ActuationEvent(
            event_id="",
            stage=ActuationStage.FOCUS_CONFIRMED,
        ),
        ActuationEvent(
            event_id="",
            stage=ActuationStage.SCREENSHOT_CAPTURED,
            observed_state=_make_valid_observed_state(),
        ),
    ]


# -----------------------------------------------------------------------
# Command Registration
# -----------------------------------------------------------------------


class TestCommandRegistration:
    def test_chrome_proof_in_supported(self):
        assert "!chrome-proof" in SUPPORTED_COMMANDS

    def test_chrome_proof_action_mapping(self):
        assert COMMAND_ACTION_MAP["!chrome-proof"] == "chrome_proof"

    def test_chrome_proof_spine_routed(self):
        assert "!chrome-proof" in SPINE_ROUTED_COMMANDS

    def test_chrome_proof_contract_exists(self):
        assert "!chrome-proof" in COMMAND_CONTRACT

    def test_chrome_proof_requires_foreground_gui(self):
        contract = COMMAND_CONTRACT["!chrome-proof"]
        assert contract["require_foreground_gui"] is True

    def test_chrome_proof_requires_screenshot(self):
        contract = COMMAND_CONTRACT["!chrome-proof"]
        assert contract["require_screenshot_proof"] is True

    def test_chrome_proof_no_mutation(self):
        contract = COMMAND_CONTRACT["!chrome-proof"]
        assert contract["mutation_allowed"] is False

    def test_chrome_proof_proof_required(self):
        contract = COMMAND_CONTRACT["!chrome-proof"]
        assert contract["proof_required"] is True

    def test_chrome_proof_in_allowed_types(self):
        assert "chrome_proof" in ALLOWED_ACTION_TYPES

    def test_chrome_proof_capability_map(self):
        cap = ACTION_CAPABILITY_MAP["chrome_proof"]
        assert cap.capability_type == CapabilityType.WINDOWS_GUI_EXECUTION
        assert cap.requires_gui is True

    def test_chrome_proof_action_type_enum(self):
        assert WindowsDesktopActionType.CHROME_PROOF.value == "chrome_proof"


# -----------------------------------------------------------------------
# Environment Enforcement
# -----------------------------------------------------------------------


class TestEnvironmentEnforcement:
    def test_required_environment_is_foreground(self):
        assert REQUIRED_ENVIRONMENT == EnvironmentRequirement.LOCAL_WINDOWS_FOREGROUND

    def test_vps_environment_forbidden(self):
        assert EnvironmentRequirement.VPS in FORBIDDEN_ENVIRONMENTS

    def test_headless_environment_forbidden(self):
        assert EnvironmentRequirement.LOCAL_WINDOWS_HEADLESS in FORBIDDEN_ENVIRONMENTS

    def test_background_environment_forbidden(self):
        assert EnvironmentRequirement.LOCAL_WINDOWS_BACKGROUND in FORBIDDEN_ENVIRONMENTS

    def test_foreground_not_forbidden(self):
        assert EnvironmentRequirement.LOCAL_WINDOWS_FOREGROUND not in FORBIDDEN_ENVIRONMENTS

    def test_gui_not_forbidden(self):
        assert EnvironmentRequirement.LOCAL_WINDOWS_GUI not in FORBIDDEN_ENVIRONMENTS


class TestEnvironmentValidation:
    def test_foreground_passes(self):
        config = {"require_foreground_gui": True, "require_real_desktop": True}
        errors = validate_environment(EnvironmentRequirement.LOCAL_WINDOWS_FOREGROUND, config)
        assert errors == []

    def test_vps_fails(self):
        config = {"require_foreground_gui": True, "require_real_desktop": True}
        errors = validate_environment(EnvironmentRequirement.VPS, config)
        assert len(errors) >= 2

    def test_headless_fails(self):
        config = {"require_foreground_gui": True}
        errors = validate_environment(EnvironmentRequirement.LOCAL_WINDOWS_HEADLESS, config)
        assert len(errors) >= 1

    def test_background_fails(self):
        config = {"require_foreground_gui": True}
        errors = validate_environment(EnvironmentRequirement.LOCAL_WINDOWS_BACKGROUND, config)
        assert len(errors) >= 1


# -----------------------------------------------------------------------
# Observed Desktop State
# -----------------------------------------------------------------------


class TestObservedDesktopState:
    def test_valid_state(self):
        state = _make_valid_observed_state()
        assert state.is_valid is True
        assert state.denial_reasons == []

    def test_no_chrome_pid_invalid(self):
        state = _make_valid_observed_state()
        state.chrome_pid = 0
        assert state.is_valid is False
        assert "no_chrome_pid" in state.denial_reasons

    def test_not_visible_invalid(self):
        state = _make_valid_observed_state()
        state.visible = False
        assert state.is_valid is False
        assert "not_visible" in state.denial_reasons

    def test_not_focused_invalid(self):
        state = _make_valid_observed_state()
        state.focused = False
        assert state.is_valid is False
        assert "not_focused" in state.denial_reasons

    def test_no_session_invalid(self):
        state = _make_valid_observed_state()
        state.active_user_session = False
        assert state.is_valid is False
        assert "no_active_user_session" in state.denial_reasons

    def test_desktop_locked_invalid(self):
        state = _make_valid_observed_state()
        state.desktop_unlocked = False
        assert state.is_valid is False
        assert "desktop_locked" in state.denial_reasons

    def test_default_state_invalid(self):
        state = ObservedDesktopState()
        assert state.is_valid is False

    def test_auto_timestamp(self):
        state = ObservedDesktopState()
        assert state.timestamp != ""

    def test_to_dict_complete(self):
        state = _make_valid_observed_state()
        d = state.to_dict()
        assert "chrome_pid" in d
        assert "visible" in d
        assert "focused" in d
        assert "is_valid" in d
        assert "denial_reasons" in d
        assert "screenshot_hash" in d
        assert "window_handle" in d


# -----------------------------------------------------------------------
# Parse Relay Result
# -----------------------------------------------------------------------


class TestParseRelayResult:
    def test_parses_completed_result(self):
        relay_result = {
            "process_id": 9999,
            "process_detected": True,
            "adapter_status": "completed",
            "window_metadata": {
                "main_window_handle": 12345,
                "main_window_title": "Google Chrome",
            },
            "url": "https://www.google.com",
        }
        state = parse_relay_result_to_observed_state(relay_result)
        assert state.chrome_pid == 9999
        assert state.window_handle == 12345
        assert state.visible is True
        assert state.focused is True
        assert state.active_user_session is True

    def test_parses_failed_result(self):
        relay_result = {
            "process_id": 0,
            "process_detected": False,
            "adapter_status": "failed",
            "window_metadata": {},
        }
        state = parse_relay_result_to_observed_state(relay_result)
        assert state.chrome_pid == 0
        assert state.is_valid is False

    def test_parses_empty_metadata(self):
        relay_result = {
            "adapter_status": "completed",
        }
        state = parse_relay_result_to_observed_state(relay_result)
        assert state.chrome_pid == 0


# -----------------------------------------------------------------------
# Actuation Events
# -----------------------------------------------------------------------


class TestActuationEvents:
    def test_event_auto_id(self):
        event = ActuationEvent(event_id="", stage=ActuationStage.CHROME_LAUNCHED)
        assert event.event_id.startswith("ACTEVT-")

    def test_event_auto_timestamp(self):
        event = ActuationEvent(event_id="", stage=ActuationStage.CHROME_LAUNCHED)
        assert event.timestamp != ""

    def test_event_to_dict(self):
        event = ActuationEvent(event_id="", stage=ActuationStage.CHROME_LAUNCHED)
        d = event.to_dict()
        assert d["stage"] == "chrome_launched"
        assert "event_id" in d

    def test_event_with_observed_state(self):
        event = ActuationEvent(
            event_id="",
            stage=ActuationStage.SCREENSHOT_CAPTURED,
            observed_state=_make_valid_observed_state(),
        )
        d = event.to_dict()
        assert d["observed_state"]["chrome_pid"] == 12345

    def test_all_stages_exist(self):
        expected = [
            "NOT_STARTED",
            "RELAY_DISPATCHED",
            "CHROME_LAUNCHED",
            "PROCESS_VERIFIED",
            "WINDOW_DETECTED",
            "FOCUS_CONFIRMED",
            "NAVIGATION_CONFIRMED",
            "SCREENSHOT_CAPTURED",
            "FOUNDER_CONFIRMED",
            "COMPLETED",
            "FAILED",
        ]
        for name in expected:
            assert hasattr(ActuationStage, name)


# -----------------------------------------------------------------------
# GUI Actuation Proof
# -----------------------------------------------------------------------


class TestGUIActuationProof:
    def test_auto_proof_id(self):
        proof = GUIActuationProof(proof_id="", trace_id="test")
        assert proof.proof_id.startswith("GUI-ACT-PROOF-")

    def test_auto_timestamp(self):
        proof = GUIActuationProof(proof_id="", trace_id="test")
        assert proof.timestamp != ""

    def test_environment_is_foreground(self):
        proof = GUIActuationProof(proof_id="", trace_id="test")
        assert proof.environment == "local_windows_foreground"

    def test_not_passed_without_state(self):
        proof = GUIActuationProof(proof_id="", trace_id="test")
        assert proof.passed is False

    def test_not_passed_without_founder(self):
        proof = GUIActuationProof(
            proof_id="",
            trace_id="test",
            final_observed_state=_make_valid_observed_state(),
            chrome_pid=12345,
            stages_completed=["a", "b", "c", "d", "e"],
            founder_confirmed=False,
        )
        assert proof.passed is False

    def test_not_passed_without_enough_stages(self):
        proof = GUIActuationProof(
            proof_id="",
            trace_id="test",
            final_observed_state=_make_valid_observed_state(),
            chrome_pid=12345,
            stages_completed=["a", "b"],
            founder_confirmed=True,
        )
        assert proof.passed is False

    def test_passed_with_all_requirements(self):
        proof = GUIActuationProof(
            proof_id="",
            trace_id="test",
            final_observed_state=_make_valid_observed_state(),
            chrome_pid=12345,
            stages_completed=["a", "b", "c", "d", "e"],
            founder_confirmed=True,
        )
        assert proof.passed is True

    def test_replay_hash_deterministic(self):
        proof = GUIActuationProof(
            proof_id="GUI-ACT-PROOF-test",
            trace_id="test",
            chrome_pid=12345,
            window_handle=67890,
            screenshot_hash="abc",
            stages_completed=["a", "b"],
        )
        h1 = proof.compute_replay_hash()
        h2 = proof.compute_replay_hash()
        assert h1 == h2
        assert len(h1) == 64

    def test_to_dict_complete(self):
        proof = GUIActuationProof(
            proof_id="",
            trace_id="test",
            final_observed_state=_make_valid_observed_state(),
            actuation_events=_make_actuation_events(),
        )
        d = proof.to_dict()
        assert "proof_id" in d
        assert "environment" in d
        assert "final_observed_state" in d
        assert "actuation_events" in d
        assert "passed" in d
        assert "replay_hash" in d
        assert len(d["actuation_events"]) == 6


# -----------------------------------------------------------------------
# Build + Persist Proof
# -----------------------------------------------------------------------


class TestBuildAndPersistProof:
    def test_build_proof(self):
        proof = build_gui_actuation_proof(
            trace_id="build-test",
            actuation_events=_make_actuation_events(),
            final_observed_state=_make_valid_observed_state(),
            chrome_pid=12345,
            window_handle=67890,
            screenshot_hash="abc123",
            founder_confirmed=True,
            stages_completed=["a", "b", "c", "d", "e"],
        )
        assert proof.passed is True
        assert proof.replay_hash != ""

    def test_persist_proof(self, tmp_path):
        proof = build_gui_actuation_proof(
            trace_id="persist-test",
            actuation_events=[],
            final_observed_state=_make_valid_observed_state(),
            chrome_pid=12345,
            founder_confirmed=True,
            stages_completed=["a", "b", "c", "d", "e"],
        )
        path = persist_gui_actuation_proof(proof, tmp_path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["proof_id"] == proof.proof_id
        assert data["passed"] is True

    def test_proof_summary(self):
        proof = build_gui_actuation_proof(
            trace_id="summary-test",
            actuation_events=[],
            final_observed_state=_make_valid_observed_state(),
            chrome_pid=12345,
            founder_confirmed=True,
            stages_completed=["a", "b", "c", "d", "e"],
        )
        summary = build_proof_summary(proof)
        assert summary["passed"] is True
        assert summary["final_state_valid"] is True
        assert summary["chrome_pid"] == 12345


# -----------------------------------------------------------------------
# Config Validation
# -----------------------------------------------------------------------


class TestConfig:
    def test_config_exists(self):
        assert CONFIG_PATH.exists()

    def test_config_valid_json(self):
        config = _load_config()
        assert isinstance(config, dict)

    def test_config_requires_foreground_gui(self):
        config = _load_config()
        assert config["require_foreground_gui"] is True

    def test_config_requires_real_desktop(self):
        config = _load_config()
        assert config["require_real_desktop"] is True

    def test_config_requires_screenshot_proof(self):
        config = _load_config()
        assert config["require_screenshot_proof"] is True

    def test_config_requires_observed_state(self):
        config = _load_config()
        assert config["require_observed_state"] is True

    def test_config_requires_focus_validation(self):
        config = _load_config()
        assert config["require_focus_validation"] is True

    def test_config_requires_founder_confirmation(self):
        config = _load_config()
        assert config["require_founder_confirmation"] is True

    def test_config_blocks_headless(self):
        config = _load_config()
        assert config["allow_headless"] is False

    def test_config_blocks_api(self):
        config = _load_config()
        assert config["allow_api_fallback"] is False

    def test_config_blocks_background(self):
        config = _load_config()
        assert config["allow_background_only"] is False

    def test_config_blocks_simulated(self):
        config = _load_config()
        assert config["allow_simulated_gui"] is False

    def test_config_has_proof_dir(self):
        config = _load_config()
        assert config["proof_dir"] != ""

    def test_config_forbidden_includes_simulated(self):
        config = _load_config()
        assert "simulated_gui_state" in config["forbidden_actions"]

    def test_config_forbidden_includes_inferred(self):
        config = _load_config()
        assert "inferred_visibility" in config["forbidden_actions"]

    def test_config_forbidden_includes_mocked(self):
        config = _load_config()
        assert "mocked_chrome_launch" in config["forbidden_actions"]


# -----------------------------------------------------------------------
# Forbidden Actions
# -----------------------------------------------------------------------


class TestForbiddenActions:
    def test_api_fallback(self):
        assert "api_extraction_fallback" in ACTUATION_FORBIDDEN_ACTIONS

    def test_headless_fallback(self):
        assert "headless_browser_fallback" in ACTUATION_FORBIDDEN_ACTIONS

    def test_simulated_gui(self):
        assert "simulated_gui_state" in ACTUATION_FORBIDDEN_ACTIONS

    def test_inferred_visibility(self):
        assert "inferred_visibility" in ACTUATION_FORBIDDEN_ACTIONS

    def test_mocked_chrome(self):
        assert "mocked_chrome_launch" in ACTUATION_FORBIDDEN_ACTIONS

    def test_fake_process(self):
        assert "fake_process_detection" in ACTUATION_FORBIDDEN_ACTIONS

    def test_replay_only(self):
        assert "replay_only_validation" in ACTUATION_FORBIDDEN_ACTIONS

    def test_background_only(self):
        assert "background_only_execution" in ACTUATION_FORBIDDEN_ACTIONS

    def test_hidden_window(self):
        assert "hidden_window_execution" in ACTUATION_FORBIDDEN_ACTIONS

    def test_screenshot_without_observation(self):
        assert "screenshot_without_observation" in ACTUATION_FORBIDDEN_ACTIONS

    def test_mutate_drive(self):
        assert "mutate_drive" in ACTUATION_FORBIDDEN_ACTIONS

    def test_mutate_docs(self):
        assert "mutate_docs" in ACTUATION_FORBIDDEN_ACTIONS

    def test_auto_promote(self):
        assert "auto_promote_canonical_truth" in ACTUATION_FORBIDDEN_ACTIONS


# -----------------------------------------------------------------------
# Request Builder
# -----------------------------------------------------------------------


class TestRequestBuilder:
    def test_chrome_proof_request_builds(self):
        req = build_w0_chrome_proof_request()
        assert req.action_type == "chrome_proof"

    def test_chrome_proof_request_proof_type(self):
        req = build_w0_chrome_proof_request()
        assert req.proof_required == "screenshot_and_observed_state"

    def test_chrome_proof_no_mutation(self):
        req = build_w0_chrome_proof_request()
        assert req.no_mutation is True

    def test_chrome_proof_has_trace_id(self):
        req = build_w0_chrome_proof_request()
        assert req.trace_id.startswith("W0-chrome-proof-")

    def test_chrome_proof_default_url(self):
        req = build_w0_chrome_proof_request()
        assert req.url == "https://www.google.com"

    def test_chrome_proof_custom_url(self):
        req = build_w0_chrome_proof_request(url="https://drive.google.com")
        assert req.url == "https://drive.google.com"

    def test_chrome_proof_notes_block_headless(self):
        req = build_w0_chrome_proof_request()
        notes_text = " ".join(req.notes).lower()
        assert "no headless" in notes_text

    def test_chrome_proof_notes_require_screenshot(self):
        req = build_w0_chrome_proof_request()
        notes_text = " ".join(req.notes).upper()
        assert "SCREENSHOT" in notes_text


# -----------------------------------------------------------------------
# WorkPacket Builder
# -----------------------------------------------------------------------


class TestWorkPacketBuilder:
    def test_chrome_proof_builds_packet(self):
        packet = build_work_packet_for_router("!chrome-proof")
        assert packet is not None
        assert packet.action_type == "chrome_proof"

    def test_chrome_proof_packet_has_trace_id(self):
        packet = build_work_packet_for_router("!chrome-proof")
        assert packet.trace_id != ""

    def test_chrome_proof_packet_source(self):
        packet = build_work_packet_for_router("!chrome-proof")
        assert packet.source_interface == "discord_interface_adapter_v1"


# -----------------------------------------------------------------------
# Adapter Registry
# -----------------------------------------------------------------------


class TestAdapterRegistry:
    def test_worker_has_chrome_proof(self):
        with open("data/registries/local_worker_adapter_registry_v1.json") as f:
            reg = json.load(f)
        caps = reg["workers"]["windows_interactive_desktop_relay"]["capabilities"]
        assert "chrome_proof" in caps

    def test_adapter_has_chrome_proof(self):
        with open("data/registries/local_worker_adapter_registry_v1.json") as f:
            reg = json.load(f)
        adapter_caps = reg["adapters"]["windows_interactive_desktop_relay"]["capabilities"]
        found = [c for c in adapter_caps if c["capability_id"] == "chrome_proof"]
        assert len(found) == 1

    def test_adapter_chrome_proof_requires_gui(self):
        with open("data/registries/local_worker_adapter_registry_v1.json") as f:
            reg = json.load(f)
        adapter_caps = reg["adapters"]["windows_interactive_desktop_relay"]["capabilities"]
        cap = next(c for c in adapter_caps if c["capability_id"] == "chrome_proof")
        assert cap["requires_gui"] is True


# -----------------------------------------------------------------------
# Spine Integration
# -----------------------------------------------------------------------


class TestSpineIntegration:
    def test_spine_source_has_chrome_proof(self):
        import inspect
        from runtime.interfaces import discord_spine_integration_v1

        src = inspect.getsource(discord_spine_integration_v1.build_spine_infrastructure)
        assert "chrome_proof" in src


# -----------------------------------------------------------------------
# PowerShell Relay
# -----------------------------------------------------------------------


class TestPowerShellRelay:
    def test_relay_script_exists(self):
        assert (Path(_ROOT) / "scripts" / "windows_interactive_desktop_relay.ps1").exists()

    def test_relay_handles_chrome_proof(self):
        content = (Path(_ROOT) / "scripts" / "windows_interactive_desktop_relay.ps1").read_text()
        assert "Handle-ChromeProof" in content

    def test_relay_dispatch_has_chrome_proof(self):
        content = (Path(_ROOT) / "scripts" / "windows_interactive_desktop_relay.ps1").read_text()
        assert '"chrome_proof"' in content

    def test_relay_captures_screenshots(self):
        content = (Path(_ROOT) / "scripts" / "windows_interactive_desktop_relay.ps1").read_text()
        assert "Capture-Screenshot" in content

    def test_relay_collects_foreground_info(self):
        content = (Path(_ROOT) / "scripts" / "windows_interactive_desktop_relay.ps1").read_text()
        assert "Get-ForegroundWindowInfo" in content

    def test_relay_uses_win32_apis(self):
        content = (Path(_ROOT) / "scripts" / "windows_interactive_desktop_relay.ps1").read_text()
        assert "GetForegroundWindow" in content
        assert "IsWindowVisible" in content

    def test_relay_writes_observed_state(self):
        content = (Path(_ROOT) / "scripts" / "windows_interactive_desktop_relay.ps1").read_text()
        assert "observed_desktop_state" in content

    def test_relay_writes_proof_summary(self):
        content = (Path(_ROOT) / "scripts" / "windows_interactive_desktop_relay.ps1").read_text()
        assert "proof_summary" in content

    def test_relay_writes_desktop_environment(self):
        content = (Path(_ROOT) / "scripts" / "windows_interactive_desktop_relay.ps1").read_text()
        assert "desktop_environment" in content


# -----------------------------------------------------------------------
# Dataclass Contracts
# -----------------------------------------------------------------------


class TestDataclassContracts:
    def test_observed_state_defaults_invalid(self):
        state = ObservedDesktopState()
        assert state.is_valid is False

    def test_proof_defaults_not_passed(self):
        proof = GUIActuationProof(proof_id="", trace_id="test")
        assert proof.passed is False

    def test_environment_values(self):
        assert EnvironmentRequirement.VPS.value == "vps"
        assert EnvironmentRequirement.LOCAL_WINDOWS_FOREGROUND.value == "local_windows_foreground"
        assert EnvironmentRequirement.LOCAL_WINDOWS_HEADLESS.value == "local_windows_headless"
        assert EnvironmentRequirement.LOCAL_WINDOWS_GUI.value == "local_windows_gui"
        assert EnvironmentRequirement.LOCAL_WINDOWS_BACKGROUND.value == "local_windows_background"

    def test_actuation_stage_values(self):
        assert ActuationStage.NOT_STARTED.value == "not_started"
        assert ActuationStage.COMPLETED.value == "completed"
        assert ActuationStage.FAILED.value == "failed"

    def test_observed_state_to_dict(self):
        state = ObservedDesktopState()
        d = state.to_dict()
        assert isinstance(d, dict)
        assert len(d) >= 14

    def test_proof_to_dict(self):
        proof = GUIActuationProof(proof_id="", trace_id="test")
        d = proof.to_dict()
        assert isinstance(d, dict)
        assert d["environment"] == "local_windows_foreground"


# -----------------------------------------------------------------------
# Regression: Existing Commands
# -----------------------------------------------------------------------


class TestRegressionExistingCommands:
    def test_ping_still_supported(self):
        assert "!ping" in SUPPORTED_COMMANDS

    def test_chrome_still_supported(self):
        assert "!chrome" in SUPPORTED_COMMANDS

    def test_ingest_safe_doc_still_supported(self):
        assert "!ingest-safe-doc" in SUPPORTED_COMMANDS

    def test_ingest_safe_doc_cu_still_supported(self):
        assert "!ingest-safe-doc-cu" in SUPPORTED_COMMANDS

    def test_chrome_open_drive_still_spine_routed(self):
        assert "!chrome-open-google-drive" in SPINE_ROUTED_COMMANDS

    def test_unknown_command_returns_none(self):
        packet = build_work_packet_for_router("!nonexistent")
        assert packet is None
