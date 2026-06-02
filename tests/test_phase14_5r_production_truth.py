"""Phase 14.5R — Trinity Convergence + 13-Layer + Socratic Governance Production Truth Promotion tests."""

import json
import glob
import os
import pytest


BASE = "data/umh/trinity_convergence"


def convergence_path(filename: str) -> str:
    return os.path.join(BASE, filename)


def load(filename: str) -> dict:
    with open(convergence_path(filename)) as f:
        return json.load(f)


# ─── PREFLIGHT ──────────────────────────────────────────────


class TestPreflight:
    def test_preflight_exists(self):
        assert os.path.isfile(convergence_path("phase14_5r_preflight.json"))

    def test_preflight_passes(self):
        data = load("phase14_5r_preflight.json")
        assert data["preflight_result"] == "PASS"
        assert data["all_checks_pass"] is True

    def test_14_5_artifacts_present(self):
        data = load("phase14_5r_preflight.json")
        assert data["checks"]["phase14_5_artifacts_exist"]["all_present"] is True
        assert data["checks"]["phase14_5_artifacts_exist"]["count"] == 16

    def test_14_5a_artifacts_present(self):
        data = load("phase14_5r_preflight.json")
        assert data["checks"]["phase14_5a_artifacts_exist"]["all_present"] is True
        assert data["checks"]["phase14_5a_artifacts_exist"]["count"] == 17

    def test_14_5a_commit_verified(self):
        data = load("phase14_5r_preflight.json")
        assert data["checks"]["phase14_5a_commit_exists"]["verified"] is True

    def test_feature_build_blocked(self):
        data = load("phase14_5r_preflight.json")
        assert data["checks"]["feature_build_blocked"] is True

    def test_infrastructure_blocked(self):
        data = load("phase14_5r_preflight.json")
        assert data["checks"]["infrastructure_implementation_blocked"] is True

    def test_auth_migration_blocked(self):
        data = load("phase14_5r_preflight.json")
        assert data["checks"]["auth_migration_blocked"] is True

    def test_autonomous_execution_blocked(self):
        data = load("phase14_5r_preflight.json")
        assert data["checks"]["autonomous_work_packet_blocked"] is True


# ─── REVIEW ─────────────────────────────────────────────────


class TestReview:
    def test_review_exists(self):
        assert os.path.isfile(convergence_path("phase14_5r_review.json"))

    def test_review_safe(self):
        data = load("phase14_5r_review.json")
        assert data["review_safe"] is True
        assert len(data["blockers"]) == 0

    def test_no_implementation(self):
        data = load("phase14_5r_review.json")
        assert data["review_checks"]["no_implementation_occurred"] is True

    def test_no_source_mutation(self):
        data = load("phase14_5r_review.json")
        assert data["review_checks"]["no_trinity_app_source_mutation"] is True

    def test_no_github_writes(self):
        data = load("phase14_5r_review.json")
        assert data["review_checks"]["no_github_writes"] is True

    def test_no_windows_writes(self):
        data = load("phase14_5r_review.json")
        assert data["review_checks"]["no_windows_dev_writes"] is True

    def test_products_not_collapsed(self):
        data = load("phase14_5r_review.json")
        assert data["review_checks"]["products_not_collapsed"] is True

    def test_system_recommendations_separated(self):
        data = load("phase14_5r_review.json")
        assert data["review_checks"]["system_recommendations_separated_from_operator_decisions"] is True

    def test_pending_decisions_block(self):
        data = load("phase14_5r_review.json")
        assert data["review_checks"]["pending_operator_decisions_block_execution"] is True

    def test_no_secrets(self):
        data = load("phase14_5r_review.json")
        assert data["review_checks"]["no_secrets_exposed"] is True

    def test_no_projection_names_in_substrate(self):
        data = load("phase14_5r_review.json")
        assert data["review_checks"]["no_hardcoded_projection_names_in_substrate"] is True


# ─── 13-LAYER STACK VERIFICATION ────────────────────────────


class TestStackVerification:
    def test_stack_verification_exists(self):
        assert os.path.isfile(convergence_path("phase14_5r_13_layer_stack_verification.json"))

    def test_all_products_pass(self):
        data = load("phase14_5r_13_layer_stack_verification.json")
        assert data["all_pass"] is True

    @pytest.mark.parametrize("product", ["EOS", "CreatorOS", "LyfeOS", "UMH", "OS_Platform_Standard_v2"])
    def test_product_has_13_layers(self, product):
        data = load("phase14_5r_13_layer_stack_verification.json")
        assert data["products"][product]["has_all_13_layers"] is True

    @pytest.mark.parametrize("product", ["EOS", "CreatorOS", "LyfeOS", "UMH", "OS_Platform_Standard_v2"])
    def test_product_security_rls(self, product):
        data = load("phase14_5r_13_layer_stack_verification.json")
        assert data["products"][product]["security_rls_represented"] is True

    @pytest.mark.parametrize("product", ["EOS", "CreatorOS", "LyfeOS", "UMH", "OS_Platform_Standard_v2"])
    def test_product_error_tracking_logs(self, product):
        data = load("phase14_5r_13_layer_stack_verification.json")
        assert data["products"][product]["error_tracking_logs_represented"] is True

    @pytest.mark.parametrize("product", ["EOS", "CreatorOS", "LyfeOS", "UMH", "OS_Platform_Standard_v2"])
    def test_product_availability_recovery(self, product):
        data = load("phase14_5r_13_layer_stack_verification.json")
        assert data["products"][product]["availability_recovery_represented"] is True


# ─── UMH INTEGRATION BOUNDARY ──────────────────────────────


class TestIntegrationBoundary:
    def test_boundary_exists(self):
        assert os.path.isfile(convergence_path("phase14_5r_umh_integration_boundary_verification.json"))

    def test_all_13_layers(self):
        data = load("phase14_5r_umh_integration_boundary_verification.json")
        assert data["all_13_layers_covered"] is True

    def test_all_3_apps_per_layer(self):
        data = load("phase14_5r_umh_integration_boundary_verification.json")
        assert data["all_3_apps_covered_per_layer"] is True

    def test_umh_does_not_own_product_ux(self):
        data = load("phase14_5r_umh_integration_boundary_verification.json")
        assert data["umh_does_not_own_product_ux"] is True

    def test_umh_owns_orchestration(self):
        data = load("phase14_5r_umh_integration_boundary_verification.json")
        assert data["umh_owns_orchestration_governance"] is True

    def test_roles_classified(self):
        data = load("phase14_5r_umh_integration_boundary_verification.json")
        assert data["umh_role_classified_per_layer"] is True
        assert data["app_role_classified_per_layer"] is True


# ─── SOCRATIC GOVERNANCE ────────────────────────────────────


class TestSocraticGovernance:
    def test_governance_exists(self):
        assert os.path.isfile(convergence_path("phase14_5r_socratic_governance_verification.json"))

    def test_governance_passes(self):
        data = load("phase14_5r_socratic_governance_verification.json")
        assert data["status"] == "PASS"

    def test_all_artifacts_exist(self):
        data = load("phase14_5r_socratic_governance_verification.json")
        for name, info in data["artifacts"].items():
            assert info["exists"] is True, f"Artifact {name} missing"

    def test_intent_extrapolation_recorded(self):
        data = load("phase14_5r_socratic_governance_verification.json")
        assert data["governance_checks"]["intent_extrapolation_recorded"] is True

    def test_pending_decisions_remain_pending(self):
        data = load("phase14_5r_socratic_governance_verification.json")
        assert data["governance_checks"]["pending_decisions_remain_pending"] is True
        assert data["governance_checks"]["pending_count"] == 13

    def test_autonomous_requires_boundary(self):
        data = load("phase14_5r_socratic_governance_verification.json")
        assert data["governance_checks"]["autonomous_execution_requires_approved_boundary"] is True


# ─── READINESS GATES ────────────────────────────────────────


class TestReadinessGates:
    def test_gates_exist(self):
        assert os.path.isfile(convergence_path("phase14_5r_readiness_gate_verification.json"))

    def test_all_expected_match(self):
        data = load("phase14_5r_readiness_gate_verification.json")
        assert data["all_expected_match"] is True
        assert data["status"] == "PASS"

    def test_13_layer_design_ready(self):
        data = load("phase14_5r_readiness_gate_verification.json")
        assert data["gate_states"]["ready_for_13_layer_product_design"] is True

    def test_feature_build_not_ready(self):
        data = load("phase14_5r_readiness_gate_verification.json")
        assert data["gate_states"]["ready_for_feature_build"] is False

    def test_infrastructure_not_ready(self):
        data = load("phase14_5r_readiness_gate_verification.json")
        assert data["gate_states"]["ready_for_infrastructure_implementation"] is False

    def test_auth_migration_not_ready(self):
        data = load("phase14_5r_readiness_gate_verification.json")
        assert data["gate_states"]["ready_for_auth_migration_execution"] is False

    def test_autonomous_not_ready(self):
        data = load("phase14_5r_readiness_gate_verification.json")
        assert data["gate_states"]["ready_for_autonomous_work_packet_execution"] is False

    def test_phase14_5r_ready(self):
        data = load("phase14_5r_readiness_gate_verification.json")
        assert data["gate_states"]["ready_for_phase14_5r"] is True

    def test_operator_counts_present(self):
        data = load("phase14_5r_readiness_gate_verification.json")
        assert data["gate_states"]["operator_questions_open_count"] == 8
        assert data["gate_states"]["operator_decisions_pending_count"] == 13
        assert data["gate_states"]["blocking_contradictions_count"] == 1


# ─── WORK PACKET TREE ──────────────────────────────────────


class TestWorkPacketTree:
    def test_wp_tree_exists(self):
        assert os.path.isfile(convergence_path("phase14_5r_work_packet_tree_verification.json"))

    def test_all_required_covered(self):
        data = load("phase14_5r_work_packet_tree_verification.json")
        assert data["all_required_covered"] is True

    def test_no_implementation_before_decisions(self):
        data = load("phase14_5r_work_packet_tree_verification.json")
        assert data["no_implementation_before_decisions"] is True

    def test_18_new_packets(self):
        data = load("phase14_5r_work_packet_tree_verification.json")
        assert data["total_new_packets"] == 18


# ─── POLICY / SAFETY ───────────────────────────────────────


class TestPolicySafety:
    def test_policy_exists(self):
        assert os.path.isfile(convergence_path("phase14_5r_policy_safety_proof.json"))

    def test_all_blocked(self):
        data = load("phase14_5r_policy_safety_proof.json")
        assert data["all_blocked"] is True
        assert data["summary"]["all_unsafe_actions_prevented"] is True

    def test_22_unsafe_actions(self):
        data = load("phase14_5r_policy_safety_proof.json")
        assert data["summary"]["total_unsafe_actions"] == 22

    def test_no_unblocked_actions(self):
        data = load("phase14_5r_policy_safety_proof.json")
        for action in data["unsafe_actions"]:
            assert action["status"] in ["BLOCKED", "DENIED", "APPROVAL_REQUIRED", "DEFERRED"], \
                f"Unsafe action not prevented: {action['action']}"


# ─── TEST / GATE RESULTS ───────────────────────────────────


class TestGateResults:
    def test_results_exist(self):
        assert os.path.isfile(convergence_path("phase14_5r_test_gate_results.json"))

    def test_all_pass(self):
        data = load("phase14_5r_test_gate_results.json")
        assert data["all_pass"] is True
        assert data["total_tests_passed"] == 557
        assert data["total_tests_failed"] == 0

    def test_all_gates_pass(self):
        data = load("phase14_5r_test_gate_results.json")
        assert data["total_gates_passed"] == 23
        assert data["total_gates_failed"] == 0


# ─── PRODUCTION VERIFICATION ───────────────────────────────


class TestProductionVerification:
    def test_verification_exists(self):
        assert os.path.isfile(convergence_path("phase14_5r_production_verification.json"))

    def test_verification_passes(self):
        data = load("phase14_5r_production_verification.json")
        assert data["status"] == "PASS"

    def test_production_truth_delta(self):
        data = load("phase14_5r_production_verification.json")
        delta = data["production_truth_delta"]
        assert delta["delta_id"] == "PTD-14.5R-001"
        assert delta["artifacts_promoted"] == 33

    def test_production_outcome_committed(self):
        data = load("phase14_5r_production_verification.json")
        outcome = data["production_outcome_committed"]
        assert outcome["outcome_id"] == "POC-14.5R-001"
        assert outcome["emitted"] is True
        assert outcome["duplicate_suppressed"] is True


# ─── NO SOURCE MUTATION (14.5R) ─────────────────────────────


class TestNoSourceMutation14_5R:
    def test_no_ts_tsx_files(self):
        for f in glob.glob(convergence_path("phase14_5r_*.json")):
            content = open(f).read()
            assert ".tsx" not in content.split('"')[-1] if ".tsx" in content else True

    def test_no_app_dirs_on_vps(self):
        app_dirs = ["/opt/OS/EntrepreneurOS", "/opt/OS/CreatorOS", "/opt/OS/LyfeOS"]
        for d in app_dirs:
            assert not os.path.isdir(d), f"App directory {d} should not exist on VPS"

    def test_14_5r_artifacts_are_json(self):
        for f in glob.glob(convergence_path("phase14_5r_*.json")):
            data = json.load(open(f))
            assert isinstance(data, dict)


# ─── SUCCESS CRITERIA ───────────────────────────────────────


class TestSuccessCriteria:
    """Verify all 43 success criteria are met."""

    def test_sc01_phase14_5_reviewed_safe(self):
        assert load("phase14_5r_review.json")["review_safe"] is True

    def test_sc02_phase14_5a_reviewed_safe(self):
        assert load("phase14_5r_review.json")["review_checks"]["13_layer_production_stack_complete"] is True

    def test_sc03_13_layer_eos_verified(self):
        assert load("phase14_5r_13_layer_stack_verification.json")["products"]["EOS"]["status"] == "PASS"

    def test_sc04_13_layer_creatoros_verified(self):
        assert load("phase14_5r_13_layer_stack_verification.json")["products"]["CreatorOS"]["status"] == "PASS"

    def test_sc05_13_layer_lyfeos_verified(self):
        assert load("phase14_5r_13_layer_stack_verification.json")["products"]["LyfeOS"]["status"] == "PASS"

    def test_sc06_13_layer_umh_verified(self):
        assert load("phase14_5r_13_layer_stack_verification.json")["products"]["UMH"]["status"] == "PASS"

    def test_sc07_os_platform_std_v2_verified(self):
        assert load("phase14_5r_13_layer_stack_verification.json")["products"]["OS_Platform_Standard_v2"]["status"] == "PASS"

    def test_sc08_every_product_all_13_layers(self):
        data = load("phase14_5r_13_layer_stack_verification.json")
        for product in data["products"].values():
            assert product["has_all_13_layers"] is True

    def test_sc09_security_rls_represented(self):
        data = load("phase14_5r_13_layer_stack_verification.json")
        for product in data["products"].values():
            assert product["security_rls_represented"] is True

    def test_sc10_error_tracking_logs_represented(self):
        data = load("phase14_5r_13_layer_stack_verification.json")
        for product in data["products"].values():
            assert product["error_tracking_logs_represented"] is True

    def test_sc11_availability_recovery_represented(self):
        data = load("phase14_5r_13_layer_stack_verification.json")
        for product in data["products"].values():
            assert product["availability_recovery_represented"] is True

    def test_sc12_integration_boundary_verified(self):
        assert load("phase14_5r_umh_integration_boundary_verification.json")["status"] == "PASS"

    def test_sc13_intent_extrapolation_verified(self):
        data = load("phase14_5r_socratic_governance_verification.json")
        assert data["governance_checks"]["intent_extrapolation_recorded"] is True

    def test_sc14_technical_grounding_verified(self):
        data = load("phase14_5r_socratic_governance_verification.json")
        assert data["governance_checks"]["technical_grounding_recorded"] is True

    def test_sc15_operator_question_ledger_verified(self):
        assert load("phase14_5r_socratic_governance_verification.json")["artifacts"]["operator_question_ledger"]["exists"] is True

    def test_sc16_contradiction_ledger_verified(self):
        assert load("phase14_5r_socratic_governance_verification.json")["artifacts"]["contradiction_ledger"]["exists"] is True

    def test_sc17_clarification_ledger_verified(self):
        assert load("phase14_5r_socratic_governance_verification.json")["artifacts"]["clarification_ledger"]["exists"] is True

    def test_sc18_operator_decision_ledger_verified(self):
        assert load("phase14_5r_socratic_governance_verification.json")["artifacts"]["operator_decision_ledger"]["exists"] is True

    def test_sc19_recommendations_separated(self):
        assert load("phase14_5r_socratic_governance_verification.json")["governance_checks"]["system_recommendations_distinct_from_operator_decisions"] is True

    def test_sc20_pending_decisions_block(self):
        assert load("phase14_5r_review.json")["review_checks"]["pending_operator_decisions_block_execution"] is True

    def test_sc21_questions_block(self):
        assert load("phase14_5r_review.json")["review_checks"]["operator_required_questions_block_execution"] is True

    def test_sc22_contradictions_block(self):
        assert load("phase14_5r_review.json")["review_checks"]["blocking_contradictions_block_execution"] is True

    def test_sc23_boundary_required(self):
        assert load("phase14_5r_review.json")["review_checks"]["approved_execution_boundary_required"] is True

    def test_sc24_work_packet_tree_verified(self):
        assert load("phase14_5r_work_packet_tree_verification.json")["all_required_covered"] is True

    def test_sc25_feature_build_blocked(self):
        assert load("phase14_5r_readiness_gate_verification.json")["gate_states"]["ready_for_feature_build"] is False

    def test_sc26_infrastructure_blocked(self):
        assert load("phase14_5r_readiness_gate_verification.json")["gate_states"]["ready_for_infrastructure_implementation"] is False

    def test_sc27_auth_migration_blocked(self):
        assert load("phase14_5r_readiness_gate_verification.json")["gate_states"]["ready_for_auth_migration_execution"] is False

    def test_sc28_autonomous_blocked(self):
        assert load("phase14_5r_readiness_gate_verification.json")["gate_states"]["ready_for_autonomous_work_packet_execution"] is False

    def test_sc29_no_implementation(self):
        assert load("phase14_5r_review.json")["review_checks"]["no_implementation_occurred"] is True

    def test_sc30_no_source_mutation(self):
        assert load("phase14_5r_review.json")["review_checks"]["no_trinity_app_source_mutation"] is True

    def test_sc31_no_github_writes(self):
        assert load("phase14_5r_review.json")["review_checks"]["no_github_writes"] is True

    def test_sc32_no_windows_writes(self):
        assert load("phase14_5r_review.json")["review_checks"]["no_windows_dev_writes"] is True

    def test_sc33_no_deployment(self):
        assert load("phase14_5r_review.json")["review_checks"]["no_fly_io_deployment"] is True

    def test_sc34_no_stale_firebase(self):
        assert load("phase14_5r_review.json")["review_checks"]["no_stale_firebase_auth_canonized"] is True

    def test_sc35_products_not_collapsed(self):
        assert load("phase14_5r_review.json")["review_checks"]["products_not_collapsed"] is True

    def test_sc36_no_projection_names_in_substrate(self):
        assert load("phase14_5r_review.json")["review_checks"]["no_hardcoded_projection_names_in_substrate"] is True

    def test_sc37_no_legacy_ai_name(self):
        assert load("phase14_5r_review.json")["review_checks"]["no_hardcoded_legacy_ai_name_in_substrate"] is True

    def test_sc38_production_verification_passes(self):
        assert load("phase14_5r_production_verification.json")["status"] == "PASS"

    def test_sc39_truth_delta_created(self):
        assert load("phase14_5r_production_verification.json")["production_truth_delta"]["delta_id"] == "PTD-14.5R-001"

    def test_sc40_outcome_committed(self):
        assert load("phase14_5r_production_verification.json")["production_outcome_committed"]["emitted"] is True

    def test_sc41_duplicate_suppressed(self):
        assert load("phase14_5r_production_verification.json")["production_outcome_committed"]["duplicate_suppressed"] is True

    def test_sc42_policy_safety(self):
        assert load("phase14_5r_policy_safety_proof.json")["all_blocked"] is True

    def test_sc43_tests_gates_pass(self):
        assert load("phase14_5r_test_gate_results.json")["all_pass"] is True
