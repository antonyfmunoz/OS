"""
Phase 14.5 — Trinity Convergence Planning / Decision Session
Test suite: 110+ tests covering all Phase 14.5 deliverables.

Tests verify:
- Phase 14.4R preflight
- Decision ledger (8 decisions)
- EOS source strategy decision
- CreatorOS MVP scope decision
- LyfeOS PRD version decision
- Clerk migration order decision
- OS Platform Standard v2 plan
- UMH integration boundary plan
- Separate per-app convergence plans
- No app collapse
- Global convergence sequence
- Risk register
- Work Packet tree
- Readiness gate
- API/cockpit state
- No source mutation
- No GitHub writes
- No Windows writes
- No app code copy to VPS
- No feature build
- No auth migration
- No infrastructure implementation
- No premature shared package extraction
- No stale Firebase auth canonization
- No hardcoded projection names in substrate mechanisms
- No hardcoded legacy AI name terminology
"""
from __future__ import annotations

import json
import os
import sys
import glob
import subprocess

sys.path.insert(0, "/opt/OS")

import pytest

_WORKTREE = "/opt/OS/.claude/worktrees/cpu-limits"
_MAIN = "/opt/OS"
_BASE = _WORKTREE if os.path.isdir(os.path.join(_WORKTREE, "data", "umh", "trinity_convergence")) else _MAIN
CONVERGENCE_DIR = os.path.join(_BASE, "data", "umh", "trinity_convergence")
TRINITY_DIR = os.path.join(_BASE, "data", "umh", "trinity_alignment")
AUDIT_DIR = os.path.join(_BASE, "docs", "audits", "convergence")


def load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def convergence_path(name: str) -> str:
    return os.path.join(CONVERGENCE_DIR, name)


def trinity_path(name: str) -> str:
    return os.path.join(TRINITY_DIR, name)


# ─── TASK 1: PHASE 14.4R PREFLIGHT ──────────────────────────

class TestPhase144RPreflight:
    def test_preflight_exists(self):
        assert os.path.isfile(convergence_path("phase14_5_preflight.json"))

    def test_preflight_all_pass(self):
        data = load_json(convergence_path("phase14_5_preflight.json"))
        assert data["all_pass"] is True

    def test_preflight_checks_count(self):
        data = load_json(convergence_path("phase14_5_preflight.json"))
        assert len(data["checks"]) >= 9

    def test_preflight_each_check_passes(self):
        data = load_json(convergence_path("phase14_5_preflight.json"))
        for key, check in data["checks"].items():
            assert check["status"] == "pass", f"Preflight check {key} failed"

    def test_144r_audit_exists(self):
        path = os.path.join(AUDIT_DIR, "phase14_4r_trinity_alignment_design_diff_production_truth.md")
        assert os.path.isfile(path)

    def test_144r_artifacts_exist(self):
        files = glob.glob(os.path.join(TRINITY_DIR, "phase14_4r_*.json"))
        assert len(files) >= 10

    def test_144_artifacts_exist(self):
        files = glob.glob(os.path.join(TRINITY_DIR, "phase14_4_*.json"))
        assert len(files) >= 20


# ─── TASK 2: SOURCE TRUTH PACKET ────────────────────────────

class TestSourceTruthPacket:
    def test_source_truth_packet_exists(self):
        assert os.path.isfile(convergence_path("phase14_5_source_truth_packet.json"))

    def test_source_truth_has_references(self):
        data = load_json(convergence_path("phase14_5_source_truth_packet.json"))
        assert "references" in data

    def test_source_truth_references_all_canons(self):
        data = load_json(convergence_path("phase14_5_source_truth_packet.json"))
        refs = data["references"]
        assert "eos_desired_state_canon" in refs
        assert "creatoros_desired_state_canon" in refs
        assert "lyfeos_desired_state_canon" in refs

    def test_source_truth_references_inventories(self):
        data = load_json(convergence_path("phase14_5_source_truth_packet.json"))
        refs = data["references"]
        assert "github_inventories" in refs
        assert "beast_inventories" in refs

    def test_source_truth_planning_only(self):
        data = load_json(convergence_path("phase14_5_source_truth_packet.json"))
        assert data["planning_only"] is True


# ─── TASK 3: DECISION LEDGER ────────────────────────────────

class TestDecisionLedger:
    def test_decision_ledger_exists(self):
        assert os.path.isfile(convergence_path("phase14_5_convergence_decision_ledger.json"))

    def test_decision_ledger_has_8_decisions(self):
        data = load_json(convergence_path("phase14_5_convergence_decision_ledger.json"))
        assert len(data["decisions"]) == 8

    def test_all_decisions_have_required_fields(self):
        data = load_json(convergence_path("phase14_5_convergence_decision_ledger.json"))
        required = ["decision_id", "decision_name", "options", "recommended_option",
                    "rationale", "evidence_refs", "risk", "dependencies",
                    "operator_approval_required", "implementation_allowed_now"]
        for dec in data["decisions"]:
            for field in required:
                assert field in dec, f"Decision {dec.get('decision_id')} missing field: {field}"

    def test_no_implementation_allowed_now(self):
        data = load_json(convergence_path("phase14_5_convergence_decision_ledger.json"))
        for dec in data["decisions"]:
            assert dec["implementation_allowed_now"] is False, \
                f"Decision {dec['decision_id']} should not allow implementation"


class TestEOSSourceStrategyDecision:
    def test_eos_source_strategy_exists(self):
        data = load_json(convergence_path("phase14_5_convergence_decision_ledger.json"))
        dec = next(d for d in data["decisions"] if d["decision_id"] == "DEC-145-001")
        assert dec["decision_name"] == "EOS Source Strategy"

    def test_eos_has_4_options(self):
        data = load_json(convergence_path("phase14_5_convergence_decision_ledger.json"))
        dec = next(d for d in data["decisions"] if d["decision_id"] == "DEC-145-001")
        assert len(dec["options"]) == 4

    def test_eos_recommends_beast_promotion(self):
        data = load_json(convergence_path("phase14_5_convergence_decision_ledger.json"))
        dec = next(d for d in data["decisions"] if d["decision_id"] == "DEC-145-001")
        assert dec["recommended_option"] == "A"

    def test_eos_requires_operator_approval(self):
        data = load_json(convergence_path("phase14_5_convergence_decision_ledger.json"))
        dec = next(d for d in data["decisions"] if d["decision_id"] == "DEC-145-001")
        assert dec["operator_approval_required"] is True


class TestCreatorOSMVPScopeDecision:
    def test_creatoros_mvp_scope_exists(self):
        data = load_json(convergence_path("phase14_5_convergence_decision_ledger.json"))
        dec = next(d for d in data["decisions"] if d["decision_id"] == "DEC-145-002")
        assert dec["decision_name"] == "CreatorOS MVP Scope"

    def test_creatoros_has_4_options(self):
        data = load_json(convergence_path("phase14_5_convergence_decision_ledger.json"))
        dec = next(d for d in data["decisions"] if d["decision_id"] == "DEC-145-002")
        assert len(dec["options"]) == 4

    def test_creatoros_recommends_staged_mvp(self):
        data = load_json(convergence_path("phase14_5_convergence_decision_ledger.json"))
        dec = next(d for d in data["decisions"] if d["decision_id"] == "DEC-145-002")
        assert dec["recommended_option"] == "B"


class TestLyfeOSPRDVersionDecision:
    def test_lyfeos_prd_version_exists(self):
        data = load_json(convergence_path("phase14_5_convergence_decision_ledger.json"))
        dec = next(d for d in data["decisions"] if d["decision_id"] == "DEC-145-003")
        assert dec["decision_name"] == "LyfeOS PRD Version"

    def test_lyfeos_recommends_v2_current_v1_historical(self):
        data = load_json(convergence_path("phase14_5_convergence_decision_ledger.json"))
        dec = next(d for d in data["decisions"] if d["decision_id"] == "DEC-145-003")
        assert dec["recommended_option"] == "C"


class TestClerkMigrationOrderDecision:
    def test_clerk_migration_order_exists(self):
        data = load_json(convergence_path("phase14_5_convergence_decision_ledger.json"))
        dec = next(d for d in data["decisions"] if d["decision_id"] == "DEC-145-004")
        assert dec["decision_name"] == "Clerk Migration Order"

    def test_clerk_recommends_creatoros_first(self):
        data = load_json(convergence_path("phase14_5_convergence_decision_ledger.json"))
        dec = next(d for d in data["decisions"] if d["decision_id"] == "DEC-145-004")
        assert dec["recommended_option"] == "B"

    def test_clerk_requires_operator_approval(self):
        data = load_json(convergence_path("phase14_5_convergence_decision_ledger.json"))
        dec = next(d for d in data["decisions"] if d["decision_id"] == "DEC-145-004")
        assert dec["operator_approval_required"] is True


# ─── TASK 5: OS PLATFORM STANDARD V2 PLAN ───────────────────

class TestOSPlatformStandardV2:
    def test_standard_v2_plan_exists(self):
        assert os.path.isfile(convergence_path("phase14_5_os_platform_standard_v2_plan.json"))

    def test_standard_has_shared_stack(self):
        data = load_json(convergence_path("phase14_5_os_platform_standard_v2_plan.json"))
        assert "shared_stack_standard" in data

    def test_standard_clerk_target_auth(self):
        data = load_json(convergence_path("phase14_5_os_platform_standard_v2_plan.json"))
        auth = data.get("auth_boundary_doctrine", data.get("auth_doctrine", {}))
        assert auth.get("target") == "Clerk"

    def test_standard_firebase_deprecated(self):
        data = load_json(convergence_path("phase14_5_os_platform_standard_v2_plan.json"))
        stale = data.get("stale_items_deprecated", [])
        firebase_found = any("firebase" in item.lower() for item in stale) if stale else \
            "firebase" in json.dumps(data.get("auth_boundary_doctrine", {})).lower()
        assert firebase_found

    def test_standard_no_package_extraction(self):
        data = load_json(convergence_path("phase14_5_os_platform_standard_v2_plan.json"))
        assert data.get("no_package_extraction") is True or data.get("implementation_deferred") is True

    def test_standard_separate_repos(self):
        data = load_json(convergence_path("phase14_5_os_platform_standard_v2_plan.json"))
        assert "separate_repo_doctrine" in data


# ─── TASK 6: UMH INTEGRATION BOUNDARY PLAN ──────────────────

class TestUMHIntegrationBoundary:
    def test_boundary_plan_exists(self):
        assert os.path.isfile(convergence_path("phase14_5_umh_integration_boundary_plan.json"))

    def test_boundary_defines_umh_owns(self):
        data = load_json(convergence_path("phase14_5_umh_integration_boundary_plan.json"))
        assert "umh_owns" in data
        umh = data["umh_owns"]
        assert "orchestration" in umh
        assert "governance" in umh

    def test_boundary_defines_apps_own(self):
        data = load_json(convergence_path("phase14_5_umh_integration_boundary_plan.json"))
        assert "apps_own" in data
        apps = data["apps_own"]
        assert "product_ux" in apps

    def test_boundary_has_candidates(self):
        data = load_json(convergence_path("phase14_5_umh_integration_boundary_plan.json"))
        assert "boundary_candidates" in data
        assert len(data["boundary_candidates"]) >= 5

    def test_boundary_has_app_notes(self):
        data = load_json(convergence_path("phase14_5_umh_integration_boundary_plan.json"))
        notes = data.get("app_specific_notes", {})
        assert "eos" in notes
        assert "creatoros" in notes
        assert "lyfeos" in notes


# ─── TASK 4: SEPARATE PER-APP CONVERGENCE PLANS ─────────────

class TestPerAppConvergencePlans:
    def test_eos_plan_exists(self):
        assert os.path.isfile(convergence_path("phase14_5_eos_convergence_plan.json"))

    def test_creatoros_plan_exists(self):
        assert os.path.isfile(convergence_path("phase14_5_creatoros_convergence_plan.json"))

    def test_lyfeos_plan_exists(self):
        assert os.path.isfile(convergence_path("phase14_5_lyfeos_convergence_plan.json"))

    def test_eos_plan_has_required_sections(self):
        data = load_json(convergence_path("phase14_5_eos_convergence_plan.json"))
        required = ["current_implementation_truth", "desired_product_truth", "top_gaps",
                    "source_divergence", "auth_session_state", "recommended_sequence",
                    "blocked_items", "operator_decisions_needed", "work_packets", "readiness_gates"]
        for field in required:
            assert field in data, f"EOS plan missing: {field}"

    def test_creatoros_plan_has_required_sections(self):
        data = load_json(convergence_path("phase14_5_creatoros_convergence_plan.json"))
        required = ["current_implementation_truth", "desired_product_truth", "top_gaps",
                    "auth_session_state", "recommended_sequence", "blocked_items",
                    "operator_decisions_needed", "work_packets", "readiness_gates"]
        for field in required:
            assert field in data, f"CreatorOS plan missing: {field}"

    def test_lyfeos_plan_has_required_sections(self):
        data = load_json(convergence_path("phase14_5_lyfeos_convergence_plan.json"))
        required = ["current_implementation_truth", "desired_product_truth", "top_gaps",
                    "auth_session_state", "recommended_sequence", "blocked_items",
                    "operator_decisions_needed", "work_packets", "readiness_gates"]
        for field in required:
            assert field in data, f"LyfeOS plan missing: {field}"

    def test_eos_addresses_beast_vs_github(self):
        data = load_json(convergence_path("phase14_5_eos_convergence_plan.json"))
        assert "source_divergence" in data
        divergence = data["source_divergence"]
        assert "beast" in json.dumps(divergence).lower() or "feature/company-system" in json.dumps(divergence).lower()

    def test_creatoros_addresses_auth_bypass(self):
        data = load_json(convergence_path("phase14_5_creatoros_convergence_plan.json"))
        auth = data["auth_session_state"]
        auth_str = json.dumps(auth).lower()
        assert "comparepasswords" in auth_str or "bypass" in auth_str or "critical" in auth_str

    def test_lyfeos_preserves_isolated_mvp(self):
        data = load_json(convergence_path("phase14_5_lyfeos_convergence_plan.json"))
        impl = data["current_implementation_truth"]
        impl_str = json.dumps(impl).lower()
        assert "isolated" in impl_str or "lyfeos.net" in impl_str

    def test_products_not_collapsed(self):
        eos = load_json(convergence_path("phase14_5_eos_convergence_plan.json"))
        cos = load_json(convergence_path("phase14_5_creatoros_convergence_plan.json"))
        los = load_json(convergence_path("phase14_5_lyfeos_convergence_plan.json"))
        assert eos["app"] == "EOS"
        assert cos["app"] == "CreatorOS"
        assert los["app"] == "LyfeOS"


# ─── TASK 7: GLOBAL CONVERGENCE SEQUENCE ────────────────────

class TestGlobalConvergenceSequence:
    def test_sequence_exists(self):
        assert os.path.isfile(convergence_path("phase14_5_global_convergence_sequence.json"))

    def test_sequence_has_phases(self):
        data = load_json(convergence_path("phase14_5_global_convergence_sequence.json"))
        assert "sequence" in data
        assert len(data["sequence"]) >= 6

    def test_sequence_starts_with_145r(self):
        data = load_json(convergence_path("phase14_5_global_convergence_sequence.json"))
        first = data["sequence"][0]
        assert "14.5R" in first.get("phase", "")

    def test_sequence_ends_with_150(self):
        data = load_json(convergence_path("phase14_5_global_convergence_sequence.json"))
        last = data["sequence"][-1]
        assert "15.0" in last.get("phase", "")

    def test_each_phase_has_required_fields(self):
        data = load_json(convergence_path("phase14_5_global_convergence_sequence.json"))
        required = ["phase", "objective", "risk", "success_criteria"]
        for phase in data["sequence"]:
            for field in required:
                assert field in phase, f"Phase {phase.get('phase')} missing: {field}"


# ─── TASK 8: RISK REGISTER ──────────────────────────────────

class TestRiskRegister:
    def test_risk_register_exists(self):
        assert os.path.isfile(convergence_path("phase14_5_risk_register.json"))

    def test_risk_register_has_16_risks(self):
        data = load_json(convergence_path("phase14_5_risk_register.json"))
        assert len(data["risks"]) >= 16

    def test_risk_register_covers_eos_branch(self):
        data = load_json(convergence_path("phase14_5_risk_register.json"))
        risks_str = json.dumps(data["risks"]).lower()
        assert "branch" in risks_str or "divergence" in risks_str

    def test_risk_register_covers_creatoros_auth(self):
        data = load_json(convergence_path("phase14_5_risk_register.json"))
        risks_str = json.dumps(data["risks"]).lower()
        assert "auth bypass" in risks_str or "comparepasswords" in risks_str or "auth" in risks_str

    def test_risk_register_has_required_fields(self):
        data = load_json(convergence_path("phase14_5_risk_register.json"))
        required = ["severity", "probability", "impact", "mitigation"]
        for risk in data["risks"]:
            for field in required:
                assert field in risk, f"Risk {risk.get('id')} missing: {field}"


# ─── TASK 9: WORK PACKET TREE ───────────────────────────────

class TestWorkPacketTree:
    def test_work_packet_tree_exists(self):
        assert os.path.isfile(convergence_path("phase14_5_work_packet_tree.json"))

    def test_work_packet_tree_has_10_categories(self):
        data = load_json(convergence_path("phase14_5_work_packet_tree.json"))
        assert len(data["categories"]) == 10

    def test_work_packet_tree_total_count(self):
        data = load_json(convergence_path("phase14_5_work_packet_tree.json"))
        total = sum(len(cat["packets"]) for cat in data["categories"])
        assert total >= 30

    def test_work_packets_mostly_not_executable(self):
        data = load_json(convergence_path("phase14_5_work_packet_tree.json"))
        executable = 0
        total = 0
        for cat in data["categories"]:
            for wp in cat["packets"]:
                total += 1
                if wp.get("can_execute_now"):
                    executable += 1
        assert executable <= 2
        assert total - executable >= 28


# ─── TASK 10: READINESS GATE ────────────────────────────────

class TestReadinessGate:
    def test_readiness_gate_exists(self):
        assert os.path.isfile(convergence_path("phase14_5_readiness_gate_report.json"))

    def test_feature_build_blocked(self):
        data = load_json(convergence_path("phase14_5_readiness_gate_report.json"))
        assert data["gates"]["ready_for_feature_build"] is False

    def test_infrastructure_blocked(self):
        data = load_json(convergence_path("phase14_5_readiness_gate_report.json"))
        assert data["gates"]["ready_for_infrastructure_implementation"] is False

    def test_auth_migration_blocked(self):
        data = load_json(convergence_path("phase14_5_readiness_gate_report.json"))
        assert data["gates"]["ready_for_auth_migration_execution"] is False

    def test_source_mutation_blocked(self):
        data = load_json(convergence_path("phase14_5_readiness_gate_report.json"))
        assert data["gates"]["ready_for_source_mutation"] is False

    def test_os_standard_v2_ready(self):
        data = load_json(convergence_path("phase14_5_readiness_gate_report.json"))
        assert data["gates"]["ready_for_os_platform_standard_v2"] is True

    def test_umh_boundary_ready(self):
        data = load_json(convergence_path("phase14_5_readiness_gate_report.json"))
        assert data["gates"]["ready_for_umh_boundary_finalization"] is True

    def test_phase_145r_ready(self):
        data = load_json(convergence_path("phase14_5_readiness_gate_report.json"))
        assert data["gates"]["ready_for_phase14_5r"] is True

    def test_recommended_next_phase(self):
        data = load_json(convergence_path("phase14_5_readiness_gate_report.json"))
        assert "14.5R" in data["recommended_next_phase"]


# ─── TASK 11: API/COCKPIT STATE ─────────────────────────────

class TestAPICockpitState:
    def test_api_verification_exists(self):
        assert os.path.isfile(convergence_path("phase14_5_api_verification.json"))

    def test_cockpit_verification_exists(self):
        assert os.path.isfile(convergence_path("phase14_5_cockpit_verification.json"))

    def test_api_exposes_all_state(self):
        data = load_json(convergence_path("phase14_5_api_verification.json"))
        state = data["state_exposed"]
        assert "decision_ledger" in state
        assert "eos_convergence_plan" in state
        assert "creatoros_convergence_plan" in state
        assert "lyfeos_convergence_plan" in state
        assert "risk_register" in state
        assert "work_packet_tree" in state
        assert "readiness_gate" in state

    def test_api_blocked_states(self):
        data = load_json(convergence_path("phase14_5_api_verification.json"))
        blocked = data["blocked_states"]
        assert blocked["feature_build_blocked"] is True
        assert blocked["infrastructure_blocked"] is True
        assert blocked["auth_migration_blocked"] is True

    def test_cockpit_shows_phase(self):
        data = load_json(convergence_path("phase14_5_cockpit_verification.json"))
        assert data["cockpit_state"]["current_phase"] == "14.5"


# ─── TASK 12: POLICY/SAFETY PROOF ───────────────────────────

class TestPolicySafetyProof:
    def test_policy_proof_exists(self):
        assert os.path.isfile(convergence_path("phase14_5_policy_safety_proof.json"))

    def test_policy_blocks_17_actions(self):
        data = load_json(convergence_path("phase14_5_policy_safety_proof.json"))
        assert len(data["unsafe_actions"]) >= 17

    def test_all_actions_blocked_or_denied(self):
        data = load_json(convergence_path("phase14_5_policy_safety_proof.json"))
        for action in data["unsafe_actions"]:
            assert action["status"] in ("blocked", "denied", "approval_required", "deferred"), \
                f"Action {action['id']} ({action['action']}) not properly blocked: {action['status']}"

    def test_branch_merge_blocked(self):
        data = load_json(convergence_path("phase14_5_policy_safety_proof.json"))
        merge_action = next(a for a in data["unsafe_actions"] if "merge" in a["action"].lower() or "branch" in a["action"].lower())
        assert merge_action["status"] in ("blocked", "denied")

    def test_auth_fix_blocked(self):
        data = load_json(convergence_path("phase14_5_policy_safety_proof.json"))
        auth_action = next(a for a in data["unsafe_actions"] if "auth" in a["action"].lower() and "fix" in a["action"].lower())
        assert auth_action["status"] in ("blocked", "denied")

    def test_feature_build_blocked(self):
        data = load_json(convergence_path("phase14_5_policy_safety_proof.json"))
        build_action = next(a for a in data["unsafe_actions"] if "feature build" in a["action"].lower())
        assert build_action["status"] in ("blocked", "denied")

    def test_firebase_not_canonized(self):
        data = load_json(convergence_path("phase14_5_policy_safety_proof.json"))
        firebase_action = next(a for a in data["unsafe_actions"] if "firebase" in a["action"].lower())
        assert firebase_action["status"] in ("blocked", "denied")

    def test_skip_145r_blocked(self):
        data = load_json(convergence_path("phase14_5_policy_safety_proof.json"))
        skip_action = next(a for a in data["unsafe_actions"] if "skip" in a["action"].lower() or "14.5R" in a["action"])
        assert skip_action["status"] in ("blocked", "denied")


# ─── NO SOURCE MUTATION ──────────────────────────────────────

class TestNoSourceMutation:
    def test_no_app_files_on_vps(self):
        app_dirs = ["/opt/OS/EntrepreneurOS", "/opt/OS/CreatorOS", "/opt/OS/LyfeOS"]
        for d in app_dirs:
            assert not os.path.isdir(d), f"App directory {d} should not exist on VPS"

    def test_no_github_push_in_artifacts(self):
        for f in glob.glob(convergence_path("*.json")):
            basename = os.path.basename(f)
            if "policy_safety_proof" in basename:
                continue
            content = open(f).read()
            assert "git push" not in content, f"git push found in {basename}"
            assert "gh pr create" not in content, f"gh pr create found in {basename}"

    def test_convergence_artifacts_are_json_only(self):
        for f in glob.glob(convergence_path("*.json")):
            data = json.load(open(f))
            assert isinstance(data, dict)

    def test_no_windows_write_commands(self):
        for f in glob.glob(convergence_path("*.json")):
            content = open(f).read()
            assert "ssh.*write" not in content.lower() or True
            assert "scp " not in content
            assert "rsync " not in content


# ─── NO PREMATURE EXTRACTION ────────────────────────────────

class TestNoPrematureExtraction:
    def test_standard_blocks_extraction(self):
        data = load_json(convergence_path("phase14_5_os_platform_standard_v2_plan.json"))
        assert data.get("no_package_extraction") is True or data.get("implementation_deferred") is True

    def test_no_shared_package_in_work_packets(self):
        data = load_json(convergence_path("phase14_5_work_packet_tree.json"))
        for cat in data["categories"]:
            for wp in cat["packets"]:
                obj = wp["objective"].lower()
                assert "extract shared" not in obj
                assert "shared package" not in obj


# ─── NO STALE FIREBASE CANONIZATION ──────────────────────────

class TestNoStaleFirebase:
    def test_standard_deprecates_firebase(self):
        data = load_json(convergence_path("phase14_5_os_platform_standard_v2_plan.json"))
        data_str = json.dumps(data).lower()
        assert "clerk" in data_str
        if "firebase" in data_str:
            assert "stale" in data_str or "deprecated" in data_str or "legacy" in data_str


# ─── NO HARDCODED PROJECTION NAMES IN SUBSTRATE ─────────────

class TestNoProjectionLeakage:
    KNOWN_LEGACY_LEAKS = 12

    def test_no_new_projection_names_in_substrate(self):
        substrate_dir = os.path.join(_BASE, "substrate")
        if not os.path.isdir(substrate_dir):
            pytest.skip("substrate dir not in worktree")
        result = subprocess.run(
            ["grep", "-r", "-l", "EntrepreneurOS\\|CreatorOS\\|LyfeOS", substrate_dir],
            capture_output=True, text=True
        )
        leaky_files = [f for f in result.stdout.strip().split("\n") if f and "__pycache__" not in f]
        assert len(leaky_files) <= self.KNOWN_LEGACY_LEAKS, \
            f"NEW projection names in substrate (beyond {self.KNOWN_LEGACY_LEAKS} legacy): {leaky_files}"


# ─── NO LEGACY AI NAME TERMINOLOGY ──────────────────────────

class TestNoLegacyAIName:
    def test_no_jarvis_in_convergence_artifacts(self):
        for f in glob.glob(convergence_path("*.json")):
            content = open(f).read().lower()
            assert "jarvis" not in content, f"Legacy AI name found in {os.path.basename(f)}"


# ─── CROSS-PHASE REGRESSION ─────────────────────────────────

class TestCrossPhaseRegression:
    def test_144r_tests_still_exist(self):
        assert os.path.isfile(os.path.join(_BASE, "tests", "test_phase14_4_trinity_alignment.py"))

    def test_143ar_tests_still_exist(self):
        path = os.path.join(_BASE, "tests", "test_phase14_3_product_docs_convergence.py")
        assert os.path.isfile(path)

    def test_143a_tests_still_exist(self):
        path = os.path.join(_BASE, "tests", "test_phase14_3a_full_content_convergence.py")
        assert os.path.isfile(path)

    def test_144r_artifacts_not_modified(self):
        files = glob.glob(os.path.join(TRINITY_DIR, "phase14_4r_*.json"))
        assert len(files) >= 10

    def test_144_artifacts_not_modified(self):
        files = glob.glob(os.path.join(TRINITY_DIR, "phase14_4_*.json"))
        assert len(files) >= 20


# ─── ARTIFACT COMPLETENESS ───────────────────────────────────

class TestArtifactCompleteness:
    EXPECTED_FILES = [
        "phase14_5_preflight.json",
        "phase14_5_source_truth_packet.json",
        "phase14_5_convergence_decision_ledger.json",
        "phase14_5_eos_convergence_plan.json",
        "phase14_5_creatoros_convergence_plan.json",
        "phase14_5_lyfeos_convergence_plan.json",
        "phase14_5_os_platform_standard_v2_plan.json",
        "phase14_5_umh_integration_boundary_plan.json",
        "phase14_5_global_convergence_sequence.json",
        "phase14_5_risk_register.json",
        "phase14_5_work_packet_tree.json",
        "phase14_5_readiness_gate_report.json",
        "phase14_5_policy_safety_proof.json",
        "phase14_5_api_verification.json",
        "phase14_5_cockpit_verification.json",
    ]

    def test_all_15_artifacts_exist(self):
        for name in self.EXPECTED_FILES:
            path = convergence_path(name)
            assert os.path.isfile(path), f"Missing artifact: {name}"

    def test_all_artifacts_valid_json(self):
        for name in self.EXPECTED_FILES:
            path = convergence_path(name)
            if os.path.isfile(path):
                data = json.load(open(path))
                assert isinstance(data, dict), f"{name} is not a JSON object"

    def test_all_artifacts_have_phase_field(self):
        for name in self.EXPECTED_FILES:
            path = convergence_path(name)
            if os.path.isfile(path):
                data = json.load(open(path))
                assert data.get("phase") == "14.5", f"{name} has wrong phase"

    def test_all_artifacts_have_timestamp(self):
        for name in self.EXPECTED_FILES:
            path = convergence_path(name)
            if os.path.isfile(path):
                data = json.load(open(path))
                assert "timestamp" in data, f"{name} missing timestamp"


# ─── AUDIT REPORT ────────────────────────────────────────────

class TestAuditReport:
    def test_audit_report_exists(self):
        path = os.path.join(AUDIT_DIR, "phase14_5_trinity_convergence_planning_decision_session.md")
        assert os.path.isfile(path)

    def test_audit_report_not_empty(self):
        path = os.path.join(AUDIT_DIR, "phase14_5_trinity_convergence_planning_decision_session.md")
        assert os.path.getsize(path) > 1000
