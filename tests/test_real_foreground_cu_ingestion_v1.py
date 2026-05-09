"""Tests for Phase 96.8AH — Real Foreground CU Ingestion Proof.

Validates that foreground Computer Use ingestion enforces:
  - Foreground CU mode ONLY
  - API fallback BLOCKED
  - Headless BLOCKED
  - Background execution BLOCKED
  - Simulated extraction BLOCKED
  - Workstation readiness validated
  - Chrome process required
  - Window focus required
  - Founder confirmation required
  - Node sync required
  - Authority required
  - Identity-scoped artifacts
  - Transformation ledger valid
  - Replay deterministic
  - No auto-promotion
  - No world-model mutation

UMH substrate subsystem. Phase 96.8AH.
"""

from __future__ import annotations

import hashlib
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, "/opt/OS")

import pytest

from core.runtime.foreground_cu_verification_v1 import (
    FORBIDDEN_EXECUTION_MODES,
    FOREGROUND_CU_FORBIDDEN_ACTIONS,
    FOREGROUND_CU_REQUIRED_MODE,
    ExecutionMode,
    ForegroundCUProof,
    ForegroundCUVerification,
    WorkstationReadiness,
    build_foreground_cu_proof,
    persist_foreground_cu_proof,
    validate_execution_mode,
    validate_workstation_readiness,
)
from core.environment_bridge.chrome_visible_launch import (
    ChromeVisibleLaunchProof,
    ChromeVisibleLaunchStatus,
    visible_launch_proof_allows_next_gate,
)
from core.runtime.runtime_presence_state_v1 import (
    WorkstationPresenceState,
    is_execution_capable,
)
from core.state.transformation_state_ledger import (
    TransformationStage,
    VALID_TRANSITIONS,
)
from eos_ai.interfaces.discord_interface_adapter_v1 import (
    COMMAND_ACTION_MAP,
    COMMAND_CONTRACT,
    SPINE_ROUTED_COMMANDS,
    SUPPORTED_COMMANDS,
    build_work_packet_for_router,
)
from core.control_plane_router.router_contracts import (
    ALLOWED_ACTION_TYPES,
    CapabilityType,
)
from core.control_plane_router.control_plane_router_v1 import (
    ACTION_CAPABILITY_MAP,
)
from core.environment_bridge.windows_desktop_request_builder import (
    build_w0_real_foreground_cu_ingestion_request,
)


CU_CONFIG_PATH = Path("/opt/OS/config/w0_real_foreground_cu_ingestion_v1.json")


def _load_cu_config() -> dict:
    with open(CU_CONFIG_PATH) as f:
        return json.load(f)


def _make_ready_workstation() -> WorkstationReadiness:
    return WorkstationReadiness(
        windows_session_active=True,
        desktop_unlocked=True,
        chrome_available=True,
        gui_automation_available=True,
        monitor_attached=True,
        local_runtime_alive=True,
        node_parity_valid=True,
        foreground_session_owned=True,
    )


def _make_verified_cu() -> ForegroundCUVerification:
    return ForegroundCUVerification(
        chrome_running=True,
        window_visible=True,
        focus_confirmed=True,
        desktop_active=True,
        user_session_active=True,
        navigation_observed=True,
        extraction_observed=True,
        founder_confirmation_required=True,
        founder_confirmation_received=True,
        founder_confirmed=True,
    )


# -----------------------------------------------------------------------
# Command Registration
# -----------------------------------------------------------------------


class TestCommandRegistration:
    def test_cu_command_in_supported(self):
        assert "!ingest-safe-doc-cu" in SUPPORTED_COMMANDS

    def test_cu_command_action_mapping(self):
        assert COMMAND_ACTION_MAP["!ingest-safe-doc-cu"] == "ingest_safe_doc_cu"

    def test_cu_command_spine_routed(self):
        assert "!ingest-safe-doc-cu" in SPINE_ROUTED_COMMANDS

    def test_cu_command_contract_exists(self):
        assert "!ingest-safe-doc-cu" in COMMAND_CONTRACT

    def test_cu_command_contract_requires_foreground_cu(self):
        contract = COMMAND_CONTRACT["!ingest-safe-doc-cu"]
        assert contract["require_foreground_cu"] is True

    def test_cu_command_no_mutation(self):
        contract = COMMAND_CONTRACT["!ingest-safe-doc-cu"]
        assert contract["mutation_allowed"] is False

    def test_cu_command_proof_required(self):
        contract = COMMAND_CONTRACT["!ingest-safe-doc-cu"]
        assert contract["proof_required"] is True

    def test_cu_action_in_allowed_types(self):
        assert "ingest_safe_doc_cu" in ALLOWED_ACTION_TYPES

    def test_cu_action_capability_map(self):
        cap = ACTION_CAPABILITY_MAP["ingest_safe_doc_cu"]
        assert cap.capability_type == CapabilityType.DOCUMENT_EXTRACTION
        assert cap.requires_gui is True


# -----------------------------------------------------------------------
# Execution Mode Enforcement
# -----------------------------------------------------------------------


class TestExecutionModeEnforcement:
    def test_foreground_cu_is_required_mode(self):
        assert FOREGROUND_CU_REQUIRED_MODE == ExecutionMode.COMPUTER_USE_FOREGROUND

    def test_api_mode_forbidden(self):
        assert ExecutionMode.API in FORBIDDEN_EXECUTION_MODES

    def test_headless_mode_forbidden(self):
        assert ExecutionMode.HEADLESS in FORBIDDEN_EXECUTION_MODES

    def test_background_cu_forbidden(self):
        assert ExecutionMode.COMPUTER_USE_BACKGROUND in FORBIDDEN_EXECUTION_MODES

    def test_foreground_cu_not_forbidden(self):
        assert ExecutionMode.COMPUTER_USE_FOREGROUND not in FORBIDDEN_EXECUTION_MODES


class TestAPIFallbackBlocked:
    def test_api_blocked_by_config(self):
        config = _load_cu_config()
        assert config["allow_api_path"] is False

    def test_api_mode_validation_fails(self):
        config = {"require_foreground_cu": True, "allow_api_fallback": False}
        errors = validate_execution_mode(ExecutionMode.API, config)
        assert len(errors) >= 2
        assert any("api" in e for e in errors)

    def test_api_extraction_fallback_forbidden(self):
        assert "api_extraction_fallback" in FOREGROUND_CU_FORBIDDEN_ACTIONS


class TestHeadlessBlocked:
    def test_headless_mode_validation_fails(self):
        config = {"require_foreground_cu": True, "allow_headless": False}
        errors = validate_execution_mode(ExecutionMode.HEADLESS, config)
        assert len(errors) >= 2
        assert any("headless" in e for e in errors)

    def test_headless_browser_fallback_forbidden(self):
        assert "headless_browser_fallback" in FOREGROUND_CU_FORBIDDEN_ACTIONS


class TestBackgroundBlocked:
    def test_background_mode_validation_fails(self):
        config = {"require_foreground_cu": True}
        errors = validate_execution_mode(ExecutionMode.COMPUTER_USE_BACKGROUND, config)
        assert len(errors) >= 1

    def test_background_hidden_execution_forbidden(self):
        assert "background_hidden_execution" in FOREGROUND_CU_FORBIDDEN_ACTIONS


class TestSimulatedExtractionBlocked:
    def test_simulated_extraction_forbidden(self):
        assert "simulated_extraction" in FOREGROUND_CU_FORBIDDEN_ACTIONS

    def test_mock_browser_execution_forbidden(self):
        assert "mock_browser_execution" in FOREGROUND_CU_FORBIDDEN_ACTIONS

    def test_replay_only_validation_forbidden(self):
        assert "replay_only_validation" in FOREGROUND_CU_FORBIDDEN_ACTIONS

    def test_cached_extraction_reuse_forbidden(self):
        assert "cached_extraction_reuse" in FOREGROUND_CU_FORBIDDEN_ACTIONS


class TestForegroundCUAllowed:
    def test_foreground_cu_passes_validation(self):
        config = {
            "require_foreground_cu": True,
            "allow_api_fallback": False,
            "allow_headless": False,
        }
        errors = validate_execution_mode(ExecutionMode.COMPUTER_USE_FOREGROUND, config)
        assert errors == []


# -----------------------------------------------------------------------
# Workstation Readiness
# -----------------------------------------------------------------------


class TestWorkstationReadiness:
    def test_fully_ready(self):
        ws = _make_ready_workstation()
        assert ws.is_ready is True
        assert ws.denial_reasons == []

    def test_windows_session_required(self):
        ws = _make_ready_workstation()
        ws.windows_session_active = False
        assert ws.is_ready is False
        assert "windows_session_not_active" in ws.denial_reasons

    def test_desktop_must_be_unlocked(self):
        ws = _make_ready_workstation()
        ws.desktop_unlocked = False
        assert ws.is_ready is False
        assert "desktop_locked" in ws.denial_reasons

    def test_chrome_must_be_available(self):
        ws = _make_ready_workstation()
        ws.chrome_available = False
        assert ws.is_ready is False
        assert "chrome_not_available" in ws.denial_reasons

    def test_gui_automation_required(self):
        ws = _make_ready_workstation()
        ws.gui_automation_available = False
        assert ws.is_ready is False

    def test_local_runtime_required(self):
        ws = _make_ready_workstation()
        ws.local_runtime_alive = False
        assert ws.is_ready is False

    def test_node_parity_required(self):
        ws = _make_ready_workstation()
        ws.node_parity_valid = False
        assert ws.is_ready is False

    def test_foreground_session_required(self):
        ws = _make_ready_workstation()
        ws.foreground_session_owned = False
        assert ws.is_ready is False

    def test_to_dict_includes_all_fields(self):
        ws = _make_ready_workstation()
        d = ws.to_dict()
        assert "windows_session_active" in d
        assert "is_ready" in d
        assert "denial_reasons" in d

    def test_validate_workstation_windows_required(self):
        ws = _make_ready_workstation()
        ws.windows_session_active = False
        config = {"require_local_windows_desktop": True}
        errors = validate_workstation_readiness(ws, config)
        assert any("windows_session" in e for e in errors)

    def test_validate_workstation_active_session_required(self):
        ws = _make_ready_workstation()
        ws.foreground_session_owned = False
        config = {"require_active_session": True}
        errors = validate_workstation_readiness(ws, config)
        assert any("session" in e for e in errors)

    def test_validate_workstation_chrome_required(self):
        ws = _make_ready_workstation()
        ws.chrome_available = False
        config = {"require_chrome_process": True}
        errors = validate_workstation_readiness(ws, config)
        assert any("chrome" in e for e in errors)


# -----------------------------------------------------------------------
# Foreground CU Verification Contract
# -----------------------------------------------------------------------


class TestForegroundCUVerification:
    def test_fully_verified(self):
        v = _make_verified_cu()
        assert v.is_verified is True
        assert v.denial_reasons == []

    def test_chrome_not_running_denies(self):
        v = _make_verified_cu()
        v.chrome_running = False
        assert v.is_verified is False
        assert "chrome_not_running" in v.denial_reasons

    def test_window_not_visible_denies(self):
        v = _make_verified_cu()
        v.window_visible = False
        assert v.is_verified is False
        assert "window_not_visible" in v.denial_reasons

    def test_focus_not_confirmed_denies(self):
        v = _make_verified_cu()
        v.focus_confirmed = False
        assert v.is_verified is False
        assert "focus_not_confirmed" in v.denial_reasons

    def test_desktop_not_active_denies(self):
        v = _make_verified_cu()
        v.desktop_active = False
        assert v.is_verified is False

    def test_user_session_not_active_denies(self):
        v = _make_verified_cu()
        v.user_session_active = False
        assert v.is_verified is False

    def test_navigation_not_observed_denies(self):
        v = _make_verified_cu()
        v.navigation_observed = False
        assert v.is_verified is False
        assert "navigation_not_observed" in v.denial_reasons

    def test_extraction_not_observed_denies(self):
        v = _make_verified_cu()
        v.extraction_observed = False
        assert v.is_verified is False
        assert "extraction_not_observed" in v.denial_reasons

    def test_founder_not_confirmed_denies(self):
        v = _make_verified_cu()
        v.founder_confirmed = False
        assert v.is_verified is False
        assert "founder_not_confirmed" in v.denial_reasons

    def test_to_dict_includes_all_fields(self):
        v = _make_verified_cu()
        d = v.to_dict()
        assert "chrome_running" in d
        assert "is_verified" in d
        assert "denial_reasons" in d
        assert "founder_confirmation_required" in d


# -----------------------------------------------------------------------
# Foreground CU Proof
# -----------------------------------------------------------------------


class TestForegroundCUProof:
    def test_proof_auto_generates_id(self):
        proof = ForegroundCUProof(proof_id="", trace_id="test-trace")
        assert proof.proof_id.startswith("FGCU-PROOF-")

    def test_proof_auto_generates_timestamp(self):
        proof = ForegroundCUProof(proof_id="", trace_id="test-trace")
        assert proof.timestamp != ""

    def test_proof_auto_generates_session_id(self):
        proof = ForegroundCUProof(proof_id="", trace_id="test-trace")
        assert proof.workstation_session_id.startswith("SESSION-")

    def test_proof_execution_mode_is_foreground_cu(self):
        proof = ForegroundCUProof(proof_id="", trace_id="test-trace")
        assert proof.execution_mode == ExecutionMode.COMPUTER_USE_FOREGROUND.value

    def test_proof_passed_requires_verification(self):
        proof = ForegroundCUProof(proof_id="", trace_id="test-trace")
        assert proof.passed is False

    def test_proof_passed_with_verified_cu(self):
        proof = ForegroundCUProof(
            proof_id="",
            trace_id="test-trace",
            cu_verification=_make_verified_cu(),
        )
        assert proof.passed is True

    def test_proof_not_passed_with_partial_cu(self):
        v = _make_verified_cu()
        v.founder_confirmed = False
        proof = ForegroundCUProof(
            proof_id="",
            trace_id="test-trace",
            cu_verification=v,
        )
        assert proof.passed is False

    def test_replay_hash_deterministic(self):
        proof = ForegroundCUProof(
            proof_id="FGCU-PROOF-test",
            trace_id="test-trace",
            chrome_pid=12345,
            stages_completed=["stage_a", "stage_b"],
        )
        h1 = proof.compute_replay_hash()
        h2 = proof.compute_replay_hash()
        assert h1 == h2
        assert len(h1) == 64

    def test_to_dict_includes_all_fields(self):
        proof = ForegroundCUProof(
            proof_id="",
            trace_id="test-trace",
            workstation_readiness=_make_ready_workstation(),
            cu_verification=_make_verified_cu(),
        )
        d = proof.to_dict()
        assert "proof_id" in d
        assert "execution_mode" in d
        assert "workstation_readiness" in d
        assert "cu_verification" in d
        assert "passed" in d
        assert "replay_hash" in d


# -----------------------------------------------------------------------
# Build + Persist Proof
# -----------------------------------------------------------------------


class TestBuildAndPersistProof:
    def test_build_proof(self):
        proof = build_foreground_cu_proof(
            trace_id="build-test",
            workstation_readiness=_make_ready_workstation(),
            cu_verification=_make_verified_cu(),
            chrome_pid=9999,
            stages_completed=["validated", "launched"],
        )
        assert proof.trace_id == "build-test"
        assert proof.chrome_pid == 9999
        assert proof.replay_hash != ""
        assert proof.passed is True

    def test_persist_proof(self, tmp_path):
        proof = build_foreground_cu_proof(
            trace_id="persist-test",
            workstation_readiness=_make_ready_workstation(),
            cu_verification=_make_verified_cu(),
        )
        path = persist_foreground_cu_proof(proof, tmp_path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["proof_id"] == proof.proof_id
        assert data["passed"] is True

    def test_persist_creates_directory(self, tmp_path):
        proof_dir = tmp_path / "nested" / "proofs"
        proof = build_foreground_cu_proof(
            trace_id="nested-test",
            workstation_readiness=_make_ready_workstation(),
            cu_verification=_make_verified_cu(),
        )
        path = persist_foreground_cu_proof(proof, proof_dir)
        assert path.exists()


# -----------------------------------------------------------------------
# Config Validation
# -----------------------------------------------------------------------


class TestCUConfig:
    def test_config_exists(self):
        assert CU_CONFIG_PATH.exists()

    def test_config_valid_json(self):
        config = _load_cu_config()
        assert isinstance(config, dict)

    def test_config_requires_foreground_cu(self):
        config = _load_cu_config()
        assert config["require_foreground_cu"] is True

    def test_config_blocks_api(self):
        config = _load_cu_config()
        assert config["allow_api_path"] is False

    def test_config_allows_cu(self):
        config = _load_cu_config()
        assert config["allow_cu_path"] is True

    def test_config_requires_windows_desktop(self):
        config = _load_cu_config()
        assert config["require_local_windows_desktop"] is True

    def test_config_requires_active_session(self):
        config = _load_cu_config()
        assert config["require_active_session"] is True

    def test_config_requires_chrome_process(self):
        config = _load_cu_config()
        assert config["require_chrome_process"] is True

    def test_config_requires_founder_confirmation(self):
        config = _load_cu_config()
        assert config["require_founder_confirmation"] is True

    def test_config_requires_node_sync(self):
        config = _load_cu_config()
        assert config["require_node_sync"] is True

    def test_config_governance_required(self):
        config = _load_cu_config()
        assert config["governance_required_for_promotion"] is True

    def test_config_forbidden_actions_include_api_fallback(self):
        config = _load_cu_config()
        assert "api_extraction_fallback" in config["forbidden_actions"]

    def test_config_forbidden_actions_include_headless(self):
        config = _load_cu_config()
        assert "headless_browser_fallback" in config["forbidden_actions"]

    def test_config_forbidden_actions_include_simulated(self):
        config = _load_cu_config()
        assert "simulated_extraction" in config["forbidden_actions"]

    def test_config_forbidden_actions_include_background(self):
        config = _load_cu_config()
        assert "background_hidden_execution" in config["forbidden_actions"]

    def test_config_has_safe_doc_url(self):
        config = _load_cu_config()
        assert config["safe_doc_url_or_id"] != ""

    def test_config_has_google_identity(self):
        config = _load_cu_config()
        assert config["google_account_identity"] != ""


# -----------------------------------------------------------------------
# Transformation Ledger Stages
# -----------------------------------------------------------------------


class TestForegroundCULedgerStages:
    def test_foreground_runtime_validated_exists(self):
        assert hasattr(TransformationStage, "FOREGROUND_RUNTIME_VALIDATED")

    def test_chrome_process_started_exists(self):
        assert hasattr(TransformationStage, "CHROME_PROCESS_STARTED")

    def test_window_focus_confirmed_exists(self):
        assert hasattr(TransformationStage, "WINDOW_FOCUS_CONFIRMED")

    def test_visible_navigation_confirmed_exists(self):
        assert hasattr(TransformationStage, "VISIBLE_NAVIGATION_CONFIRMED")

    def test_visible_extraction_confirmed_exists(self):
        assert hasattr(TransformationStage, "VISIBLE_EXTRACTION_CONFIRMED")

    def test_foreground_cu_completed_exists(self):
        assert hasattr(TransformationStage, "FOREGROUND_CU_COMPLETED")


class TestForegroundCULedgerTransitions:
    def test_runtime_executing_can_reach_foreground_validated(self):
        targets = VALID_TRANSITIONS[TransformationStage.RUNTIME_EXECUTING]
        assert TransformationStage.FOREGROUND_RUNTIME_VALIDATED in targets

    def test_foreground_validated_to_chrome_started(self):
        targets = VALID_TRANSITIONS[TransformationStage.FOREGROUND_RUNTIME_VALIDATED]
        assert TransformationStage.CHROME_PROCESS_STARTED in targets

    def test_chrome_started_to_focus_confirmed(self):
        targets = VALID_TRANSITIONS[TransformationStage.CHROME_PROCESS_STARTED]
        assert TransformationStage.WINDOW_FOCUS_CONFIRMED in targets

    def test_focus_confirmed_to_navigation(self):
        targets = VALID_TRANSITIONS[TransformationStage.WINDOW_FOCUS_CONFIRMED]
        assert TransformationStage.VISIBLE_NAVIGATION_CONFIRMED in targets

    def test_navigation_to_extraction(self):
        targets = VALID_TRANSITIONS[TransformationStage.VISIBLE_NAVIGATION_CONFIRMED]
        assert TransformationStage.VISIBLE_EXTRACTION_CONFIRMED in targets

    def test_extraction_to_completed(self):
        targets = VALID_TRANSITIONS[TransformationStage.VISIBLE_EXTRACTION_CONFIRMED]
        assert TransformationStage.FOREGROUND_CU_COMPLETED in targets

    def test_completed_to_proof_captured(self):
        targets = VALID_TRANSITIONS[TransformationStage.FOREGROUND_CU_COMPLETED]
        assert TransformationStage.PROOF_CAPTURED in targets

    def test_all_cu_stages_can_fail(self):
        failable = [
            TransformationStage.FOREGROUND_RUNTIME_VALIDATED,
            TransformationStage.CHROME_PROCESS_STARTED,
            TransformationStage.WINDOW_FOCUS_CONFIRMED,
            TransformationStage.VISIBLE_NAVIGATION_CONFIRMED,
            TransformationStage.VISIBLE_EXTRACTION_CONFIRMED,
        ]
        for stage in failable:
            assert TransformationStage.RUNTIME_FAILED in VALID_TRANSITIONS[stage]

    def test_full_cu_chain_is_valid(self):
        chain = [
            TransformationStage.RUNTIME_EXECUTING,
            TransformationStage.FOREGROUND_RUNTIME_VALIDATED,
            TransformationStage.CHROME_PROCESS_STARTED,
            TransformationStage.WINDOW_FOCUS_CONFIRMED,
            TransformationStage.VISIBLE_NAVIGATION_CONFIRMED,
            TransformationStage.VISIBLE_EXTRACTION_CONFIRMED,
            TransformationStage.FOREGROUND_CU_COMPLETED,
            TransformationStage.PROOF_CAPTURED,
        ]
        for i in range(len(chain) - 1):
            assert chain[i + 1] in VALID_TRANSITIONS[chain[i]]


# -----------------------------------------------------------------------
# Chrome Visible Launch Composition
# -----------------------------------------------------------------------


class TestChromeVisibleLaunchComposition:
    def test_chrome_launch_proof_exists(self):
        proof = ChromeVisibleLaunchProof(
            process_ids=[1234],
            status=ChromeVisibleLaunchStatus.FOUNDER_CONFIRMED_VISIBLE,
        )
        assert 1234 in proof.process_ids

    def test_chrome_launch_not_confirmed_blocks_gate(self):
        proof = ChromeVisibleLaunchProof(
            process_ids=[1234],
            status=ChromeVisibleLaunchStatus.PENDING_FOUNDER_VISUAL_CONFIRMATION,
            founder_confirmed=False,
        )
        assert visible_launch_proof_allows_next_gate(proof) is False

    def test_chrome_launch_confirmed_allows_gate(self):
        proof = ChromeVisibleLaunchProof(
            process_ids=[1234],
            status=ChromeVisibleLaunchStatus.FOUNDER_CONFIRMED_VISIBLE,
            founder_confirmed=True,
        )
        assert visible_launch_proof_allows_next_gate(proof) is True


# -----------------------------------------------------------------------
# Workstation Presence Composition
# -----------------------------------------------------------------------


class TestWorkstationPresenceComposition:
    def test_active_state_is_execution_capable(self):
        assert is_execution_capable(WorkstationPresenceState.ACTIVE) is True

    def test_executing_state_is_execution_capable(self):
        assert is_execution_capable(WorkstationPresenceState.EXECUTING) is True

    def test_disconnected_not_execution_capable(self):
        assert is_execution_capable(WorkstationPresenceState.DISCONNECTED) is False

    def test_idle_is_execution_capable(self):
        assert is_execution_capable(WorkstationPresenceState.IDLE) is True


# -----------------------------------------------------------------------
# Request Builder
# -----------------------------------------------------------------------


class TestRequestBuilder:
    def test_cu_request_builds(self):
        req = build_w0_real_foreground_cu_ingestion_request()
        assert req.action_type == "ingest_safe_doc_cu"

    def test_cu_request_has_fgcu_proof_required(self):
        req = build_w0_real_foreground_cu_ingestion_request()
        assert req.proof_required == "foreground_cu_verification"

    def test_cu_request_no_mutation(self):
        req = build_w0_real_foreground_cu_ingestion_request()
        assert req.no_mutation is True

    def test_cu_request_notes_block_api(self):
        req = build_w0_real_foreground_cu_ingestion_request()
        notes_text = " ".join(req.notes).lower()
        assert "no api fallback" in notes_text

    def test_cu_request_notes_block_headless(self):
        req = build_w0_real_foreground_cu_ingestion_request()
        notes_text = " ".join(req.notes).lower()
        assert "no headless" in notes_text

    def test_cu_request_has_trace_id(self):
        req = build_w0_real_foreground_cu_ingestion_request()
        assert req.trace_id.startswith("W0-fgcu-ingest-")


# -----------------------------------------------------------------------
# WorkPacket Builder
# -----------------------------------------------------------------------


class TestWorkPacketBuilder:
    def test_cu_command_builds_packet(self):
        packet = build_work_packet_for_router("!ingest-safe-doc-cu")
        assert packet is not None
        assert packet.action_type == "ingest_safe_doc_cu"

    def test_cu_packet_has_trace_id(self):
        packet = build_work_packet_for_router("!ingest-safe-doc-cu")
        assert packet.trace_id != ""

    def test_cu_packet_has_source_interface(self):
        packet = build_work_packet_for_router("!ingest-safe-doc-cu")
        assert packet.source_interface == "discord_interface_adapter_v1"


# -----------------------------------------------------------------------
# Adapter Registry
# -----------------------------------------------------------------------


class TestAdapterRegistry:
    def test_worker_has_cu_capability(self):
        with open("data/registries/local_worker_adapter_registry_v1.json") as f:
            reg = json.load(f)
        caps = reg["workers"]["windows_interactive_desktop_relay"]["capabilities"]
        assert "ingest_safe_doc_cu" in caps

    def test_adapter_has_cu_capability(self):
        with open("data/registries/local_worker_adapter_registry_v1.json") as f:
            reg = json.load(f)
        adapter_caps = reg["adapters"]["windows_interactive_desktop_relay"]["capabilities"]
        cu_caps = [c for c in adapter_caps if c["capability_id"] == "ingest_safe_doc_cu"]
        assert len(cu_caps) == 1

    def test_adapter_cu_requires_gui(self):
        with open("data/registries/local_worker_adapter_registry_v1.json") as f:
            reg = json.load(f)
        adapter_caps = reg["adapters"]["windows_interactive_desktop_relay"]["capabilities"]
        cu_cap = next(c for c in adapter_caps if c["capability_id"] == "ingest_safe_doc_cu")
        assert cu_cap["requires_gui"] is True


# -----------------------------------------------------------------------
# Forbidden Actions
# -----------------------------------------------------------------------


class TestForbiddenActions:
    def test_api_extraction_fallback(self):
        assert "api_extraction_fallback" in FOREGROUND_CU_FORBIDDEN_ACTIONS

    def test_headless_browser_fallback(self):
        assert "headless_browser_fallback" in FOREGROUND_CU_FORBIDDEN_ACTIONS

    def test_simulated_extraction(self):
        assert "simulated_extraction" in FOREGROUND_CU_FORBIDDEN_ACTIONS

    def test_background_hidden_execution(self):
        assert "background_hidden_execution" in FOREGROUND_CU_FORBIDDEN_ACTIONS

    def test_mock_browser_execution(self):
        assert "mock_browser_execution" in FOREGROUND_CU_FORBIDDEN_ACTIONS

    def test_broad_drive_ingestion(self):
        assert "broad_drive_ingestion" in FOREGROUND_CU_FORBIDDEN_ACTIONS

    def test_mutate_drive(self):
        assert "mutate_drive" in FOREGROUND_CU_FORBIDDEN_ACTIONS

    def test_mutate_docs(self):
        assert "mutate_docs" in FOREGROUND_CU_FORBIDDEN_ACTIONS

    def test_auto_promote(self):
        assert "auto_promote_canonical_truth" in FOREGROUND_CU_FORBIDDEN_ACTIONS

    def test_mutate_world_model(self):
        assert "mutate_world_model" in FOREGROUND_CU_FORBIDDEN_ACTIONS

    def test_recursively_ingest(self):
        assert "recursively_ingest" in FOREGROUND_CU_FORBIDDEN_ACTIONS

    def test_credential_access(self):
        assert "credential_access" in FOREGROUND_CU_FORBIDDEN_ACTIONS

    def test_screenshot_as_primary_extraction(self):
        assert "screenshot_as_primary_extraction" in FOREGROUND_CU_FORBIDDEN_ACTIONS


# -----------------------------------------------------------------------
# No Auto-Promotion / No World-Model Mutation
# -----------------------------------------------------------------------


class TestNoAutoPromotion:
    def test_auto_promote_forbidden_in_actions(self):
        assert "auto_promote_canonical_truth" in FOREGROUND_CU_FORBIDDEN_ACTIONS

    def test_auto_promote_forbidden_in_config(self):
        config = _load_cu_config()
        assert "auto_promote_canonical_truth" in config["forbidden_actions"]

    def test_governance_required_for_promotion(self):
        config = _load_cu_config()
        assert config["governance_required_for_promotion"] is True


class TestNoWorldModelMutation:
    def test_world_model_mutation_forbidden_in_actions(self):
        assert "mutate_world_model" in FOREGROUND_CU_FORBIDDEN_ACTIONS

    def test_world_model_mutation_forbidden_in_config(self):
        config = _load_cu_config()
        assert "mutate_world_model" in config["forbidden_actions"]


# -----------------------------------------------------------------------
# Spine Integration
# -----------------------------------------------------------------------


class TestSpineIntegration:
    def test_spine_capability_authority_includes_cu(self):
        from core.governance.execution_authority_engine_v1 import CapabilityAuthority

        cap_auth = CapabilityAuthority(
            adapter_id="windows_interactive_desktop_relay",
            capabilities=[
                "browser_execution",
                "chrome_launch",
                "chrome_open_google_drive",
                "ingest_safe_doc",
                "ingest_safe_doc_cu",
                "open_application_url",
            ],
            is_configured=True,
            is_mature=True,
        )
        assert "ingest_safe_doc_cu" in cap_auth.capabilities

    def test_spine_integration_source_has_cu(self):
        import inspect
        from eos_ai.interfaces import discord_spine_integration_v1

        src = inspect.getsource(discord_spine_integration_v1.build_spine_infrastructure)
        assert "ingest_safe_doc_cu" in src


# -----------------------------------------------------------------------
# Dataclass Contracts
# -----------------------------------------------------------------------


class TestDataclassContracts:
    def test_workstation_readiness_defaults_not_ready(self):
        ws = WorkstationReadiness()
        assert ws.is_ready is False

    def test_cu_verification_defaults_not_verified(self):
        v = ForegroundCUVerification()
        assert v.is_verified is False

    def test_proof_defaults_not_passed(self):
        proof = ForegroundCUProof(proof_id="", trace_id="test")
        assert proof.passed is False

    def test_execution_mode_values(self):
        assert ExecutionMode.API.value == "api"
        assert ExecutionMode.HEADLESS.value == "headless"
        assert ExecutionMode.COMPUTER_USE_FOREGROUND.value == "computer_use_foreground"
        assert ExecutionMode.COMPUTER_USE_BACKGROUND.value == "computer_use_background"

    def test_workstation_readiness_to_dict(self):
        ws = WorkstationReadiness()
        d = ws.to_dict()
        assert isinstance(d, dict)
        assert len(d) >= 8

    def test_cu_verification_to_dict(self):
        v = ForegroundCUVerification()
        d = v.to_dict()
        assert isinstance(d, dict)
        assert len(d) >= 10

    def test_proof_to_dict(self):
        proof = ForegroundCUProof(proof_id="", trace_id="test")
        d = proof.to_dict()
        assert isinstance(d, dict)
        assert "execution_mode" in d
        assert d["execution_mode"] == "computer_use_foreground"


# -----------------------------------------------------------------------
# Regression: Existing Commands Still Work
# -----------------------------------------------------------------------


class TestRegressionExistingCommands:
    def test_ping_still_supported(self):
        assert "!ping" in SUPPORTED_COMMANDS

    def test_chrome_still_supported(self):
        assert "!chrome" in SUPPORTED_COMMANDS

    def test_ingest_safe_doc_still_supported(self):
        assert "!ingest-safe-doc" in SUPPORTED_COMMANDS

    def test_chrome_open_drive_still_spine_routed(self):
        assert "!chrome-open-google-drive" in SPINE_ROUTED_COMMANDS

    def test_unknown_command_returns_none(self):
        packet = build_work_packet_for_router("!nonexistent")
        assert packet is None

    def test_ingest_safe_doc_still_builds(self):
        packet = build_work_packet_for_router("!ingest-safe-doc")
        assert packet is not None
        assert packet.action_type == "ingest_safe_doc"
