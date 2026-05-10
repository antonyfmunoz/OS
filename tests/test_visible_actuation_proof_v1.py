"""Tests for Phase 96.8AQ — Visible Actuation Proof.

Verifies:
  1. Dry-run cannot escalate maturity (always L0)
  2. Missing HWND blocks escalation (ceiling caps)
  3. Missing screenshot blocks escalation
  4. Founder denial blocks escalation
  5. Full evidence escalates to L1+ (VISIBLE_ACTUATION)
  6. Evidence extraction from relay results
  7. Proof persistence writes valid JSON
  8. Founder confirmation artifact persistence
  9. Missing evidence list correctness
  10. Escalation reason propagation
"""

import json
import sys
from pathlib import Path

import pytest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from core.actuation.actuator_maturity_v1 import ActuatorMaturityLevel
from core.workstation.visible_actuation_proof_v1 import (
    FounderConfirmationArtifact,
    VisibleActuationEvidence,
    VisibleActuationProof,
    classify_visible_actuation,
    extract_evidence_from_relay_result,
    persist_founder_confirmation,
    persist_visible_actuation_proof,
)


def _full_evidence(**overrides: object) -> VisibleActuationEvidence:
    defaults = {
        "chrome_pid": 12345,
        "window_handle": 0x001A02BC,
        "window_title": "Google - Google Chrome",
        "foreground_focused": True,
        "screenshot_path": "/tmp/screenshot_001.png",
        "screenshot_hash": "abc123def456",
        "desktop_unlocked": True,
        "desktop_session_active": True,
        "monitor_detected": True,
        "founder_confirmed": True,
        "relay_node_id": "WRN-test-001",
        "relay_machine": "DESKTOP-TEST",
        "is_dry_run": False,
        "trace_id": "TR-001",
        "request_id": "REQ-001",
    }
    defaults.update(overrides)
    return VisibleActuationEvidence(**defaults)


class TestDryRunBlocked:
    def test_dry_run_always_l0(self) -> None:
        evidence = _full_evidence(is_dry_run=True)
        proof = classify_visible_actuation(evidence)
        assert proof.maturity_level == ActuatorMaturityLevel.L0_SIMULATED
        assert proof.escalation_blocked is True
        assert proof.escalation_reason == "dry_run_cannot_escalate"

    def test_dry_run_ceiling_l0(self) -> None:
        evidence = _full_evidence(is_dry_run=True)
        proof = classify_visible_actuation(evidence)
        assert proof.maturity_ceiling == ActuatorMaturityLevel.L0_SIMULATED

    def test_dry_run_with_all_evidence_still_l0(self) -> None:
        evidence = _full_evidence(is_dry_run=True)
        assert evidence.has_chrome_pid
        assert evidence.has_window_handle
        assert evidence.has_screenshot
        assert evidence.has_foreground_focus
        assert evidence.founder_confirmed
        proof = classify_visible_actuation(evidence)
        assert proof.maturity_level == ActuatorMaturityLevel.L0_SIMULATED


class TestMissingEvidence:
    def test_no_chrome_pid_blocked(self) -> None:
        evidence = _full_evidence(chrome_pid=0)
        proof = classify_visible_actuation(evidence)
        assert proof.escalation_blocked is True
        assert "chrome_pid" in proof.escalation_reason

    def test_no_window_handle_blocked(self) -> None:
        evidence = _full_evidence(window_handle=0)
        proof = classify_visible_actuation(evidence)
        assert proof.escalation_blocked is True
        assert "window_handle" in proof.escalation_reason

    def test_no_foreground_blocked(self) -> None:
        evidence = _full_evidence(foreground_focused=False)
        proof = classify_visible_actuation(evidence)
        assert proof.escalation_blocked is True
        assert "foreground_focus" in proof.escalation_reason

    def test_no_screenshot_blocked(self) -> None:
        evidence = _full_evidence(screenshot_path="", screenshot_hash="")
        proof = classify_visible_actuation(evidence)
        assert proof.escalation_blocked is True
        assert "screenshot" in proof.escalation_reason

    def test_no_founder_confirmation_blocked(self) -> None:
        evidence = _full_evidence(founder_confirmed=False)
        proof = classify_visible_actuation(evidence)
        assert proof.escalation_blocked is True
        assert "founder_confirmation" in proof.escalation_reason

    def test_screenshot_path_only_no_hash(self) -> None:
        evidence = _full_evidence(screenshot_hash="")
        assert evidence.has_screenshot is False
        proof = classify_visible_actuation(evidence)
        assert proof.escalation_blocked is True

    def test_screenshot_hash_only_no_path(self) -> None:
        evidence = _full_evidence(screenshot_path="")
        assert evidence.has_screenshot is False


class TestMissingEvidenceList:
    def test_full_evidence_nothing_missing(self) -> None:
        evidence = _full_evidence()
        assert evidence.missing_evidence == []

    def test_all_missing(self) -> None:
        evidence = VisibleActuationEvidence()
        missing = evidence.missing_evidence
        assert "chrome_pid" in missing
        assert "window_handle" in missing
        assert "foreground_focus" in missing
        assert "screenshot" in missing
        assert "founder_confirmation" in missing
        assert len(missing) == 5

    def test_partial_missing(self) -> None:
        evidence = _full_evidence(chrome_pid=0, founder_confirmed=False)
        missing = evidence.missing_evidence
        assert "chrome_pid" in missing
        assert "founder_confirmation" in missing
        assert "window_handle" not in missing
        assert len(missing) == 2


class TestMaturityCeilings:
    def test_no_hwnd_ceiling_l1(self) -> None:
        evidence = _full_evidence(window_handle=0)
        proof = classify_visible_actuation(evidence)
        assert proof.maturity_ceiling == ActuatorMaturityLevel.L1_PROCESS_STARTED

    def test_no_screenshot_ceiling_l4(self) -> None:
        evidence = _full_evidence(screenshot_path="", screenshot_hash="")
        proof = classify_visible_actuation(evidence)
        assert proof.maturity_ceiling == ActuatorMaturityLevel.L4_NAVIGATION_OBSERVED

    def test_no_founder_ceiling_l5(self) -> None:
        evidence = _full_evidence(founder_confirmed=False)
        proof = classify_visible_actuation(evidence)
        assert proof.maturity_ceiling == ActuatorMaturityLevel.L5_SCREENSHOT_VERIFIED

    def test_full_evidence_ceiling_l7(self) -> None:
        evidence = _full_evidence()
        proof = classify_visible_actuation(evidence)
        assert proof.maturity_ceiling == ActuatorMaturityLevel.L7_REPLAYABLE_ACTUATION


class TestFullEvidenceEscalation:
    def test_full_evidence_reaches_l1_or_above(self) -> None:
        evidence = _full_evidence()
        proof = classify_visible_actuation(evidence)
        assert proof.maturity_level >= ActuatorMaturityLevel.L1_PROCESS_STARTED
        assert proof.escalation_blocked is False
        assert proof.escalation_reason == ""

    def test_full_evidence_not_l0(self) -> None:
        evidence = _full_evidence()
        proof = classify_visible_actuation(evidence)
        assert proof.maturity_level != ActuatorMaturityLevel.L0_SIMULATED

    def test_full_evidence_label_not_simulated(self) -> None:
        evidence = _full_evidence()
        proof = classify_visible_actuation(evidence)
        assert proof.maturity_label != "simulated"

    def test_full_evidence_proof_type(self) -> None:
        evidence = _full_evidence()
        proof = classify_visible_actuation(evidence)
        assert proof.proof_type == "visible_actuation"


class TestEvidenceExtraction:
    def test_extract_from_full_relay_result(self) -> None:
        relay_result = {
            "observed_desktop_state": {
                "chrome_pid": 9876,
                "window_handle": 0x00AB01CD,
                "window_title": "New Tab - Google Chrome",
                "focused": True,
                "screenshot_path": "/tmp/ss.png",
                "screenshot_hash": "hash123",
                "desktop_unlocked": True,
                "desktop_session_active": True,
                "monitor_detected": True,
            },
            "node_id": "WRN-relay-001",
            "machine_name": "DESKTOP-RELAY",
            "dry_run": False,
            "trace_id": "TR-ext-001",
            "request_id": "REQ-ext-001",
        }
        evidence = extract_evidence_from_relay_result(relay_result, founder_confirmed=True)
        assert evidence.chrome_pid == 9876
        assert evidence.window_handle == 0x00AB01CD
        assert evidence.foreground_focused is True
        assert evidence.screenshot_path == "/tmp/ss.png"
        assert evidence.founder_confirmed is True
        assert evidence.relay_node_id == "WRN-relay-001"
        assert evidence.is_dry_run is False

    def test_dry_run_from_top_level(self) -> None:
        relay_result = {
            "observed_desktop_state": {
                "chrome_pid": 100,
                "window_handle": 200,
            },
            "dry_run": True,
        }
        evidence = extract_evidence_from_relay_result(relay_result)
        assert evidence.is_dry_run is True

    def test_fallback_pid_from_process_id(self) -> None:
        relay_result = {
            "observed_desktop_state": {},
            "process_id": 5555,
        }
        evidence = extract_evidence_from_relay_result(relay_result)
        assert evidence.chrome_pid == 5555

    def test_fallback_screenshot_from_top_level(self) -> None:
        relay_result = {
            "observed_desktop_state": {},
            "screenshot_path": "/fallback/ss.png",
            "screenshot_hash": "fb_hash",
        }
        evidence = extract_evidence_from_relay_result(relay_result)
        assert evidence.screenshot_path == "/fallback/ss.png"
        assert evidence.screenshot_hash == "fb_hash"

    def test_empty_relay_result(self) -> None:
        evidence = extract_evidence_from_relay_result({})
        assert evidence.chrome_pid == 0
        assert evidence.window_handle == 0
        assert evidence.is_dry_run is False
        assert evidence.founder_confirmed is False

    def test_is_foreground_fallback(self) -> None:
        relay_result = {
            "observed_desktop_state": {
                "is_foreground": True,
                "window_handle": 100,
            },
        }
        evidence = extract_evidence_from_relay_result(relay_result)
        assert evidence.foreground_focused is True


class TestProofPersistence:
    def test_persist_creates_file(self, tmp_path: Path) -> None:
        evidence = _full_evidence()
        proof = classify_visible_actuation(evidence)
        path = persist_visible_actuation_proof(proof, base_dir=tmp_path)
        assert path.exists()
        assert path.name.startswith("VAP-")
        assert path.suffix == ".json"

    def test_persisted_proof_valid_json(self, tmp_path: Path) -> None:
        evidence = _full_evidence()
        proof = classify_visible_actuation(evidence)
        path = persist_visible_actuation_proof(proof, base_dir=tmp_path)
        data = json.loads(path.read_text())
        assert data["proof_type"] == "visible_actuation"
        assert "evidence" in data
        assert "maturity_level" in data
        assert "escalation_blocked" in data

    def test_persisted_proof_matches_object(self, tmp_path: Path) -> None:
        evidence = _full_evidence()
        proof = classify_visible_actuation(evidence)
        path = persist_visible_actuation_proof(proof, base_dir=tmp_path)
        data = json.loads(path.read_text())
        assert data["maturity_level"] == proof.maturity_level.value
        assert data["escalation_blocked"] == proof.escalation_blocked

    def test_proof_dir_created(self, tmp_path: Path) -> None:
        evidence = _full_evidence()
        proof = classify_visible_actuation(evidence)
        path = persist_visible_actuation_proof(proof, base_dir=tmp_path)
        assert path.parent.exists()
        assert "actuation_proofs" in str(path.parent)


class TestFounderConfirmation:
    def test_confirmation_artifact_creation(self) -> None:
        artifact = FounderConfirmationArtifact(
            confirmed=True,
            trace_id="TR-001",
            request_id="REQ-001",
            founder_response="YES",
        )
        assert artifact.confirmed is True
        assert artifact.confirmation_id.startswith("FC-")
        assert len(artifact.confirmation_id) == 11

    def test_denial_artifact(self) -> None:
        artifact = FounderConfirmationArtifact(
            confirmed=False,
            founder_response="NO",
        )
        assert artifact.confirmed is False

    def test_persist_confirmation(self, tmp_path: Path) -> None:
        artifact = FounderConfirmationArtifact(
            confirmed=True,
            trace_id="TR-persist",
            request_id="REQ-persist",
            channel="discord",
            founder_response="YES",
        )
        path = persist_founder_confirmation(artifact, base_dir=tmp_path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["confirmed"] is True
        assert data["channel"] == "discord"
        assert data["founder_response"] == "YES"

    def test_confirmation_to_dict(self) -> None:
        artifact = FounderConfirmationArtifact(
            confirmed=True,
            trace_id="TR-dict",
        )
        d = artifact.to_dict()
        assert d["confirmed"] is True
        assert "confirmation_id" in d
        assert "timestamp" in d


class TestProofSerialization:
    def test_proof_to_dict(self) -> None:
        evidence = _full_evidence()
        proof = classify_visible_actuation(evidence)
        d = proof.to_dict()
        assert d["proof_type"] == "visible_actuation"
        assert "evidence" in d
        assert isinstance(d["evidence"], dict)
        assert d["evidence"]["chrome_pid"] == 12345

    def test_proof_json_serializable(self) -> None:
        evidence = _full_evidence()
        proof = classify_visible_actuation(evidence)
        serialized = json.dumps(proof.to_dict(), default=str)
        assert len(serialized) > 0
        parsed = json.loads(serialized)
        assert parsed["proof_type"] == "visible_actuation"

    def test_evidence_to_dict_includes_computed(self) -> None:
        evidence = _full_evidence()
        d = evidence.to_dict()
        assert "has_chrome_pid" in d
        assert "has_window_handle" in d
        assert "has_screenshot" in d
        assert "has_foreground_focus" in d
        assert "missing_evidence" in d
        assert d["has_chrome_pid"] is True
        assert d["missing_evidence"] == []

    def test_proof_id_generated(self) -> None:
        proof = VisibleActuationProof()
        assert proof.proof_id.startswith("VAP-")
        assert len(proof.proof_id) == 12

    def test_maturity_label_auto_populated(self) -> None:
        proof = VisibleActuationProof()
        assert proof.maturity_label == "simulated"

    def test_timestamp_auto_populated(self) -> None:
        proof = VisibleActuationProof()
        assert proof.timestamp != ""
        assert "T" in proof.timestamp


class TestEndToEndClassification:
    def test_full_pipeline_extract_classify_persist(self, tmp_path: Path) -> None:
        relay_result = {
            "observed_desktop_state": {
                "chrome_pid": 7777,
                "window_handle": 0x00FF00AA,
                "window_title": "Google - Google Chrome",
                "focused": True,
                "screenshot_path": "/tmp/e2e_ss.png",
                "screenshot_hash": "e2e_hash_001",
                "desktop_unlocked": True,
                "desktop_session_active": True,
                "monitor_detected": True,
            },
            "node_id": "WRN-e2e-001",
            "machine_name": "DESKTOP-E2E",
            "dry_run": False,
            "trace_id": "TR-e2e",
            "request_id": "REQ-e2e",
        }
        evidence = extract_evidence_from_relay_result(relay_result, founder_confirmed=True)
        proof = classify_visible_actuation(evidence)
        assert proof.maturity_level >= ActuatorMaturityLevel.L1_PROCESS_STARTED
        assert proof.escalation_blocked is False

        path = persist_visible_actuation_proof(proof, base_dir=tmp_path)
        data = json.loads(path.read_text())
        assert data["escalation_blocked"] is False
        assert data["maturity_level"] >= ActuatorMaturityLevel.L1_PROCESS_STARTED

    def test_dry_run_pipeline_stays_l0(self, tmp_path: Path) -> None:
        relay_result = {
            "observed_desktop_state": {
                "chrome_pid": 8888,
                "window_handle": 0x00AABB,
                "focused": True,
                "screenshot_path": "/tmp/dry.png",
                "screenshot_hash": "dry_hash",
            },
            "dry_run": True,
            "trace_id": "TR-dry",
        }
        evidence = extract_evidence_from_relay_result(relay_result, founder_confirmed=True)
        proof = classify_visible_actuation(evidence)
        assert proof.maturity_level == ActuatorMaturityLevel.L0_SIMULATED
        path = persist_visible_actuation_proof(proof, base_dir=tmp_path)
        data = json.loads(path.read_text())
        assert data["maturity_level"] == 0
        assert data["escalation_blocked"] is True
