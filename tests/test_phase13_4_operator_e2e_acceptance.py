"""Phase 13.4 — Standard Multi-Runtime Operator E2E Acceptance Tests.

70+ tests covering models, coordinator, scenarios, runtime, safety, API/security.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ═══════════════════════════════════════════════════════════════════════════
# Model tests
# ═══════════════════════════════════════════════════════════════════════════


class TestOperatorAcceptanceRunModel:

    def test_run_serialization(self):
        from substrate.organism.operator_acceptance import create_run
        run = create_run("test input", "text", "standard_multi_runtime", "os-123")
        d = run.to_dict()
        assert d["input_text"] == "test input"
        assert d["acceptance_mode"] == "standard_multi_runtime"
        assert d["status"] == "drafted"
        assert d["run_id"].startswith("oar-")

    def test_run_deserialization(self):
        from substrate.organism.operator_acceptance import create_run, run_from_dict
        run = create_run("test", "text", "standard_multi_runtime", "os-1")
        d = run.to_dict()
        restored = run_from_dict(d)
        assert restored.run_id == run.run_id
        assert restored.input_text == "test"

    def test_run_has_selected_runtime_fields(self):
        from substrate.organism.operator_acceptance import create_run
        run = create_run("test", "text", "standard_multi_runtime", "os-1")
        run.selected_runtime = "claude_code"
        run.selected_device = "vps"
        run.placement_decision_id = "wpd-abc"
        d = run.to_dict()
        assert d["selected_runtime"] == "claude_code"
        assert d["selected_device"] == "vps"
        assert d["placement_decision_id"] == "wpd-abc"

    def test_run_status_transitions(self):
        from substrate.organism.operator_acceptance import AcceptanceRunStatus, create_run
        run = create_run("test", "text", "standard_multi_runtime", "os-1")
        assert run.status == AcceptanceRunStatus.DRAFTED
        run.status = AcceptanceRunStatus.RUNNING
        assert run.status == AcceptanceRunStatus.RUNNING
        run.status = AcceptanceRunStatus.COMPLETED
        assert run.status == AcceptanceRunStatus.COMPLETED

    def test_run_persistence(self):
        from substrate.organism.operator_acceptance import create_run, persist_run, load_runs
        with tempfile.TemporaryDirectory() as td:
            run = create_run("persist test", "text", "standard_multi_runtime", "os-1")
            persist_run(run, td)
            loaded = load_runs(td)
            assert len(loaded) >= 1
            assert loaded[-1].run_id == run.run_id


class TestOperatorAcceptanceArtifactModel:

    def test_artifact_serialization(self):
        from substrate.organism.operator_acceptance import create_artifact
        art = create_artifact("oar-1", "implementation_plan", "Plan", "/path", "summary")
        d = art.to_dict()
        assert d["artifact_type"] == "implementation_plan"
        assert d["artifact_id"].startswith("oaa-")

    def test_artifact_has_runtime_fields(self):
        from substrate.organism.operator_acceptance import create_artifact
        art = create_artifact("oar-1", "runtime_report", "Report", "/path", "summary")
        art.selected_runtime = "shell"
        art.selected_device = "vps"
        d = art.to_dict()
        assert d["selected_runtime"] == "shell"
        assert d["selected_device"] == "vps"

    def test_artifact_persistence(self):
        from substrate.organism.operator_acceptance import create_artifact, persist_artifact, load_artifacts
        with tempfile.TemporaryDirectory() as td:
            art = create_artifact("oar-1", "test", "Test", "/path", "summary")
            persist_artifact(art, td)
            loaded = load_artifacts(td)
            assert len(loaded) >= 1
            assert loaded[-1].artifact_id == art.artifact_id


class TestOperatorAcceptanceModeDecision:

    def test_standard_mode_creation(self):
        from substrate.organism.operator_acceptance_mode import create_standard_mode_decision
        d = create_standard_mode_decision("rr-1", "claude_code", "vps")
        assert d.mode.value == "standard_multi_runtime"
        assert d.selected_runtime == "claude_code"
        assert d.capable_runtime_path_exists is True
        assert d.degraded is False

    def test_deterministic_mode_creation(self):
        from substrate.organism.operator_acceptance_mode import create_deterministic_mode_decision
        d = create_deterministic_mode_decision("rr-1")
        assert d.mode.value == "deterministic_only"
        assert d.degraded is True
        assert d.capable_runtime_path_exists is False

    def test_mode_selection_standard(self):
        from substrate.organism.operator_acceptance_mode import select_acceptance_mode
        d = select_acceptance_mode(
            capable_runtime_exists=True,
            selected_runtime="claude_code",
            selected_device="vps",
            llm_cloud_available=False,
            readiness_report_id="rr-1",
        )
        assert d.mode.value == "standard_multi_runtime"

    def test_mode_selection_blocked(self):
        from substrate.organism.operator_acceptance_mode import select_acceptance_mode
        d = select_acceptance_mode(
            capable_runtime_exists=False,
            selected_runtime="",
            selected_device="",
            llm_cloud_available=False,
            readiness_report_id="rr-1",
        )
        assert d.mode.value == "blocked"

    def test_mode_decision_serialization(self):
        from substrate.organism.operator_acceptance_mode import create_standard_mode_decision, from_dict
        d = create_standard_mode_decision("rr-1", "shell", "vps")
        serialized = d.to_dict()
        restored = from_dict(serialized)
        assert restored.decision_id == d.decision_id
        assert restored.mode.value == "standard_multi_runtime"

    def test_mode_decision_new_fields(self):
        from substrate.organism.operator_acceptance_mode import create_standard_mode_decision
        d = create_standard_mode_decision(
            "rr-1", "claude_code", "vps",
            selected_runtime_reason="primary governed runtime",
            cloud_api_status="exhausted",
        )
        assert d.selected_runtime_reason == "primary governed runtime"
        assert d.cloud_api_status == "exhausted"

    def test_mode_persistence(self):
        from substrate.organism.operator_acceptance_mode import (
            create_standard_mode_decision, persist_mode_decision, load_mode_decisions,
        )
        with tempfile.TemporaryDirectory() as td:
            d = create_standard_mode_decision("rr-1", "shell", "vps")
            persist_mode_decision(d, td)
            loaded = load_mode_decisions(td)
            assert len(loaded) >= 1
            assert loaded[-1].decision_id == d.decision_id


# ═══════════════════════════════════════════════════════════════════════════
# Coordinator tests
# ═══════════════════════════════════════════════════════════════════════════


class TestOperatorLoopCoordinator:

    def _make_coord(self):
        from substrate.organism.operator_loop_coordinator import OperatorLoopCoordinator
        return OperatorLoopCoordinator(repo_root=_REPO_ROOT)

    def test_verify_acceptance_mode(self):
        coord = self._make_coord()
        decision = coord.verify_acceptance_mode()
        assert decision.mode.value == "standard_multi_runtime"
        assert decision.capable_runtime_path_exists is True

    def test_start_run(self):
        coord = self._make_coord()
        run = coord.start_acceptance_run("test input")
        assert run.run_id.startswith("oar-")
        assert run.status.value == "running"
        assert run.selected_runtime != ""

    def test_send_input_to_orchestrator(self):
        coord = self._make_coord()
        run = coord.start_acceptance_run("Build the EOS dashboard")
        result = coord.send_input_to_orchestrator(run)
        assert "intent_type" in result
        assert result["intent_type"] in ("create_work", "general_query")

    def test_work_packet_creation(self):
        coord = self._make_coord()
        run = coord.start_acceptance_run("Build the EOS dashboard")
        wp = coord.load_or_create_work_packet(run, "create_work")
        assert wp["work_packet_created"] is True
        assert "packet_id" in wp

    def test_work_packet_not_required_for_query(self):
        coord = self._make_coord()
        run = coord.start_acceptance_run("What is the status?")
        wp = coord.load_or_create_work_packet(run, "query_status")
        assert "work_packet_created" in wp

    def test_context_diagnostic(self):
        coord = self._make_coord()
        run = coord.start_acceptance_run("test")
        ctx = coord.run_context_diagnostic(run)
        assert "diagnostic_id" in ctx
        assert ctx["diagnostic_id"].startswith("ocd-")

    def test_permission_not_needed_for_build(self):
        coord = self._make_coord()
        run = coord.start_acceptance_run("Build the dashboard")
        perm = coord.create_permission_request_if_needed(run, "create_work")
        assert perm["permission_required"] is False

    def test_permission_needed_for_cross_source(self):
        coord = self._make_coord()
        run = coord.start_acceptance_run("Ask me before linking email to files")
        perm = coord.create_permission_request_if_needed(run, "configure_policy")
        assert perm["permission_required"] is True
        assert perm["blocked_until_confirmed"] is True

    def test_propagation_preview(self):
        coord = self._make_coord()
        run = coord.start_acceptance_run("Build X")
        prop = coord.generate_propagation_preview(run, "create_work")
        assert "plan_id" in prop
        assert prop["safe_actions_only"] is True

    def test_workload_placement(self):
        coord = self._make_coord()
        run = coord.start_acceptance_run("Build X")
        run.work_packet_id = "wp-test"
        placement = coord.generate_workload_placement_decision(run)
        assert "decision_id" in placement
        assert "selected_device" in placement

    def test_runtime_handoff_preview(self):
        coord = self._make_coord()
        run = coord.start_acceptance_run("Build X")
        run.selected_runtime = "claude_code"
        run.selected_device = "vps"
        handoff = coord.generate_runtime_handoff_preview(run)
        assert handoff["sandbox_required"] is True
        assert handoff["approval_required"] is True
        assert handoff["selected_runtime"] == "claude_code"

    def test_operator_approval(self):
        coord = self._make_coord()
        run = coord.start_acceptance_run("Build X")
        approval = coord.require_operator_approval(run)
        assert approval["approval_required"] is True
        assert run.status.value == "waiting_for_approval"

    def test_no_production_mutation_verification(self):
        coord = self._make_coord()
        run = coord.start_acceptance_run("Build X")
        safety = coord.verify_no_production_mutation(run)
        assert safety["safe"] is True
        assert safety["production_mutation_occurred"] is False

    def test_complete_run_success(self):
        coord = self._make_coord()
        run = coord.start_acceptance_run("test")
        coord.complete_run(run, success=True)
        assert run.status.value == "completed"
        assert run.completed_at != ""

    def test_complete_run_failure(self):
        coord = self._make_coord()
        run = coord.start_acceptance_run("test")
        coord.complete_run(run, success=False, failure_reason="test failure")
        assert run.status.value == "failed"
        assert run.failure_reason == "test failure"

    def test_overview(self):
        coord = self._make_coord()
        overview = coord.get_overview()
        assert "total_runs" in overview
        assert "total_artifacts" in overview


# ═══════════════════════════════════════════════════════════════════════════
# Scenario tests
# ═══════════════════════════════════════════════════════════════════════════


class TestScenarios:

    def test_scenario_a_definition(self):
        from substrate.organism.operator_acceptance_scenarios import SCENARIO_A
        assert SCENARIO_A.scenario_id == "oas-a"
        assert SCENARIO_A.requires_runtime is True
        assert SCENARIO_A.expected_production_mutation is False

    def test_scenario_b_definition(self):
        from substrate.organism.operator_acceptance_scenarios import SCENARIO_B
        assert SCENARIO_B.scenario_id == "oas-b"
        assert SCENARIO_B.requires_runtime is False

    def test_scenario_c_definition(self):
        from substrate.organism.operator_acceptance_scenarios import SCENARIO_C
        assert SCENARIO_C.scenario_id == "oas-c"
        assert SCENARIO_C.requires_reconciliation is True

    def test_scenario_d_definition(self):
        from substrate.organism.operator_acceptance_scenarios import SCENARIO_D
        assert SCENARIO_D.scenario_id == "oas-d"
        assert SCENARIO_D.requires_permission is True

    def test_get_all_scenarios(self):
        from substrate.organism.operator_acceptance_scenarios import get_all_scenarios
        scenarios = get_all_scenarios()
        assert len(scenarios) == 4

    def test_get_scenario_by_id(self):
        from substrate.organism.operator_acceptance_scenarios import get_scenario
        s = get_scenario("oas-a")
        assert s is not None
        assert s.name == "Primary EOS Dashboard Build Intent"

    def test_get_missing_scenario(self):
        from substrate.organism.operator_acceptance_scenarios import get_scenario
        assert get_scenario("oas-z") is None

    def test_export_scenarios_json(self):
        from substrate.organism.operator_acceptance_scenarios import export_scenarios_json
        j = json.loads(export_scenarios_json())
        assert j["count"] == 4

    def test_scenario_a_e2e(self):
        from substrate.organism.operator_loop_coordinator import OperatorLoopCoordinator
        coord = OperatorLoopCoordinator(repo_root=_REPO_ROOT)
        from substrate.organism.operator_acceptance_scenarios import SCENARIO_A
        result = coord.run_scenario_e2e(SCENARIO_A.input_text)
        assert result["completed"] is True
        assert result["run"]["production_mutation_occurred"] is False
        assert result["run"]["external_write_occurred"] is False
        assert result["run"]["selected_runtime"] != ""

    def test_scenario_b_e2e(self):
        from substrate.organism.operator_loop_coordinator import OperatorLoopCoordinator
        coord = OperatorLoopCoordinator(repo_root=_REPO_ROOT)
        from substrate.organism.operator_acceptance_scenarios import SCENARIO_B
        result = coord.run_scenario_e2e(SCENARIO_B.input_text, skip_runtime=True)
        assert result["completed"] is True
        assert result["run"]["production_mutation_occurred"] is False

    def test_scenario_c_e2e(self):
        from substrate.organism.operator_loop_coordinator import OperatorLoopCoordinator
        coord = OperatorLoopCoordinator(repo_root=_REPO_ROOT)
        from substrate.organism.operator_acceptance_scenarios import SCENARIO_C
        result = coord.run_scenario_e2e(SCENARIO_C.input_text, skip_runtime=True)
        assert result["completed"] is True

    def test_scenario_d_e2e(self):
        from substrate.organism.operator_loop_coordinator import OperatorLoopCoordinator
        coord = OperatorLoopCoordinator(repo_root=_REPO_ROOT)
        from substrate.organism.operator_acceptance_scenarios import SCENARIO_D
        result = coord.run_scenario_e2e(SCENARIO_D.input_text, skip_runtime=True)
        assert result["completed"] is True
        perm_steps = [s for s in result["steps"] if s["step"] == "permission"]
        assert len(perm_steps) > 0
        assert perm_steps[0]["result"]["permission_required"] is True


# ═══════════════════════════════════════════════════════════════════════════
# Runtime tests
# ═══════════════════════════════════════════════════════════════════════════


class TestRuntimeExecution:

    def test_shell_adapter_available(self):
        from substrate.organism.shell_runtime_adapter import ShellRuntimeAdapter
        adapter = ShellRuntimeAdapter()
        assert adapter.is_available() is True

    def test_runtime_manager_init(self):
        from substrate.organism.runtime_manager import RuntimeManager
        mgr = RuntimeManager()
        adapters = mgr.get_adapters()
        assert "shell" in adapters

    def test_runtime_policy_blocks_main(self):
        from substrate.organism.runtime_manager import RuntimeManager
        mgr = RuntimeManager()
        main_root = os.environ.get("UMH_ROOT", "/opt/OS")
        policy = mgr.validate_runtime_policy(
            runtime_type="shell",
            command="echo test",
            risk_class="low",
            cwd=main_root,
            work_packet_id="wp-1",
            operator_session_id="os-1",
        )
        assert policy["allowed"] is False

    def test_runtime_policy_blocks_medium_risk(self):
        from substrate.organism.runtime_manager import RuntimeManager
        mgr = RuntimeManager()
        policy = mgr.validate_runtime_policy(
            runtime_type="shell",
            command="echo test",
            risk_class="medium",
            cwd="/tmp/test",
            work_packet_id="wp-1",
            operator_session_id="os-1",
        )
        assert policy["allowed"] is False
        assert policy.get("approval_required") is True

    def test_runtime_session_creation(self):
        from substrate.organism.runtime_manager import RuntimeManager
        mgr = RuntimeManager()
        session, policy = mgr.create_runtime_session(
            runtime_type="shell",
            command="echo acceptance",
            work_packet_id="wp-test",
            operator_session_id="os-test",
            risk_class="low",
            cwd=".",
        )
        assert session.session_id.startswith("rs-")

    def test_runtime_events_streaming(self):
        from substrate.organism.runtime_manager import RuntimeManager
        mgr = RuntimeManager()
        session, _ = mgr.create_runtime_session(
            runtime_type="shell",
            command="echo stream_test",
            work_packet_id="wp-test",
            operator_session_id="os-test",
            risk_class="low",
        )
        events = mgr.stream_events(session.session_id)
        assert isinstance(events, list)


# ═══════════════════════════════════════════════════════════════════════════
# Safety tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSafetyPolicy:

    def _check(self, text: str) -> bool:
        from substrate.organism.operator_loop_coordinator import OperatorLoopCoordinator
        coord = OperatorLoopCoordinator(repo_root=_REPO_ROOT)
        return coord.check_safety_policy(text)["blocked"]

    def test_direct_main_blocked(self):
        assert self._check("Run this directly on main.") is True

    def test_git_push_blocked(self):
        assert self._check("Push the changes to GitHub.") is True

    def test_auto_merge_blocked(self):
        assert self._check("Merge the PR automatically.") is True

    def test_recursive_home_blocked(self):
        assert self._check("Read all files in my home directory recursively.") is True

    def test_cross_source_without_permission_blocked(self):
        assert self._check("Link all email receipts to apps without asking.") is True

    def test_canonize_without_approval_blocked(self):
        assert self._check("Canonize this without approval.") is True

    def test_medium_risk_blocked(self):
        assert self._check("Run a medium-risk deployment command.") is True

    def test_heavy_browser_on_vps_blocked(self):
        assert self._check("Route heavy browser automation to the VPS by default.") is True

    def test_safe_input_not_blocked(self):
        assert self._check("What is the current roadmap status?") is False

    def test_safe_build_not_blocked(self):
        assert self._check("Build a new dashboard component") is False


# ═══════════════════════════════════════════════════════════════════════════
# API / security tests
# ═══════════════════════════════════════════════════════════════════════════


class TestAPIRoutes:

    def test_bridge_operator_acceptance(self):
        from substrate.organism.operator_loop_coordinator import OperatorLoopCoordinator
        coord = OperatorLoopCoordinator(repo_root=_REPO_ROOT)
        overview = coord.get_overview()
        assert "total_runs" in overview

    def test_bridge_scenarios(self):
        from substrate.organism.operator_acceptance_scenarios import get_all_scenarios
        scenarios = get_all_scenarios()
        assert len(scenarios) == 4
        for s in scenarios:
            d = s.to_dict()
            assert "scenario_id" in d

    def test_bridge_readiness(self):
        from substrate.organism.operator_readiness_gate import assess_readiness
        report = assess_readiness(repo_root=_REPO_ROOT)
        d = report.to_dict()
        assert "ready" in d
        assert "capable_runtimes" in d

    def test_invalid_run_id_returns_none(self):
        from substrate.organism.operator_acceptance import get_run
        assert get_run("oar-nonexistent") is None

    def test_no_path_traversal_in_run_id(self):
        from substrate.organism.operator_acceptance import get_run
        result = get_run("../../etc/passwd")
        assert result is None

    def test_no_sensitive_log_leak(self):
        from substrate.organism.operator_loop_coordinator import OperatorLoopCoordinator
        coord = OperatorLoopCoordinator(repo_root=_REPO_ROOT)
        run = coord.start_acceptance_run("test with secret API_KEY=sk-12345")
        summary = coord.generate_operator_summary(run)
        assert "sk-12345" not in json.dumps(summary.get("metadata", {}))


# ═══════════════════════════════════════════════════════════════════════════
# Readiness gate tests
# ═══════════════════════════════════════════════════════════════════════════


class TestReadinessGate:

    def test_readiness_returns_report(self):
        from substrate.organism.operator_readiness_gate import assess_readiness
        report = assess_readiness(repo_root=_REPO_ROOT)
        assert hasattr(report, "ready")
        assert hasattr(report, "standard_ready")

    def test_readiness_detects_capable_runtimes(self):
        from substrate.organism.operator_readiness_gate import assess_readiness
        report = assess_readiness(repo_root=_REPO_ROOT)
        assert len(report.capable_runtimes) > 0

    def test_readiness_standard_ready(self):
        from substrate.organism.operator_readiness_gate import assess_readiness
        report = assess_readiness(repo_root=_REPO_ROOT)
        assert report.standard_ready is True


# ═══════════════════════════════════════════════════════════════════════════
# Proof file existence tests
# ═══════════════════════════════════════════════════════════════════════════


class TestProofFiles:

    _proof_dir = os.path.join(_REPO_ROOT, "data", "umh", "operator_acceptance")

    def test_preflight_proof_exists(self):
        assert os.path.isfile(os.path.join(self._proof_dir, "phase13_4_preflight.json"))

    def test_primary_e2e_proof_exists(self):
        assert os.path.isfile(os.path.join(self._proof_dir, "phase13_4_primary_e2e_proof.json"))

    def test_roadmap_proof_exists(self):
        assert os.path.isfile(os.path.join(self._proof_dir, "phase13_4_roadmap_status_proof.json"))

    def test_reconciliation_proof_exists(self):
        assert os.path.isfile(os.path.join(self._proof_dir, "phase13_4_reconciliation_acceptance_proof.json"))

    def test_cross_source_proof_exists(self):
        assert os.path.isfile(os.path.join(self._proof_dir, "phase13_4_permissioned_cross_source_proof.json"))

    def test_voice_fallback_proof_exists(self):
        assert os.path.isfile(os.path.join(self._proof_dir, "phase13_4_voice_or_fallback_proof.json"))

    def test_runtime_stream_proof_exists(self):
        assert os.path.isfile(os.path.join(self._proof_dir, "phase13_4_runtime_stream_stop_proof.json"))

    def test_safety_proof_exists(self):
        assert os.path.isfile(os.path.join(self._proof_dir, "phase13_4_policy_safety_proof.json"))

    def test_api_verification_exists(self):
        assert os.path.isfile(os.path.join(self._proof_dir, "phase13_4_api_verification.json"))

    def test_cockpit_verification_exists(self):
        assert os.path.isfile(os.path.join(self._proof_dir, "phase13_4_cockpit_verification.json"))

    def test_artifact_report_exists(self):
        assert os.path.isfile(os.path.join(self._proof_dir, "artifacts", "eos_dashboard_implementation_plan.md"))

    def test_coordinator_proof_exists(self):
        assert os.path.isfile(os.path.join(self._proof_dir, "phase13_4_coordinator_proof.json"))

    def test_mode_decision_proof_exists(self):
        assert os.path.isfile(os.path.join(self._proof_dir, "phase13_4_mode_decision_proof.json"))

    def test_scenario_definitions_exist(self):
        assert os.path.isfile(os.path.join(self._proof_dir, "phase13_4_scenario_definitions.json"))


# ═══════════════════════════════════════════════════════════════════════════
# No-execution invariant tests
# ═══════════════════════════════════════════════════════════════════════════


class TestNoExecutionInvariants:

    def test_primary_proof_no_mutation(self):
        path = os.path.join(_REPO_ROOT, "data", "umh", "operator_acceptance", "phase13_4_primary_e2e_proof.json")
        if not os.path.isfile(path):
            pytest.skip("proof file not generated yet")
        with open(path) as f:
            data = json.load(f)
        assert data["run"]["production_mutation_occurred"] is False
        assert data["run"]["external_write_occurred"] is False

    def test_safety_proof_all_blocked(self):
        path = os.path.join(_REPO_ROOT, "data", "umh", "operator_acceptance", "phase13_4_policy_safety_proof.json")
        if not os.path.isfile(path):
            pytest.skip("proof file not generated yet")
        with open(path) as f:
            data = json.load(f)
        assert data["all_blocked"] is True

    def test_no_fake_data_in_proofs(self):
        proof_dir = os.path.join(_REPO_ROOT, "data", "umh", "operator_acceptance")
        if not os.path.isdir(proof_dir):
            pytest.skip("proof dir not populated yet")
        for fname in os.listdir(proof_dir):
            if not fname.startswith("phase13_4_"):
                continue
            if not fname.endswith(".json"):
                continue
            path = os.path.join(proof_dir, fname)
            with open(path) as f:
                data = json.load(f)
            content = json.dumps(data)
            has_fake_marker = '"fake":' in content.lower() or '"is_fake":' in content.lower()
            assert not has_fake_marker, f"fake data marker found in {fname}"
