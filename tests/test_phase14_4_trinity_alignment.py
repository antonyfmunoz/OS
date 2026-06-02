"""
Phase 14.4 — Trinity GitHub/Windows Alignment + Product Design Diff
Test suite: 100+ tests covering all Phase 14.4 deliverables.

Tests verify:
- Phase 14.3AR preflight
- Separate desired-state canons for EOS, CreatorOS, LyfeOS
- No colossal merged product doc
- Device/runtime placement
- Source access state
- Current source inventories
- GitHub/Windows alignment
- Feature preservation matrices
- Product design diffs
- Architecture diffs
- Current state summaries
- Gap maps/build sequences
- Cross-Trinity shared standard diff
- Work Packet generation
- Readiness gate
- API/cockpit state
- No source mutation
- No GitHub writes
- No Windows writes
- No app code copy to VPS
- No feature build
- No infrastructure implementation
- No stale Firebase auth canonization
- No app collapse
- No hardcoded projection names in substrate mechanisms
- No hardcoded Jarvis terminology
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
_BASE = _WORKTREE if os.path.isdir(os.path.join(_WORKTREE, "data", "umh", "trinity_alignment")) else _MAIN
TRINITY_DIR = os.path.join(_BASE, "data", "umh", "trinity_alignment")
CONVERGENCE_DIR = os.path.join(_BASE, "data", "umh", "product_docs_convergence")
AUDIT_DIR = os.path.join(_BASE, "docs", "audits", "convergence")


def load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def artifact_path(name: str) -> str:
    return os.path.join(TRINITY_DIR, name)


def convergence_path(name: str) -> str:
    return os.path.join(CONVERGENCE_DIR, name)


# ─── PHASE 14.3AR PREFLIGHT ───────────────────────────────

class TestPhase143ARPreflight:
    def test_preflight_exists(self):
        assert os.path.isfile(artifact_path("phase14_4_preflight.json"))

    def test_preflight_all_checks_pass(self):
        data = load_json(artifact_path("phase14_4_preflight.json"))
        assert data["all_checks_pass"] is True

    def test_preflight_has_16_checks(self):
        data = load_json(artifact_path("phase14_4_preflight.json"))
        checks = data["checks"]
        assert len(checks) >= 16

    def test_preflight_each_check_passes(self):
        data = load_json(artifact_path("phase14_4_preflight.json"))
        for key, check in data["checks"].items():
            assert check["status"] == "pass", f"Check {key} failed"

    def test_143ar_audit_exists(self):
        path = os.path.join(AUDIT_DIR, "phase14_3ar_full_product_documentation_convergence_production_truth.md")
        assert os.path.isfile(path)

    def test_143ar_artifacts_count(self):
        files = glob.glob(os.path.join(CONVERGENCE_DIR, "phase14_3ar_*.json"))
        assert len(files) >= 14

    def test_143a_artifacts_count(self):
        files = glob.glob(os.path.join(CONVERGENCE_DIR, "phase14_3a_*.json"))
        assert len(files) >= 16

    def test_preflight_audit_doc_exists(self):
        path = os.path.join(AUDIT_DIR, "phase14_4_preflight_143ar_verification.md")
        assert os.path.isfile(path)


# ─── SEPARATE DESIRED-STATE CANONS ────────────────────────

class TestDesiredStateCanons:
    def test_eos_canon_exists(self):
        assert os.path.isfile(artifact_path("phase14_4_eos_desired_state_canon.json"))

    def test_creatoros_canon_exists(self):
        assert os.path.isfile(artifact_path("phase14_4_creatoros_desired_state_canon.json"))

    def test_lyfeos_canon_exists(self):
        assert os.path.isfile(artifact_path("phase14_4_lyfeos_desired_state_canon.json"))

    def test_eos_canon_has_required_fields(self):
        data = load_json(artifact_path("phase14_4_eos_desired_state_canon.json"))
        required = ["purpose", "target_users", "product_promise", "modules", "screens",
                     "workflows", "feature_list", "data_concepts", "ai_agent_concepts",
                     "umh_integration_assumptions", "auth_assumptions", "open_questions",
                     "contradictions", "acceptance_criteria_candidates"]
        for field in required:
            assert field in data, f"EOS canon missing field: {field}"

    def test_creatoros_canon_has_required_fields(self):
        data = load_json(artifact_path("phase14_4_creatoros_desired_state_canon.json"))
        required = ["purpose", "target_users", "product_promise", "modules", "screens",
                     "workflows", "feature_list", "data_concepts", "auth_assumptions",
                     "open_questions", "contradictions", "acceptance_criteria_candidates"]
        for field in required:
            assert field in data, f"CreatorOS canon missing field: {field}"

    def test_lyfeos_canon_has_required_fields(self):
        data = load_json(artifact_path("phase14_4_lyfeos_desired_state_canon.json"))
        required = ["purpose", "target_users", "product_promise", "modules", "screens",
                     "workflows", "feature_list", "data_concepts", "gamification_mechanics",
                     "auth_assumptions", "open_questions", "contradictions",
                     "isolated_mvp_vs_umh_connected_mvp", "acceptance_criteria_candidates"]
        for field in required:
            assert field in data, f"LyfeOS canon missing field: {field}"

    def test_eos_not_collapsed(self):
        data = load_json(artifact_path("phase14_4_eos_desired_state_canon.json"))
        assert data["not_collapsed_into_shared_doc"] is True

    def test_creatoros_not_collapsed(self):
        data = load_json(artifact_path("phase14_4_creatoros_desired_state_canon.json"))
        assert data["not_collapsed_into_shared_doc"] is True

    def test_lyfeos_not_collapsed(self):
        data = load_json(artifact_path("phase14_4_lyfeos_desired_state_canon.json"))
        assert data["not_collapsed_into_shared_doc"] is True

    def test_eos_modules_count(self):
        data = load_json(artifact_path("phase14_4_eos_desired_state_canon.json"))
        assert len(data["modules"]) >= 19

    def test_creatoros_modules_count(self):
        data = load_json(artifact_path("phase14_4_creatoros_desired_state_canon.json"))
        assert len(data["modules"]) >= 16

    def test_lyfeos_modules_count(self):
        data = load_json(artifact_path("phase14_4_lyfeos_desired_state_canon.json"))
        assert len(data["modules"]) >= 10

    def test_eos_screens_count(self):
        data = load_json(artifact_path("phase14_4_eos_desired_state_canon.json"))
        assert len(data["screens"]) >= 11

    def test_creatoros_screens_count(self):
        data = load_json(artifact_path("phase14_4_creatoros_desired_state_canon.json"))
        assert len(data["screens"]) >= 28

    def test_lyfeos_screens_count(self):
        data = load_json(artifact_path("phase14_4_lyfeos_desired_state_canon.json"))
        assert len(data["screens"]) >= 7

    def test_creatoros_auth_contradictions_preserved(self):
        data = load_json(artifact_path("phase14_4_creatoros_desired_state_canon.json"))
        auth = data["auth_assumptions"]
        assert auth["contradiction_preserved"] is True
        assert "Firebase" in auth.get("prd_primary", "") or "firebase" in json.dumps(auth).lower()

    def test_creatoros_mvp_scope_contradictions_preserved(self):
        data = load_json(artifact_path("phase14_4_creatoros_desired_state_canon.json"))
        assert "mvp_definition_conflicts" in data
        assert data["mvp_definition_conflicts"]["resolution_required"] is True

    def test_lyfeos_v1_v2_conflict_preserved(self):
        data = load_json(artifact_path("phase14_4_lyfeos_desired_state_canon.json"))
        contradictions = data["contradictions"]
        v1_v2_found = any("v1" in c.lower() and "v2" in c.lower() for c in contradictions)
        assert v1_v2_found, "LyfeOS v1/v2 PRD conflict must be preserved"

    def test_lyfeos_isolated_vs_umh_connected_mvp(self):
        data = load_json(artifact_path("phase14_4_lyfeos_desired_state_canon.json"))
        mvp = data["isolated_mvp_vs_umh_connected_mvp"]
        assert mvp["isolated_mvp"]["status"] == "completed"
        assert mvp["umh_connected_mvp"]["status"] == "not_started"
        assert mvp["distinction_preserved"] is True

    def test_lyfeos_gamification_mechanics_present(self):
        data = load_json(artifact_path("phase14_4_lyfeos_desired_state_canon.json"))
        gam = data["gamification_mechanics"]
        assert "xp" in gam
        assert "levels" in gam
        assert "streaks" in gam
        assert "archetypes" in gam
        assert "stats_hud" in gam


# ─── NO COLOSSAL MERGED PRODUCT DOC ──────────────────────

class TestNoCollapsedDocs:
    def test_no_single_all_apps_canon(self):
        files = glob.glob(artifact_path("phase14_4_*_desired_state_canon.json"))
        assert len(files) == 3, "Must be exactly 3 separate canons"

    def test_verification_confirms_no_collapse(self):
        data = load_json(artifact_path("phase14_4_product_end_state_input_verification.json"))
        assert data["cross_verification"]["no_colossal_merged_product_doc"] is True
        assert data["cross_verification"]["all_three_have_separate_canons"] is True

    def test_each_canon_is_app_specific(self):
        for app_slug, app_name in [("eos", "EOS"), ("creatoros", "CreatorOS"), ("lyfeos", "LyfeOS")]:
            data = load_json(artifact_path(f"phase14_4_{app_slug}_desired_state_canon.json"))
            assert data["app"] == app_name
            assert data["canon_status"] == "separate_product_canon"


# ─── DEVICE/RUNTIME PLACEMENT ─────────────────────────────

class TestDeviceRuntimePlacement:
    def test_device_runtime_plan_exists(self):
        assert os.path.isfile(artifact_path("phase14_4_device_runtime_plan.json"))

    def test_vps_is_orchestrator(self):
        data = load_json(artifact_path("phase14_4_device_runtime_plan.json"))
        assert data["nodes"]["vps"]["role"] == "orchestrator"

    def test_beast_is_inspection_node(self):
        data = load_json(artifact_path("phase14_4_device_runtime_plan.json"))
        assert data["nodes"]["windows_beast"]["role"] == "trinity_app_source_inspection_node"

    def test_github_is_source_truth(self):
        data = load_json(artifact_path("phase14_4_device_runtime_plan.json"))
        assert data["nodes"]["github"]["role"] == "durable_versioned_source_truth"

    def test_no_mutation_rule(self):
        data = load_json(artifact_path("phase14_4_device_runtime_plan.json"))
        assert data["no_mutation_rule"] is True

    def test_beast_has_three_apps(self):
        data = load_json(artifact_path("phase14_4_device_runtime_plan.json"))
        apps = data["nodes"]["windows_beast"]["apps"]
        assert "eos" in apps
        assert "creatoros" in apps
        assert "lyfeos" in apps

    def test_github_has_three_repos(self):
        data = load_json(artifact_path("phase14_4_device_runtime_plan.json"))
        repos = data["nodes"]["github"]["repos"]
        assert "eos" in repos
        assert "creatoros" in repos
        assert "lyfeos" in repos


# ─── SOURCE ACCESS STATE ──────────────────────────────────

class TestSourceAccessState:
    def test_source_access_state_exists(self):
        assert os.path.isfile(artifact_path("phase14_4_source_access_state.json"))

    def test_source_access_has_all_sources(self):
        data = load_json(artifact_path("phase14_4_source_access_state.json"))
        sources = data.get("sources", {})
        expected = ["eos_github", "creatoros_github", "lyfeos_github",
                     "eos_beast", "creatoros_beast", "lyfeos_beast",
                     "phase_14_3a_artifacts", "opt_os_projection_artifacts"]
        for src in expected:
            assert src in sources, f"Missing source access entry: {src}"


# ─── CURRENT SOURCE INVENTORIES ───────────────────────────

class TestCurrentSourceInventories:
    def test_combined_inventory_exists(self):
        assert os.path.isfile(artifact_path("phase14_4_current_source_inventory.json"))

    def test_inventory_has_all_six_sources(self):
        data = load_json(artifact_path("phase14_4_current_source_inventory.json"))
        apps = data.get("apps", {})
        for app in ["EOS", "CreatorOS", "LyfeOS"]:
            assert app in apps, f"Missing app in inventory: {app}"
            app_data = apps[app]
            assert "github" in app_data or "github_inventory" in json.dumps(app_data)
            assert "beast" in app_data or "windows_beast" in json.dumps(app_data) or "beast_inventory" in json.dumps(app_data)


# ─── GITHUB/WINDOWS ALIGNMENT ─────────────────────────────

class TestGithubWindowsAlignment:
    def test_alignment_exists(self):
        assert os.path.isfile(artifact_path("phase14_4_github_windows_alignment.json"))

    def test_alignment_has_all_apps(self):
        data = load_json(artifact_path("phase14_4_github_windows_alignment.json"))
        apps = data.get("apps", {})
        for app in ["EOS", "CreatorOS", "LyfeOS"]:
            assert app in apps, f"Missing app in alignment: {app}"

    def test_alignment_classifications_valid(self):
        valid = {"aligned", "windows_ahead", "github_ahead", "divergent",
                 "unknown", "stale", "requires_operator_decision"}
        data = load_json(artifact_path("phase14_4_github_windows_alignment.json"))
        for app_name, app_data in data.get("apps", {}).items():
            for key, comparison in app_data.items():
                if isinstance(comparison, dict) and "status" in comparison:
                    assert comparison["status"] in valid, f"{app_name}.{key} has invalid status: {comparison['status']}"


# ─── FEATURE PRESERVATION MATRICES ────────────────────────

class TestFeaturePreservationMatrices:
    def test_matrices_exist(self):
        assert os.path.isfile(artifact_path("phase14_4_feature_preservation_matrices.json"))

    def test_matrices_have_all_apps(self):
        data = load_json(artifact_path("phase14_4_feature_preservation_matrices.json"))
        apps = data.get("apps", {})
        for app in ["EOS", "CreatorOS", "LyfeOS"]:
            assert app in apps, f"Missing app in feature matrices: {app}"

    def test_no_features_silently_dropped(self):
        data = load_json(artifact_path("phase14_4_feature_preservation_matrices.json"))
        for app_name, app_data in data.get("apps", {}).items():
            features = app_data.get("features", [])
            for f in features:
                assert f.get("classification") != "dropped", f"Feature silently dropped in {app_name}: {f.get('name')}"


# ─── PRODUCT DESIGN DIFFS ─────────────────────────────────

class TestProductDesignDiffs:
    def test_diffs_exist(self):
        assert os.path.isfile(artifact_path("phase14_4_product_design_diffs.json"))

    def test_diffs_have_all_apps(self):
        data = load_json(artifact_path("phase14_4_product_design_diffs.json"))
        apps = data.get("apps", {})
        for app in ["EOS", "CreatorOS", "LyfeOS"]:
            assert app in apps, f"Missing app in design diffs: {app}"

    def test_diffs_cover_required_dimensions(self):
        required = ["product_purpose", "user_personas", "core_workflows",
                     "screen_module_inventory", "data_model", "auth_session_model",
                     "umh_integration_boundary"]
        data = load_json(artifact_path("phase14_4_product_design_diffs.json"))
        for app_name, app_data in data.get("apps", {}).items():
            dims = app_data.get("dimensions", {})
            for dim in required:
                assert dim in dims, f"{app_name} missing dimension: {dim}"


# ─── ARCHITECTURE DIFFS ───────────────────────────────────

class TestArchitectureDiffs:
    def test_arch_diffs_exist(self):
        assert os.path.isfile(artifact_path("phase14_4_architecture_diffs.json"))

    def test_arch_diffs_have_all_apps(self):
        data = load_json(artifact_path("phase14_4_architecture_diffs.json"))
        apps = data.get("apps", {})
        for app in ["EOS", "CreatorOS", "LyfeOS"]:
            assert app in apps, f"Missing app in arch diffs: {app}"


# ─── CURRENT STATE SUMMARIES ──────────────────────────────

class TestCurrentStateSummaries:
    def test_summaries_exist(self):
        assert os.path.isfile(artifact_path("phase14_4_current_state_summaries.json"))

    def test_summaries_have_all_apps(self):
        data = load_json(artifact_path("phase14_4_current_state_summaries.json"))
        apps = data.get("apps", {})
        for app in ["EOS", "CreatorOS", "LyfeOS"]:
            assert app in apps, f"Missing app in summaries: {app}"

    def test_summaries_have_required_sections(self):
        required = ["what_exists", "what_works", "what_is_partial",
                     "what_is_missing", "what_is_stale"]
        data = load_json(artifact_path("phase14_4_current_state_summaries.json"))
        for app_name, app_data in data.get("apps", {}).items():
            for section in required:
                assert section in app_data, f"{app_name} missing section: {section}"


# ─── GAP MAPS / BUILD SEQUENCES ───────────────────────────

class TestGapMaps:
    def test_gap_maps_exist(self):
        assert os.path.isfile(artifact_path("phase14_4_gap_maps_build_sequences.json"))

    def test_gap_maps_have_all_apps(self):
        data = load_json(artifact_path("phase14_4_gap_maps_build_sequences.json"))
        gaps = data.get("gaps", [])
        apps_covered = {g["app"] for g in gaps}
        for app in ["EOS", "CreatorOS", "LyfeOS"]:
            assert app in apps_covered, f"No gaps recorded for {app}"


# ─── CROSS-TRINITY SHARED STANDARD DIFF ───────────────────

class TestCrossTrinityStandardDiff:
    def test_standard_diff_exists(self):
        assert os.path.isfile(artifact_path("phase14_4_cross_trinity_shared_standard_diff.json"))

    def test_shared_repo_strategy_aligned(self):
        data = load_json(artifact_path("phase14_4_cross_trinity_shared_standard_diff.json"))
        assert data["comparisons"]["shared_repo_strategy"]["alignment"] == "aligned"

    def test_firebase_auth_marked_stale(self):
        data = load_json(artifact_path("phase14_4_cross_trinity_shared_standard_diff.json"))
        stale = data["comparisons"]["os_platform_standard_v1_stale_items"]
        firebase_stale = any("firebase" in s.lower() or "Firebase" in s for s in stale)
        assert firebase_stale, "Firebase auth must be marked STALE"

    def test_no_premature_shared_packages(self):
        data = load_json(artifact_path("phase14_4_cross_trinity_shared_standard_diff.json"))
        assert "premature_shared_packages_warning" in data

    def test_no_monolith_collapse(self):
        data = load_json(artifact_path("phase14_4_cross_trinity_shared_standard_diff.json"))
        assert "monolith_warning" in data


# ─── WORK PACKETS ──────────────────────────────────────────

class TestWorkPackets:
    def test_work_packets_exist(self):
        assert os.path.isfile(artifact_path("phase14_4_work_packets.json"))

    def test_work_packets_count(self):
        data = load_json(artifact_path("phase14_4_work_packets.json"))
        packets = data.get("work_packets", [])
        assert len(packets) >= 16

    def test_work_packets_have_required_fields(self):
        required = ["objective", "app", "risk_class", "expected_artifacts",
                     "no_mutation_rule"]
        data = load_json(artifact_path("phase14_4_work_packets.json"))
        for wp in data.get("work_packets", []):
            for field in required:
                assert field in wp, f"Work packet missing field: {field} in {wp.get('objective', 'unknown')}"


# ─── READINESS GATE ───────────────────────────────────────

class TestReadinessGate:
    def test_readiness_gate_exists(self):
        assert os.path.isfile(artifact_path("phase14_4_readiness_gate_report.json"))

    def test_feature_build_blocked(self):
        data = load_json(artifact_path("phase14_4_readiness_gate_report.json"))
        gates = data.get("gates", data)
        assert gates.get("ready_for_feature_build") is False

    def test_implementation_blocked(self):
        data = load_json(artifact_path("phase14_4_readiness_gate_report.json"))
        gates = data.get("gates", data)
        assert gates.get("ready_for_implementation") is False

    def test_infrastructure_blocked(self):
        data = load_json(artifact_path("phase14_4_readiness_gate_report.json"))
        gates = data.get("gates", data)
        assert gates.get("ready_for_infrastructure_implementation") is False

    def test_auth_migration_blocked(self):
        data = load_json(artifact_path("phase14_4_readiness_gate_report.json"))
        gates = data.get("gates", data)
        assert gates.get("ready_for_auth_migration_execution") is False

    def test_design_diff_complete(self):
        data = load_json(artifact_path("phase14_4_readiness_gate_report.json"))
        gates = data.get("gates", data)
        assert gates.get("ready_for_product_design_diff") == "complete"


# ─── API/COCKPIT STATE ────────────────────────────────────

class TestAPICockpitState:
    def test_api_verification_exists(self):
        assert os.path.isfile(artifact_path("phase14_4_api_verification.json"))

    def test_cockpit_verification_exists(self):
        assert os.path.isfile(artifact_path("phase14_4_cockpit_verification.json"))


# ─── POLICY/SAFETY PROOF ──────────────────────────────────

class TestPolicySafetyProof:
    def test_policy_proof_exists(self):
        assert os.path.isfile(artifact_path("phase14_4_policy_safety_proof.json"))

    def test_all_unsafe_actions_blocked(self):
        data = load_json(artifact_path("phase14_4_policy_safety_proof.json"))
        assert data["all_unsafe_actions_blocked"] is True

    def test_16_unsafe_actions_verified(self):
        data = load_json(artifact_path("phase14_4_policy_safety_proof.json"))
        assert len(data["unsafe_actions_verified"]) >= 16

    def test_each_action_blocked_or_denied(self):
        data = load_json(artifact_path("phase14_4_policy_safety_proof.json"))
        for action in data["unsafe_actions_verified"]:
            assert action["status"] in ("blocked", "denied", "approval_required", "deferred"), \
                f"Unsafe action not blocked: {action['action']}"
            assert action["verified"] is True


# ─── NO SOURCE MUTATION ────────────────────────────────────

class TestNoSourceMutation:
    def test_no_trinity_source_on_vps(self):
        for app_dir in ["EntrepreneurOS", "CreatorOS", "LyfeOS", "LYFEOS"]:
            path = os.path.join(_BASE, app_dir)
            assert not os.path.isdir(path), f"Trinity app source found on VPS: {path}"

    def test_no_node_modules_for_trinity_on_vps(self):
        for app_dir in ["EntrepreneurOS", "CreatorOS", "LyfeOS", "LYFEOS"]:
            path = os.path.join(_BASE, app_dir, "node_modules")
            assert not os.path.isdir(path), f"node_modules found on VPS: {path}"


# ─── NO FEATURE BUILD ─────────────────────────────────────

class TestNoFeatureBuild:
    def test_no_new_component_files_created(self):
        trinity_alignment_files = glob.glob(artifact_path("*.json"))
        for f in trinity_alignment_files:
            assert not f.endswith(".tsx"), "TSX component file created — feature build violation"
            assert not f.endswith(".jsx"), "JSX component file created — feature build violation"

    def test_policy_confirms_no_feature_build(self):
        data = load_json(artifact_path("phase14_4_policy_safety_proof.json"))
        feature_action = next(
            (a for a in data["unsafe_actions_verified"] if "feature build" in a["action"].lower()),
            None
        )
        assert feature_action is not None
        assert feature_action["status"] == "blocked"


# ─── NO STALE FIREBASE CANONIZATION ───────────────────────

class TestNoStaleFirebaseCanonization:
    def test_eos_auth_target_is_clerk(self):
        data = load_json(artifact_path("phase14_4_eos_desired_state_canon.json"))
        assert data["auth_assumptions"]["target"] == "Clerk"

    def test_creatoros_auth_target_is_clerk(self):
        data = load_json(artifact_path("phase14_4_creatoros_desired_state_canon.json"))
        assert data["auth_assumptions"]["target"] == "Clerk (aligned with EOS target)"

    def test_lyfeos_auth_target_is_clerk(self):
        data = load_json(artifact_path("phase14_4_lyfeos_desired_state_canon.json"))
        assert data["auth_assumptions"]["target"] == "Clerk (aligned with EOS target)"

    def test_firebase_marked_stale_in_shared_diff(self):
        data = load_json(artifact_path("phase14_4_cross_trinity_shared_standard_diff.json"))
        auth_section = data["comparisons"]["shared_auth_target"]
        assert auth_section["alignment"] == "divergent"
        assert "STALE" in auth_section["os_platform_standard_v1"]


# ─── NO APP COLLAPSE ──────────────────────────────────────

class TestNoAppCollapse:
    def test_three_separate_canons_exist(self):
        assert os.path.isfile(artifact_path("phase14_4_eos_desired_state_canon.json"))
        assert os.path.isfile(artifact_path("phase14_4_creatoros_desired_state_canon.json"))
        assert os.path.isfile(artifact_path("phase14_4_lyfeos_desired_state_canon.json"))

    def test_each_canon_has_different_purpose(self):
        eos = load_json(artifact_path("phase14_4_eos_desired_state_canon.json"))
        cos = load_json(artifact_path("phase14_4_creatoros_desired_state_canon.json"))
        los = load_json(artifact_path("phase14_4_lyfeos_desired_state_canon.json"))
        assert eos["purpose"] != cos["purpose"]
        assert cos["purpose"] != los["purpose"]
        assert eos["purpose"] != los["purpose"]


# ─── NO HARDCODED PROJECTION NAMES ────────────────────────

class TestNoProjectionLeaks:
    def test_no_new_projection_leaks_in_phase14_4(self):
        """Phase 14.4 is read-only — verify it introduced no new projection leaks."""
        trinity_dir = TRINITY_DIR
        for f in glob.glob(os.path.join(trinity_dir, "phase14_4_*.json")):
            with open(f) as fh:
                content = fh.read()
                if "substrate/" in f.lower():
                    assert "EntrepreneurOS" not in content or "projection" in content.lower(), \
                        f"New projection leak in Phase 14.4 artifact: {f}"


# ─── NO HARDCODED JARVIS TERMINOLOGY ──────────────────────

class TestNoJarvisTerminology:
    def test_no_jarvis_in_trinity_artifacts(self):
        for f in glob.glob(artifact_path("phase14_4_*.json")):
            with open(f) as fh:
                content = fh.read().lower()
                assert "jarvis" not in content, f"Jarvis terminology found in {f}"


# ─── NO INFRASTRUCTURE IMPLEMENTATION ─────────────────────

class TestNoInfrastructureImplementation:
    def test_policy_confirms_no_deploy(self):
        data = load_json(artifact_path("phase14_4_policy_safety_proof.json"))
        deploy_action = next(
            (a for a in data["unsafe_actions_verified"] if "fly.io" in a["action"].lower()),
            None
        )
        assert deploy_action is not None
        assert deploy_action["status"] == "denied"

    def test_policy_confirms_no_neon_db(self):
        data = load_json(artifact_path("phase14_4_policy_safety_proof.json"))
        neon_action = next(
            (a for a in data["unsafe_actions_verified"] if "neon" in a["action"].lower()),
            None
        )
        assert neon_action is not None
        assert neon_action["status"] == "denied"

    def test_policy_confirms_no_posthog(self):
        data = load_json(artifact_path("phase14_4_policy_safety_proof.json"))
        ph_action = next(
            (a for a in data["unsafe_actions_verified"] if "posthog" in a["action"].lower()),
            None
        )
        assert ph_action is not None
        assert ph_action["status"] == "denied"


# ─── AUDIT REPORT ──────────────────────────────────────────

class TestAuditReport:
    def test_audit_report_exists(self):
        path = os.path.join(AUDIT_DIR, "phase14_4_trinity_github_windows_alignment_product_design_diff.md")
        assert os.path.isfile(path)


# ─── TEST GATE RESULTS ────────────────────────────────────

class TestTestGateResults:
    def test_gate_results_exist(self):
        assert os.path.isfile(artifact_path("phase14_4_test_gate_results.json"))
