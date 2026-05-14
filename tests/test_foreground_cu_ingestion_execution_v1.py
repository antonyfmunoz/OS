"""Tests for Phase 96.8AS — Foreground CU Ingestion Execution.

Verifies:
  1. CUIngestionEvidence creation, properties, serialization
  2. Dry run always L0, always blocked
  3. Headless/API mode blocked (via existing contracts)
  4. Stale relay blocked from execution
  5. Missing screenshot blocks maturity
  6. Missing extraction blocks maturity
  7. Missing founder confirmation blocks maturity
  8. Canonical/instance candidate classification
  9. Candidate leakage blocked (instance defaults)
  10. Successful full ingestion escalates maturity
  11. Evidence extraction from relay result
  12. Proof persistence
  13. Full build_full_ingestion_proof pipeline
  14. Transport integration with ingestion
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from execution.workers.workstation.foreground_cu_ingestion_execution_v1 import (
    CANDIDATE_TYPE_CANONICAL,
    CANDIDATE_TYPE_INSTANCE,
    CU_INGESTION_MATURITY_REQUIREMENTS,
    CUIngestionEvidence,
    CUIngestionProof,
    IngestionCandidate,
    build_full_ingestion_proof,
    classify_candidate_type,
    classify_cu_ingestion,
    compute_ingestion_maturity,
    extract_ingestion_evidence,
    generate_candidates_from_extraction,
    ingestion_maturity_ceiling,
    persist_cu_ingestion_proof,
)
from execution.actuation.actuator_maturity_v1 import ActuatorMaturityLevel


def _full_evidence(**overrides: object) -> CUIngestionEvidence:
    defaults = {
        "chrome_pid": 9876,
        "window_handle": 0x00AA11BB,
        "window_title": "EOS W0 Test Document - Google Docs - Google Chrome",
        "foreground_focused": True,
        "navigation_observed": True,
        "navigation_url": "https://docs.google.com/document/d/EOS-W0-SAFE-TEST-DOC/edit",
        "screenshot_path": "/proof/nav.png",
        "screenshot_hash": "abc123def456",
        "extraction_completed": True,
        "extracted_title": "EOS W0 Test Document",
        "extracted_content_length": 2500,
        "extracted_content_preview": "This is the EOS W0 test document content...",
        "extracted_content_hash": "contenthash789",
        "desktop_unlocked": True,
        "desktop_session_active": True,
        "monitor_detected": True,
        "founder_confirmed": True,
        "relay_node_id": "WRN-test",
        "relay_machine": "DESKTOP-TEST",
        "is_dry_run": False,
        "trace_id": "TR-test-001",
        "request_id": "REQ-test-001",
    }
    defaults.update(overrides)
    return CUIngestionEvidence(**defaults)


def _full_relay_result(**overrides: object) -> dict:
    result = {
        "request_id": "REQ-W0-FGCU-INGEST-test001",
        "trace_id": "W0-fgcu-ingest-test001",
        "action_type": "ingest_safe_doc_cu",
        "adapter_status": "completed",
        "process_id": 9876,
        "dry_run": False,
        "node_id": "WRN-test",
        "machine_name": "DESKTOP-TEST",
        "observed_desktop_state": {
            "chrome_pid": 9876,
            "window_handle": 0x00AA11BB,
            "window_title": "EOS W0 Test Document - Google Docs - Google Chrome",
            "focused": True,
            "navigation_detected": True,
            "navigation_url": "https://docs.google.com/document/d/EOS-W0-SAFE-TEST-DOC/edit",
            "screenshot_path": "/proof/nav.png",
            "screenshot_hash": "abc123def456",
            "desktop_unlocked": True,
            "active_user_session": True,
            "monitor_detected": True,
        },
        "extraction_result": {
            "completed": True,
            "title": "EOS W0 Test Document",
            "content_length": 2500,
            "content_preview": "This is the EOS W0 test document content...",
            "content_hash": "contenthash789",
            "headings": ["Introduction", "Architecture", "Implementation"],
            "links": ["https://example.com/ref"],
            "method": "clipboard_select_all",
        },
        "stages_completed": [
            "relay_dispatched",
            "chrome_launched",
            "process_verified",
            "window_detected",
            "focus_confirmed",
            "navigation_confirmed",
            "screenshot_captured",
            "extraction_completed",
        ],
    }
    result.update(overrides)
    return result


class TestCUIngestionEvidence:
    def test_default_evidence(self) -> None:
        e = CUIngestionEvidence()
        assert e.chrome_pid == 0
        assert not e.has_chrome_pid
        assert not e.has_window_handle
        assert not e.has_screenshot
        assert not e.has_extraction
        assert not e.has_navigation

    def test_full_evidence_properties(self) -> None:
        e = _full_evidence()
        assert e.has_chrome_pid
        assert e.has_window_handle
        assert e.has_screenshot
        assert e.has_extraction
        assert e.has_navigation
        assert e.missing_evidence == []

    def test_missing_evidence_list(self) -> None:
        e = CUIngestionEvidence()
        missing = e.missing_evidence
        assert "chrome_pid" in missing
        assert "window_handle" in missing
        assert "foreground_focused" in missing
        assert "navigation_observed" in missing
        assert "screenshot" in missing
        assert "extraction" in missing
        assert "founder_confirmed" in missing

    def test_partial_evidence(self) -> None:
        e = _full_evidence(extraction_completed=False, extracted_content_length=0)
        assert e.has_chrome_pid
        assert not e.has_extraction
        assert "extraction" in e.missing_evidence

    def test_to_dict_serializable(self) -> None:
        e = _full_evidence()
        d = e.to_dict()
        serialized = json.dumps(d)
        assert len(serialized) > 0
        assert d["chrome_pid"] == 9876
        assert d["extraction_completed"] is True


class TestDryRunBlocked:
    def test_dry_run_always_l0(self) -> None:
        e = _full_evidence(is_dry_run=True)
        proof = classify_cu_ingestion(e)
        assert proof.maturity_level == ActuatorMaturityLevel.L0_SIMULATED

    def test_dry_run_ceiling_l0(self) -> None:
        e = _full_evidence(is_dry_run=True)
        proof = classify_cu_ingestion(e)
        assert proof.maturity_ceiling == ActuatorMaturityLevel.L0_SIMULATED

    def test_dry_run_escalation_blocked(self) -> None:
        e = _full_evidence(is_dry_run=True)
        proof = classify_cu_ingestion(e)
        assert proof.escalation_blocked is True
        assert "dry_run" in proof.escalation_reason

    def test_dry_run_with_full_evidence_still_l0(self) -> None:
        e = _full_evidence(is_dry_run=True)
        level = compute_ingestion_maturity(e)
        assert level == ActuatorMaturityLevel.L0_SIMULATED


class TestHeadlessBlocked:
    def test_foreground_cu_forbidden_modes(self) -> None:
        from execution.runtime.foreground_cu_verification_v1 import (
            FORBIDDEN_EXECUTION_MODES,
            ExecutionMode,
        )

        assert ExecutionMode.API in FORBIDDEN_EXECUTION_MODES
        assert ExecutionMode.HEADLESS in FORBIDDEN_EXECUTION_MODES
        assert ExecutionMode.COMPUTER_USE_BACKGROUND in FORBIDDEN_EXECUTION_MODES
        assert ExecutionMode.COMPUTER_USE_FOREGROUND not in FORBIDDEN_EXECUTION_MODES

    def test_api_mode_blocked_by_config(self) -> None:
        from execution.runtime.foreground_cu_verification_v1 import (
            ExecutionMode,
            validate_execution_mode,
        )

        config = {"require_foreground_cu": True, "allow_api_fallback": False}
        errors = validate_execution_mode(ExecutionMode.API, config)
        assert len(errors) > 0


class TestStaleRelayBlocked:
    def test_stale_heartbeat_blocks(self, tmp_path: Path) -> None:
        from datetime import datetime, timedelta, timezone
        from execution.workers.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            write_relay_heartbeat,
        )
        from execution.workers.workstation.workstation_relay_self_heal_v1 import (
            should_allow_chrome_proof,
        )

        now = datetime.now(timezone.utc)
        hb = RelayHeartbeat(
            node_id="WRN-stale",
            desktop_session_active=True,
            chrome_available=True,
            timestamp=(now - timedelta(seconds=300)).isoformat(),
        )
        write_relay_heartbeat(hb, tmp_path)

        allowed, reason = should_allow_chrome_proof(tmp_path)
        assert allowed is False


class TestMissingScreenshotBlocks:
    def test_no_screenshot_caps_maturity(self) -> None:
        e = _full_evidence(screenshot_path="", screenshot_hash="")
        ceiling = ingestion_maturity_ceiling(e)
        assert ceiling == ActuatorMaturityLevel.L4_NAVIGATION_OBSERVED

    def test_no_screenshot_blocks_escalation(self) -> None:
        e = _full_evidence(screenshot_path="", screenshot_hash="")
        proof = classify_cu_ingestion(e)
        assert proof.escalation_blocked is True
        assert "screenshot" in proof.evidence.missing_evidence


class TestMissingExtractionBlocks:
    def test_no_extraction_caps_maturity(self) -> None:
        e = _full_evidence(extraction_completed=False, extracted_content_length=0)
        ceiling = ingestion_maturity_ceiling(e)
        assert ceiling == ActuatorMaturityLevel.L5_SCREENSHOT_VERIFIED

    def test_no_extraction_blocks_escalation(self) -> None:
        e = _full_evidence(extraction_completed=False, extracted_content_length=0)
        proof = classify_cu_ingestion(e)
        assert proof.escalation_blocked is True
        assert "extraction" in proof.escalation_reason

    def test_extraction_completed_but_empty_blocks(self) -> None:
        e = _full_evidence(extraction_completed=True, extracted_content_length=0)
        assert not e.has_extraction
        proof = classify_cu_ingestion(e)
        assert proof.escalation_blocked is True


class TestMissingFounderBlocks:
    def test_no_founder_caps_maturity(self) -> None:
        e = _full_evidence(founder_confirmed=False)
        ceiling = ingestion_maturity_ceiling(e)
        assert ceiling == ActuatorMaturityLevel.L5_SCREENSHOT_VERIFIED

    def test_no_founder_blocks_escalation(self) -> None:
        e = _full_evidence(founder_confirmed=False)
        proof = classify_cu_ingestion(e)
        assert proof.escalation_blocked is True
        assert "founder" in proof.escalation_reason


class TestCandidateClassification:
    def test_template_is_canonical(self) -> None:
        assert classify_candidate_type("Project Template", "") == CANDIDATE_TYPE_CANONICAL

    def test_schema_is_canonical(self) -> None:
        assert classify_candidate_type("Database Schema", "") == CANDIDATE_TYPE_CANONICAL

    def test_framework_is_canonical(self) -> None:
        assert classify_candidate_type("", "reusable framework pattern") == CANDIDATE_TYPE_CANONICAL

    def test_personal_is_instance(self) -> None:
        assert classify_candidate_type("Personal Notes", "") == CANDIDATE_TYPE_INSTANCE

    def test_account_is_instance(self) -> None:
        assert classify_candidate_type("Account Settings", "") == CANDIDATE_TYPE_INSTANCE

    def test_founder_is_instance(self) -> None:
        assert classify_candidate_type("Founder Meeting Notes", "") == CANDIDATE_TYPE_INSTANCE

    def test_ambiguous_defaults_to_instance(self) -> None:
        assert classify_candidate_type("Random Document", "") == CANDIDATE_TYPE_INSTANCE

    def test_mixed_signals_instance_wins(self) -> None:
        result = classify_candidate_type("Personal Template", "founder's schema for account")
        assert result == CANDIDATE_TYPE_INSTANCE


class TestCandidateLeakageBlocked:
    def test_default_scope_is_instance(self) -> None:
        c = IngestionCandidate(candidate_type=CANDIDATE_TYPE_INSTANCE, label="test")
        assert c.memory_scope == "instance_memory"

    def test_generated_candidates_default_instance_scope(self) -> None:
        extraction = {
            "title": "My Personal Notes",
            "content_preview": "Private business meeting notes",
            "headings": [],
            "links": [],
        }
        candidates = generate_candidates_from_extraction(extraction)
        for c in candidates:
            assert c.memory_scope in ("instance_memory", "project_memory")


class TestSuccessfulIngestionEscalates:
    def test_full_evidence_not_blocked(self) -> None:
        e = _full_evidence()
        proof = classify_cu_ingestion(e)
        assert proof.escalation_blocked is False

    def test_full_evidence_above_l0(self) -> None:
        e = _full_evidence()
        proof = classify_cu_ingestion(e)
        assert proof.maturity_level.value >= ActuatorMaturityLevel.L1_PROCESS_STARTED.value

    def test_full_evidence_l7_achievable(self) -> None:
        e = _full_evidence()
        level = compute_ingestion_maturity(e)
        assert level == ActuatorMaturityLevel.L7_REPLAYABLE_ACTUATION

    def test_full_evidence_ceiling_l7(self) -> None:
        e = _full_evidence()
        ceiling = ingestion_maturity_ceiling(e)
        assert ceiling == ActuatorMaturityLevel.L7_REPLAYABLE_ACTUATION


class TestEvidenceExtraction:
    def test_extract_from_full_relay_result(self) -> None:
        relay = _full_relay_result()
        e = extract_ingestion_evidence(relay, founder_confirmed=True)
        assert e.chrome_pid == 9876
        assert e.has_window_handle
        assert e.foreground_focused
        assert e.navigation_observed
        assert e.has_screenshot
        assert e.has_extraction
        assert e.extracted_title == "EOS W0 Test Document"
        assert e.extracted_content_length == 2500
        assert e.founder_confirmed

    def test_extract_dry_run(self) -> None:
        relay = _full_relay_result(dry_run=True)
        relay["observed_desktop_state"] = {}
        relay["extraction_result"] = {}
        e = extract_ingestion_evidence(relay)
        assert e.is_dry_run is True

    def test_extract_missing_extraction(self) -> None:
        relay = _full_relay_result()
        relay["extraction_result"] = {}
        e = extract_ingestion_evidence(relay)
        assert not e.has_extraction

    def test_extract_missing_desktop_state(self) -> None:
        relay = _full_relay_result()
        relay["observed_desktop_state"] = {}
        e = extract_ingestion_evidence(relay)
        assert not e.has_chrome_pid
        assert not e.has_window_handle

    def test_founder_confirmed_from_parameter(self) -> None:
        relay = _full_relay_result()
        e_yes = extract_ingestion_evidence(relay, founder_confirmed=True)
        e_no = extract_ingestion_evidence(relay, founder_confirmed=False)
        assert e_yes.founder_confirmed is True
        assert e_no.founder_confirmed is False


class TestCandidateGeneration:
    def test_generates_title_candidate(self) -> None:
        extraction = {
            "title": "Test Document",
            "headings": [],
            "links": [],
            "content_preview": "",
        }
        candidates = generate_candidates_from_extraction(extraction)
        title_cands = [c for c in candidates if "document_title" in c.label]
        assert len(title_cands) == 1

    def test_generates_heading_candidates(self) -> None:
        extraction = {
            "title": "",
            "headings": ["Intro", "Methods", "Results"],
            "links": [],
            "content_preview": "",
        }
        candidates = generate_candidates_from_extraction(extraction)
        heading_cands = [c for c in candidates if "heading" in c.label]
        assert len(heading_cands) == 3

    def test_generates_content_candidate(self) -> None:
        extraction = {
            "title": "",
            "headings": [],
            "links": [],
            "content_preview": "Some document body text here",
        }
        candidates = generate_candidates_from_extraction(extraction)
        content_cands = [c for c in candidates if c.label == "document_content"]
        assert len(content_cands) == 1

    def test_generates_link_candidates(self) -> None:
        extraction = {
            "title": "",
            "headings": [],
            "links": ["https://example.com", "https://test.com"],
            "content_preview": "",
        }
        candidates = generate_candidates_from_extraction(extraction)
        link_cands = [c for c in candidates if "link" in c.label]
        assert len(link_cands) == 2

    def test_canonical_heading_classified(self) -> None:
        extraction = {
            "title": "",
            "headings": ["Template Schema"],
            "links": [],
            "content_preview": "",
        }
        candidates = generate_candidates_from_extraction(extraction)
        heading_cands = [c for c in candidates if "heading" in c.label]
        assert heading_cands[0].candidate_type == CANDIDATE_TYPE_CANONICAL

    def test_empty_extraction_no_candidates(self) -> None:
        extraction = {
            "title": "",
            "headings": [],
            "links": [],
            "content_preview": "",
        }
        candidates = generate_candidates_from_extraction(extraction)
        assert len(candidates) == 0


class TestProofPersistence:
    def test_persist_creates_file(self, tmp_path: Path) -> None:
        e = _full_evidence()
        proof = classify_cu_ingestion(e)
        path = persist_cu_ingestion_proof(proof, base_dir=tmp_path)
        assert path.exists()

    def test_persist_valid_json(self, tmp_path: Path) -> None:
        e = _full_evidence()
        proof = classify_cu_ingestion(e)
        path = persist_cu_ingestion_proof(proof, base_dir=tmp_path)
        data = json.loads(path.read_text())
        assert data["proof_type"] == "foreground_cu_ingestion"

    def test_persist_includes_evidence(self, tmp_path: Path) -> None:
        e = _full_evidence()
        proof = classify_cu_ingestion(e)
        path = persist_cu_ingestion_proof(proof, base_dir=tmp_path)
        data = json.loads(path.read_text())
        assert data["evidence"]["chrome_pid"] == 9876

    def test_persist_includes_candidates(self, tmp_path: Path) -> None:
        relay = _full_relay_result()
        proof = build_full_ingestion_proof(relay, founder_confirmed=True)
        path = persist_cu_ingestion_proof(proof, base_dir=tmp_path)
        data = json.loads(path.read_text())
        assert len(data["candidates"]) > 0


class TestProofSerialization:
    def test_proof_id_auto_generated(self) -> None:
        proof = CUIngestionProof(trace_id="test")
        assert proof.proof_id.startswith("CUIP-")

    def test_to_dict_serializable(self) -> None:
        e = _full_evidence()
        proof = classify_cu_ingestion(e)
        d = proof.to_dict()
        serialized = json.dumps(d)
        assert len(serialized) > 0

    def test_maturity_label_computed(self) -> None:
        e = _full_evidence()
        proof = classify_cu_ingestion(e)
        assert proof.maturity_label != "unknown"

    def test_candidate_to_dict(self) -> None:
        c = IngestionCandidate(
            candidate_type=CANDIDATE_TYPE_INSTANCE,
            label="test",
            content_preview="x" * 300,
        )
        d = c.to_dict()
        assert len(d["content_preview"]) <= 200
        assert d["candidate_id"].startswith("CAND-")


class TestBuildFullIngestionProof:
    def test_full_pipeline_success(self) -> None:
        relay = _full_relay_result()
        proof = build_full_ingestion_proof(relay, founder_confirmed=True)
        assert proof.escalation_blocked is False
        assert proof.maturity_level.value >= ActuatorMaturityLevel.L1_PROCESS_STARTED.value
        assert len(proof.candidates) > 0
        assert proof.canonical_count + proof.instance_count == len(proof.candidates)

    def test_full_pipeline_dry_run(self) -> None:
        relay = _full_relay_result(dry_run=True)
        relay["observed_desktop_state"] = {}
        relay["extraction_result"] = {}
        proof = build_full_ingestion_proof(relay)
        assert proof.maturity_level == ActuatorMaturityLevel.L0_SIMULATED
        assert proof.escalation_blocked is True
        assert len(proof.candidates) == 0

    def test_full_pipeline_no_extraction(self) -> None:
        relay = _full_relay_result()
        relay["extraction_result"] = {"completed": False}
        proof = build_full_ingestion_proof(relay, founder_confirmed=True)
        assert proof.escalation_blocked is True
        assert len(proof.candidates) == 0

    def test_full_pipeline_no_founder(self) -> None:
        relay = _full_relay_result()
        proof = build_full_ingestion_proof(relay, founder_confirmed=False)
        assert proof.escalation_blocked is True
        assert "founder" in proof.escalation_reason


class TestMaturityCeilings:
    def test_no_window_handle_caps_l1(self) -> None:
        e = _full_evidence(window_handle=0)
        ceiling = ingestion_maturity_ceiling(e)
        assert ceiling == ActuatorMaturityLevel.L1_PROCESS_STARTED

    def test_no_screenshot_caps_l4(self) -> None:
        e = _full_evidence(screenshot_path="", screenshot_hash="")
        ceiling = ingestion_maturity_ceiling(e)
        assert ceiling == ActuatorMaturityLevel.L4_NAVIGATION_OBSERVED

    def test_no_extraction_caps_l5(self) -> None:
        e = _full_evidence(extraction_completed=False, extracted_content_length=0)
        ceiling = ingestion_maturity_ceiling(e)
        assert ceiling == ActuatorMaturityLevel.L5_SCREENSHOT_VERIFIED

    def test_no_founder_caps_l5(self) -> None:
        e = _full_evidence(founder_confirmed=False)
        ceiling = ingestion_maturity_ceiling(e)
        assert ceiling == ActuatorMaturityLevel.L5_SCREENSHOT_VERIFIED

    def test_full_evidence_ceiling_l7(self) -> None:
        e = _full_evidence()
        ceiling = ingestion_maturity_ceiling(e)
        assert ceiling == ActuatorMaturityLevel.L7_REPLAYABLE_ACTUATION


class TestTransportIntegration:
    def test_relay_transport_result_with_ingestion(self) -> None:
        from execution.workers.workstation.relay_execution_transport_v1 import RelayTransportResult

        transport = RelayTransportResult(
            status="completed",
            request_id="REQ-W0-FGCU-INGEST-e2e001",
            relay_result=_full_relay_result(),
            ssh_reachable=True,
            inbox_written=True,
            result_received=True,
            elapsed_seconds=12.3,
        )

        proof = build_full_ingestion_proof(transport.relay_result, founder_confirmed=True)
        assert proof.escalation_blocked is False
        assert proof.maturity_level.value >= 1
        assert len(proof.candidates) > 0

    def test_request_builder_integration(self) -> None:
        from execution.environments.windows_desktop_request_builder import (
            build_w0_real_foreground_cu_ingestion_request,
        )

        req = build_w0_real_foreground_cu_ingestion_request()
        assert req.action_type == "ingest_safe_doc_cu"
        assert req.request_id.startswith("REQ-W0-FGCU-INGEST-")
        d = req.to_dict()
        assert d["no_mutation"] is True
        assert d["proof_required"] == "foreground_cu_verification"
