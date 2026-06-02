"""
Phase 14.5A tests — 13-layer production stack + Socratic governance completion.
Design-only phase. No implementation. No source mutation.
"""
from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, "/opt/OS")

BASE = os.environ.get("UMH_ROOT", "/opt/OS")
WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(WORKTREE, "data", "umh", "trinity_convergence")
AUDIT_DIR = os.path.join(WORKTREE, "docs", "audits", "convergence")


def load(name: str) -> dict:
    with open(os.path.join(DATA_DIR, name)) as f:
        return json.load(f)


LAYER_NAMES = [
    "Frontend Foundations",
    "APIs + Backend Logic",
    "Database + Storage",
    "Auth + Permissions",
    "Hosting + Deployment",
    "Cloud + Compute",
    "CI/CD + Version Control",
    "Security + Row-Level Security",
    "Rate Limiting",
    "Caching + CDN",
    "Load Balancing + Scaling",
    "Error Tracking + Logs",
    "Availability + Recovery",
]


class TestPhase145Preflight(unittest.TestCase):
    """Task 1 — verify Phase 14.5 completion."""

    def test_preflight_exists(self):
        d = load("phase14_5a_preflight.json")
        self.assertEqual(d["phase"], "14.5A")
        self.assertTrue(d["all_checks_pass"])

    def test_preflight_all_22_checks_pass(self):
        d = load("phase14_5a_preflight.json")
        self.assertEqual(d["check_count"], 22)
        self.assertEqual(d["passed_count"], 22)
        self.assertEqual(d["failed_count"], 0)

    def test_phase14_5_artifacts_count(self):
        d = load("phase14_5a_preflight.json")
        arts = d["checks"]["phase14_5_artifacts_exist"]
        self.assertEqual(arts["expected_count"], 16)
        self.assertEqual(arts["actual_count"], 16)

    def test_feature_build_blocked_in_preflight(self):
        d = load("phase14_5a_preflight.json")
        self.assertFalse(d["checks"]["feature_build_blocked"]["gate_value"])

    def test_infrastructure_blocked_in_preflight(self):
        d = load("phase14_5a_preflight.json")
        self.assertFalse(d["checks"]["infrastructure_blocked"]["gate_value"])

    def test_auth_migration_blocked_in_preflight(self):
        d = load("phase14_5a_preflight.json")
        self.assertFalse(d["checks"]["auth_migration_blocked"]["gate_value"])


class TestEOS13Layer(unittest.TestCase):
    """Task 2-3 — EOS 13-layer production stack."""

    def setUp(self):
        self.d = load("phase14_5a_eos_13_layer_production_stack.json")

    def test_exists_and_correct_app(self):
        self.assertEqual(self.d["app"], "EOS")

    def test_has_all_13_layers(self):
        self.assertEqual(len(self.d["layers"]), 13)

    def test_layer_numbers_sequential(self):
        nums = [l["layer_number"] for l in self.d["layers"]]
        self.assertEqual(nums, list(range(1, 14)))

    def test_all_layer_names_present(self):
        names = [l["layer_name"] for l in self.d["layers"]]
        for expected in LAYER_NAMES:
            self.assertIn(expected, names)

    def test_implementation_not_allowed(self):
        self.assertFalse(self.d["implementation_allowed"])

    def test_production_design_not_complete(self):
        self.assertFalse(self.d["production_design_complete"])

    def test_source_divergence_reflected(self):
        layer1 = self.d["layers"][0]
        self.assertIn("divergen", layer1["current_state"].lower())

    def test_beast_clerk_reflected(self):
        layer4 = self.d["layers"][3]
        self.assertIn("Clerk", layer4["current_state"])


class TestCreatorOS13Layer(unittest.TestCase):
    """Task 2-3 — CreatorOS 13-layer production stack."""

    def setUp(self):
        self.d = load("phase14_5a_creatoros_13_layer_production_stack.json")

    def test_exists_and_correct_app(self):
        self.assertEqual(self.d["app"], "CreatorOS")

    def test_has_all_13_layers(self):
        self.assertEqual(len(self.d["layers"]), 13)

    def test_layer_numbers_sequential(self):
        nums = [l["layer_number"] for l in self.d["layers"]]
        self.assertEqual(nums, list(range(1, 14)))

    def test_all_layer_names_present(self):
        names = [l["layer_name"] for l in self.d["layers"]]
        for expected in LAYER_NAMES:
            self.assertIn(expected, names)

    def test_auth_bypass_reflected(self):
        layer4 = self.d["layers"][3]
        self.assertIn("comparePasswords", layer4["current_state"])
        self.assertEqual(layer4["risk_level"], "CRITICAL")

    def test_god_files_reflected(self):
        layer1 = self.d["layers"][0]
        self.assertIn("god", layer1["gap"].lower())

    def test_implementation_not_allowed(self):
        self.assertFalse(self.d["implementation_allowed"])


class TestLyfeOS13Layer(unittest.TestCase):
    """Task 2-3 — LyfeOS 13-layer production stack."""

    def setUp(self):
        self.d = load("phase14_5a_lyfeos_13_layer_production_stack.json")

    def test_exists_and_correct_app(self):
        self.assertEqual(self.d["app"], "LyfeOS")

    def test_has_all_13_layers(self):
        self.assertEqual(len(self.d["layers"]), 13)

    def test_layer_numbers_sequential(self):
        nums = [l["layer_number"] for l in self.d["layers"]]
        self.assertEqual(nums, list(range(1, 14)))

    def test_all_layer_names_present(self):
        names = [l["layer_name"] for l in self.d["layers"]]
        for expected in LAYER_NAMES:
            self.assertIn(expected, names)

    def test_deployed_mvp_reflected(self):
        layer1 = self.d["layers"][0]
        self.assertIn("lyfeos.net", layer1["current_state"])

    def test_35_tables_reflected(self):
        layer3 = self.d["layers"][2]
        self.assertIn("35", layer3["current_state"])

    def test_implementation_not_allowed(self):
        self.assertFalse(self.d["implementation_allowed"])


class TestUMH13Layer(unittest.TestCase):
    """Task 2-3 — UMH 13-layer production stack."""

    def setUp(self):
        self.d = load("phase14_5a_umh_13_layer_production_stack.json")

    def test_exists_and_correct_app(self):
        self.assertEqual(self.d["app"], "UMH")

    def test_has_all_13_layers(self):
        self.assertEqual(len(self.d["layers"]), 13)

    def test_layer_numbers_sequential(self):
        nums = [l["layer_number"] for l in self.d["layers"]]
        self.assertEqual(nums, list(range(1, 14)))

    def test_all_layer_names_present(self):
        names = [l["layer_name"] for l in self.d["layers"]]
        for expected in LAYER_NAMES:
            self.assertIn(expected, names)

    def test_orchestrator_role_reflected(self):
        self.assertIn("orchestrat", self.d["note"].lower())

    def test_some_layers_operational(self):
        self.assertGreater(self.d["summary"]["layers_operational"], 0)

    def test_implementation_not_allowed(self):
        self.assertFalse(self.d["implementation_allowed"])


class TestOSPlatformStandardV2(unittest.TestCase):
    """Task 4 — OS Platform Standard v2 13-layer defaults."""

    def setUp(self):
        self.d = load("phase14_5a_os_platform_standard_v2_13_layer_defaults.json")

    def test_exists(self):
        self.assertEqual(self.d["phase"], "14.5A")

    def test_has_all_13_layers(self):
        self.assertEqual(len(self.d["layers"]), 13)

    def test_layer_numbers_sequential(self):
        nums = [l["layer_number"] for l in self.d["layers"]]
        self.assertEqual(nums, list(range(1, 14)))

    def test_all_layer_names_present(self):
        names = [l["layer_name"] for l in self.d["layers"]]
        for expected in LAYER_NAMES:
            self.assertIn(expected, names)

    def test_firebase_removed(self):
        layer4 = self.d["layers"][3]
        self.assertIn("Firebase", str(layer4.get("stale_v1_items_removed", [])))

    def test_clerk_is_auth_standard(self):
        layer4 = self.d["layers"][3]
        self.assertEqual(layer4["default_standard"]["provider"], "Clerk")

    def test_implementation_not_allowed(self):
        self.assertFalse(self.d["implementation_allowed"])


class TestUMHIntegrationBoundary(unittest.TestCase):
    """Task 5 — UMH 13-layer integration boundary."""

    def setUp(self):
        self.d = load("phase14_5a_umh_13_layer_integration_boundary.json")

    def test_exists(self):
        self.assertEqual(self.d["phase"], "14.5A")

    def test_has_all_13_layers(self):
        self.assertEqual(len(self.d["boundaries"]), 13)

    def test_each_layer_has_3_apps(self):
        for b in self.d["boundaries"]:
            self.assertEqual(len(b["apps"]), 3)

    def test_umh_never_owns_app_layer(self):
        for b in self.d["boundaries"]:
            for app in b["apps"]:
                self.assertNotEqual(app["umh_role"], "owner")

    def test_app_always_owns(self):
        for b in self.d["boundaries"]:
            for app in b["apps"]:
                self.assertEqual(app["app_role"], "owner")

    def test_implementation_not_allowed(self):
        self.assertFalse(self.d["implementation_allowed"])


class TestIntentExtrapolation(unittest.TestCase):
    """Task 6 — intent extrapolation artifact."""

    def setUp(self):
        self.d = load("phase14_5a_intent_extrapolation.json")

    def test_exists(self):
        self.assertEqual(self.d["phase"], "14.5A")

    def test_has_operator_intent_summary(self):
        self.assertIn("operator_intent_summary", self.d)
        self.assertGreater(len(self.d["operator_intent_summary"]), 50)

    def test_has_inferred_goals(self):
        self.assertGreater(len(self.d["inferred_goals"]), 0)

    def test_has_explicit_goals(self):
        self.assertGreater(len(self.d["explicit_goals"]), 0)

    def test_has_implicit_goals(self):
        self.assertGreater(len(self.d["implicit_goals"]), 0)

    def test_has_all_product_intents(self):
        for p in ["UMH", "EOS", "CreatorOS", "LyfeOS"]:
            self.assertIn(p, self.d["product_specific_intent"])

    def test_has_confidence_by_area(self):
        self.assertIn("confidence_by_area", self.d)
        self.assertGreater(len(self.d["confidence_by_area"]), 0)

    def test_has_unresolved_gaps(self):
        self.assertGreater(len(self.d["unresolved_intent_gaps"]), 0)

    def test_questions_required(self):
        self.assertTrue(self.d["questions_required"])

    def test_operator_decisions_needed(self):
        self.assertGreater(len(self.d["operator_decisions_needed"]), 8)

    def test_socratic_intent_stated(self):
        summary = self.d["operator_intent_summary"]
        self.assertIn("Socratic", summary)

    def test_autonomy_requires_boundary(self):
        self.assertIn("approved execution boundary", self.d["autonomy_intent"].lower())


class TestTechnicalGrounding(unittest.TestCase):
    """Task 7 — technical grounding artifact."""

    def setUp(self):
        self.d = load("phase14_5a_technical_grounding.json")

    def test_exists(self):
        self.assertEqual(self.d["phase"], "14.5A")

    def test_has_5_scopes(self):
        self.assertEqual(len(self.d["scopes"]), 5)

    def test_all_products_grounded(self):
        names = [s["product_or_scope"] for s in self.d["scopes"]]
        for p in ["EOS", "CreatorOS", "LyfeOS", "UMH", "OS Platform Standard v2"]:
            self.assertIn(p, names)

    def test_eos_not_grounded(self):
        eos = [s for s in self.d["scopes"] if s["product_or_scope"] == "EOS"][0]
        self.assertFalse(eos["technically_grounded"])

    def test_creatoros_not_grounded(self):
        cos = [s for s in self.d["scopes"] if s["product_or_scope"] == "CreatorOS"][0]
        self.assertFalse(cos["technically_grounded"])

    def test_lyfeos_grounded(self):
        los = [s for s in self.d["scopes"] if s["product_or_scope"] == "LyfeOS"][0]
        self.assertTrue(los["technically_grounded"])

    def test_umh_grounded(self):
        umh = [s for s in self.d["scopes"] if s["product_or_scope"] == "UMH"][0]
        self.assertTrue(umh["technically_grounded"])

    def test_implementation_not_allowed(self):
        self.assertFalse(self.d["implementation_allowed"])


class TestOperatorQuestionLedger(unittest.TestCase):
    """Task 8 — operator question ledger."""

    def setUp(self):
        self.d = load("phase14_5a_operator_question_ledger.json")

    def test_exists(self):
        self.assertEqual(self.d["phase"], "14.5A")

    def test_has_questions(self):
        self.assertGreater(len(self.d["questions"]), 10)

    def test_questions_have_required_fields(self):
        for q in self.d["questions"]:
            self.assertIn("question_id", q)
            self.assertIn("question", q)
            self.assertIn("why_it_matters", q)
            self.assertIn("options", q)
            self.assertIn("recommended_option", q)
            self.assertIn("operator_response_required", q)

    def test_eos_source_question_exists(self):
        ids = [q["question_id"] for q in self.d["questions"]]
        self.assertIn("Q-001", ids)

    def test_creatoros_mvp_question_exists(self):
        ids = [q["question_id"] for q in self.d["questions"]]
        self.assertIn("Q-002", ids)

    def test_clerk_migration_question_exists(self):
        ids = [q["question_id"] for q in self.d["questions"]]
        self.assertIn("Q-004", ids)

    def test_operator_required_count(self):
        count = sum(1 for q in self.d["questions"] if q["operator_response_required"])
        self.assertGreaterEqual(count, 8)

    def test_implementation_not_allowed(self):
        self.assertFalse(self.d["implementation_allowed"])


class TestContradictionLedger(unittest.TestCase):
    """Task 9 — contradiction ledger."""

    def setUp(self):
        self.d = load("phase14_5a_contradiction_ledger.json")

    def test_exists(self):
        self.assertEqual(self.d["phase"], "14.5A")

    def test_has_contradictions(self):
        self.assertGreater(len(self.d["contradictions"]), 5)

    def test_contradictions_have_required_fields(self):
        for c in self.d["contradictions"]:
            self.assertIn("contradiction_id", c)
            self.assertIn("conflicting_claims", c)
            self.assertIn("possible_resolutions", c)
            self.assertIn("recommended_resolution", c)
            self.assertIn("operator_decision_required", c)

    def test_auth_bypass_contradiction_exists(self):
        ids = [c["contradiction_id"] for c in self.d["contradictions"]]
        self.assertIn("CONTRA-001", ids)

    def test_firebase_clerk_contradiction_exists(self):
        ids = [c["contradiction_id"] for c in self.d["contradictions"]]
        self.assertIn("CONTRA-002", ids)

    def test_eos_source_contradiction_exists(self):
        ids = [c["contradiction_id"] for c in self.d["contradictions"]]
        self.assertIn("CONTRA-003", ids)

    def test_blocking_contradictions_identified(self):
        self.assertGreaterEqual(self.d["summary"]["blocking_contradictions"], 1)


class TestClarificationLedger(unittest.TestCase):
    """Task 10 — clarification ledger."""

    def setUp(self):
        self.d = load("phase14_5a_clarification_ledger.json")

    def test_exists(self):
        self.assertEqual(self.d["phase"], "14.5A")

    def test_has_clarifications(self):
        self.assertGreater(len(self.d["clarifications"]), 5)

    def test_clarifications_have_required_fields(self):
        for c in self.d["clarifications"]:
            self.assertIn("clarification_id", c)
            self.assertIn("unclear_item", c)
            self.assertIn("possible_interpretations", c)
            self.assertIn("recommended_interpretation", c)
            self.assertIn("operator_response_required", c)

    def test_production_ready_clarification_exists(self):
        items = [c["unclear_item"] for c in self.d["clarifications"]]
        self.assertTrue(any("production ready" in i.lower() for i in items))


class TestOperatorDecisionLedger(unittest.TestCase):
    """Task 11 — operator decision ledger."""

    def setUp(self):
        self.d = load("phase14_5a_operator_decision_ledger.json")

    def test_exists(self):
        self.assertEqual(self.d["phase"], "14.5A")

    def test_has_decisions(self):
        self.assertGreater(len(self.d["decisions"]), 10)

    def test_decisions_have_required_fields(self):
        for dec in self.d["decisions"]:
            self.assertIn("decision_id", dec)
            self.assertIn("decision_name", dec)
            self.assertIn("options", dec)
            self.assertIn("system_recommendation", dec)
            self.assertIn("operator_selected_option", dec)
            self.assertIn("status", dec)
            self.assertIn("can_proceed_without_decision", dec)

    def test_all_decisions_pending(self):
        for dec in self.d["decisions"]:
            self.assertEqual(dec["status"], "pending")

    def test_no_operator_selected_options(self):
        for dec in self.d["decisions"]:
            self.assertIsNone(dec["operator_selected_option"])

    def test_system_recommendations_separate_from_decisions(self):
        for dec in self.d["decisions"]:
            self.assertIsNotNone(dec["system_recommendation"])
            self.assertIsNone(dec["operator_selected_option"])

    def test_pending_decisions_block_execution(self):
        blocking = [d for d in self.d["decisions"] if not d["can_proceed_without_decision"]]
        self.assertGreater(len(blocking), 0)

    def test_carries_forward_phase14_5_decisions(self):
        ids = [d["decision_id"] for d in self.d["decisions"]]
        for i in range(1, 9):
            self.assertIn(f"DEC-145-{i:03d}", ids)


class TestReadinessGate(unittest.TestCase):
    """Task 12 — readiness gate report."""

    def setUp(self):
        self.d = load("phase14_5a_13_layer_readiness_gate_report.json")

    def test_exists(self):
        self.assertEqual(self.d["phase"], "14.5A")

    def test_13_layer_design_ready(self):
        self.assertTrue(self.d["gates"]["ready_for_13_layer_product_design"])

    def test_all_product_designs_ready(self):
        self.assertTrue(self.d["gates"]["ready_for_eos_13_layer_design"])
        self.assertTrue(self.d["gates"]["ready_for_creatoros_13_layer_design"])
        self.assertTrue(self.d["gates"]["ready_for_lyfeos_13_layer_design"])
        self.assertTrue(self.d["gates"]["ready_for_umh_13_layer_design"])

    def test_os_platform_v2_ready(self):
        self.assertTrue(self.d["gates"]["ready_for_os_platform_standard_v2_13_layers"])

    def test_intent_extrapolated(self):
        self.assertTrue(self.d["gates"]["intent_extrapolated"])

    def test_technical_grounding_complete(self):
        self.assertTrue(self.d["gates"]["technical_grounding_complete"])

    def test_feature_build_blocked(self):
        self.assertFalse(self.d["gates"]["ready_for_feature_build"])

    def test_infrastructure_blocked(self):
        self.assertFalse(self.d["gates"]["ready_for_infrastructure_implementation"])

    def test_auth_migration_blocked(self):
        self.assertFalse(self.d["gates"]["ready_for_auth_migration_execution"])

    def test_autonomous_execution_blocked(self):
        self.assertFalse(self.d["gates"]["ready_for_autonomous_work_packet_execution"])

    def test_no_approved_boundary(self):
        self.assertFalse(self.d["gates"]["approved_execution_boundary_exists"])

    def test_ready_for_phase14_5r(self):
        self.assertTrue(self.d["gates"]["ready_for_phase14_5r"])

    def test_open_questions_counted(self):
        self.assertGreater(self.d["gates"]["socratic_questions_open_count"], 0)

    def test_pending_decisions_counted(self):
        self.assertGreater(self.d["gates"]["operator_decisions_pending_count"], 0)


class TestWorkPacketTree(unittest.TestCase):
    """Task 13 — updated work packet tree."""

    def setUp(self):
        self.d = load("phase14_5a_updated_work_packet_tree.json")

    def test_exists(self):
        self.assertEqual(self.d["phase"], "14.5A")

    def test_has_18_new_packets(self):
        self.assertEqual(len(self.d["new_packets"]), 18)

    def test_total_is_53(self):
        self.assertEqual(self.d["total_packets"], 53)

    def test_all_packets_planning_only(self):
        for wp in self.d["new_packets"]:
            self.assertIn("blocked_actions", wp)

    def test_packets_have_required_fields(self):
        for wp in self.d["new_packets"]:
            self.assertIn("id", wp)
            self.assertIn("objective", wp)
            self.assertIn("risk_class", wp)
            self.assertIn("operator_decision_required", wp)
            self.assertIn("can_execute_now", wp)

    def test_13_layer_ratification_packets_exist(self):
        ids = [wp["id"] for wp in self.d["new_packets"]]
        for i in range(1, 6):
            self.assertIn(f"WP-13L-{i:03d}", ids)

    def test_governance_session_packets_exist(self):
        ids = [wp["id"] for wp in self.d["new_packets"]]
        for i in range(1, 6):
            self.assertIn(f"WP-GOV-{i:03d}", ids)

    def test_execution_boundary_packet_exists(self):
        ids = [wp["id"] for wp in self.d["new_packets"]]
        self.assertIn("WP-GOV-005", ids)


class TestPolicySafetyProof(unittest.TestCase):
    """Task 14 — policy/safety proof."""

    def setUp(self):
        self.d = load("phase14_5a_policy_safety_proof.json")

    def test_exists(self):
        self.assertEqual(self.d["phase"], "14.5A")

    def test_all_20_unsafe_actions_listed(self):
        self.assertEqual(len(self.d["unsafe_actions"]), 20)

    def test_all_blocked_or_denied(self):
        self.assertTrue(self.d["all_blocked"])
        for ua in self.d["unsafe_actions"]:
            self.assertIn(ua["status"], ["BLOCKED", "DENIED"])

    def test_no_implementation_allowed(self):
        impl = [ua for ua in self.d["unsafe_actions"] if ua["action"] == "Implementing any of the 13 layers"]
        self.assertEqual(len(impl), 1)
        self.assertEqual(impl[0]["status"], "BLOCKED")

    def test_no_neon_creation(self):
        neon = [ua for ua in self.d["unsafe_actions"] if "Neon" in ua["action"]]
        self.assertEqual(len(neon), 1)
        self.assertEqual(neon[0]["status"], "BLOCKED")

    def test_no_fly_deployment(self):
        fly = [ua for ua in self.d["unsafe_actions"] if "Fly.io" in ua["action"]]
        self.assertEqual(len(fly), 1)
        self.assertEqual(fly[0]["status"], "BLOCKED")

    def test_no_stale_firebase(self):
        fb = [ua for ua in self.d["unsafe_actions"] if "Firebase" in ua["action"]]
        self.assertEqual(len(fb), 1)
        self.assertEqual(fb[0]["status"], "DENIED")

    def test_no_app_collapse(self):
        coll = [ua for ua in self.d["unsafe_actions"] if "Collapsing" in ua["action"]]
        self.assertEqual(len(coll), 1)
        self.assertEqual(coll[0]["status"], "DENIED")

    def test_no_silent_contradiction_resolution(self):
        sc = [ua for ua in self.d["unsafe_actions"] if "Silently resolving" in ua["action"]]
        self.assertEqual(len(sc), 1)
        self.assertEqual(sc[0]["status"], "DENIED")

    def test_no_silent_scope_decision(self):
        ss = [ua for ua in self.d["unsafe_actions"] if "Silently choosing" in ua["action"]]
        self.assertEqual(len(ss), 1)
        self.assertEqual(ss[0]["status"], "DENIED")


class TestLayerCompleteness(unittest.TestCase):
    """Cross-product 13-layer completeness tests."""

    def test_frontend_layer_all_products(self):
        for f in [
            "phase14_5a_eos_13_layer_production_stack.json",
            "phase14_5a_creatoros_13_layer_production_stack.json",
            "phase14_5a_lyfeos_13_layer_production_stack.json",
            "phase14_5a_umh_13_layer_production_stack.json",
        ]:
            d = load(f)
            names = [l["layer_name"] for l in d["layers"]]
            self.assertIn("Frontend Foundations", names, f"{f} missing Frontend Foundations")

    def test_api_layer_all_products(self):
        for f in [
            "phase14_5a_eos_13_layer_production_stack.json",
            "phase14_5a_creatoros_13_layer_production_stack.json",
            "phase14_5a_lyfeos_13_layer_production_stack.json",
            "phase14_5a_umh_13_layer_production_stack.json",
        ]:
            d = load(f)
            names = [l["layer_name"] for l in d["layers"]]
            self.assertIn("APIs + Backend Logic", names, f"{f} missing APIs + Backend Logic")

    def test_database_layer_all_products(self):
        for f in [
            "phase14_5a_eos_13_layer_production_stack.json",
            "phase14_5a_creatoros_13_layer_production_stack.json",
            "phase14_5a_lyfeos_13_layer_production_stack.json",
            "phase14_5a_umh_13_layer_production_stack.json",
        ]:
            d = load(f)
            names = [l["layer_name"] for l in d["layers"]]
            self.assertIn("Database + Storage", names, f"{f} missing Database + Storage")

    def test_auth_layer_all_products(self):
        for f in [
            "phase14_5a_eos_13_layer_production_stack.json",
            "phase14_5a_creatoros_13_layer_production_stack.json",
            "phase14_5a_lyfeos_13_layer_production_stack.json",
            "phase14_5a_umh_13_layer_production_stack.json",
        ]:
            d = load(f)
            names = [l["layer_name"] for l in d["layers"]]
            self.assertIn("Auth + Permissions", names, f"{f} missing Auth + Permissions")

    def test_hosting_layer_all_products(self):
        for f in [
            "phase14_5a_eos_13_layer_production_stack.json",
            "phase14_5a_creatoros_13_layer_production_stack.json",
            "phase14_5a_lyfeos_13_layer_production_stack.json",
            "phase14_5a_umh_13_layer_production_stack.json",
        ]:
            d = load(f)
            names = [l["layer_name"] for l in d["layers"]]
            self.assertIn("Hosting + Deployment", names, f"{f} missing Hosting + Deployment")

    def test_security_layer_all_products(self):
        for f in [
            "phase14_5a_eos_13_layer_production_stack.json",
            "phase14_5a_creatoros_13_layer_production_stack.json",
            "phase14_5a_lyfeos_13_layer_production_stack.json",
            "phase14_5a_umh_13_layer_production_stack.json",
        ]:
            d = load(f)
            names = [l["layer_name"] for l in d["layers"]]
            self.assertIn("Security + Row-Level Security", names, f"{f} missing Security + RLS")

    def test_rate_limiting_layer_all_products(self):
        for f in [
            "phase14_5a_eos_13_layer_production_stack.json",
            "phase14_5a_creatoros_13_layer_production_stack.json",
            "phase14_5a_lyfeos_13_layer_production_stack.json",
            "phase14_5a_umh_13_layer_production_stack.json",
        ]:
            d = load(f)
            names = [l["layer_name"] for l in d["layers"]]
            self.assertIn("Rate Limiting", names, f"{f} missing Rate Limiting")

    def test_caching_layer_all_products(self):
        for f in [
            "phase14_5a_eos_13_layer_production_stack.json",
            "phase14_5a_creatoros_13_layer_production_stack.json",
            "phase14_5a_lyfeos_13_layer_production_stack.json",
            "phase14_5a_umh_13_layer_production_stack.json",
        ]:
            d = load(f)
            names = [l["layer_name"] for l in d["layers"]]
            self.assertIn("Caching + CDN", names, f"{f} missing Caching + CDN")

    def test_load_balancing_layer_all_products(self):
        for f in [
            "phase14_5a_eos_13_layer_production_stack.json",
            "phase14_5a_creatoros_13_layer_production_stack.json",
            "phase14_5a_lyfeos_13_layer_production_stack.json",
            "phase14_5a_umh_13_layer_production_stack.json",
        ]:
            d = load(f)
            names = [l["layer_name"] for l in d["layers"]]
            self.assertIn("Load Balancing + Scaling", names, f"{f} missing Load Balancing + Scaling")

    def test_error_tracking_layer_all_products(self):
        for f in [
            "phase14_5a_eos_13_layer_production_stack.json",
            "phase14_5a_creatoros_13_layer_production_stack.json",
            "phase14_5a_lyfeos_13_layer_production_stack.json",
            "phase14_5a_umh_13_layer_production_stack.json",
        ]:
            d = load(f)
            names = [l["layer_name"] for l in d["layers"]]
            self.assertIn("Error Tracking + Logs", names, f"{f} missing Error Tracking + Logs")

    def test_availability_layer_all_products(self):
        for f in [
            "phase14_5a_eos_13_layer_production_stack.json",
            "phase14_5a_creatoros_13_layer_production_stack.json",
            "phase14_5a_lyfeos_13_layer_production_stack.json",
            "phase14_5a_umh_13_layer_production_stack.json",
        ]:
            d = load(f)
            names = [l["layer_name"] for l in d["layers"]]
            self.assertIn("Availability + Recovery", names, f"{f} missing Availability + Recovery")

    def test_no_product_marked_complete(self):
        for f in [
            "phase14_5a_eos_13_layer_production_stack.json",
            "phase14_5a_creatoros_13_layer_production_stack.json",
            "phase14_5a_lyfeos_13_layer_production_stack.json",
            "phase14_5a_umh_13_layer_production_stack.json",
        ]:
            d = load(f)
            self.assertFalse(d["production_design_complete"], f"{f} incorrectly marked complete")


class TestGovernanceIntegrity(unittest.TestCase):
    """Cross-artifact governance integrity tests."""

    def test_no_silent_canonization(self):
        dl = load("phase14_5a_operator_decision_ledger.json")
        for dec in dl["decisions"]:
            self.assertIsNone(dec["operator_selected_option"])

    def test_no_silent_contradiction_resolution_in_artifacts(self):
        cl = load("phase14_5a_contradiction_ledger.json")
        requiring = [c for c in cl["contradictions"] if c["operator_decision_required"]]
        self.assertGreater(len(requiring), 0)

    def test_no_silent_scope_decision_in_artifacts(self):
        dl = load("phase14_5a_operator_decision_ledger.json")
        scope = [d for d in dl["decisions"] if "scope" in d["decision_name"].lower()]
        for s in scope:
            self.assertEqual(s["status"], "pending")

    def test_no_autonomous_execution_without_boundary(self):
        rg = load("phase14_5a_13_layer_readiness_gate_report.json")
        self.assertFalse(rg["gates"]["approved_execution_boundary_exists"])
        self.assertFalse(rg["gates"]["ready_for_autonomous_work_packet_execution"])


class TestSafety(unittest.TestCase):
    """Safety enforcement tests."""

    def test_no_source_mutation(self):
        ps = load("phase14_5a_policy_safety_proof.json")
        src = [ua for ua in ps["unsafe_actions"] if "source code" in ua["action"].lower()]
        self.assertTrue(all(ua["status"] == "BLOCKED" for ua in src))

    def test_no_github_writes(self):
        ps = load("phase14_5a_policy_safety_proof.json")
        gh = [ua for ua in ps["unsafe_actions"] if "GitHub" in ua["action"]]
        self.assertTrue(all(ua["status"] == "BLOCKED" for ua in gh))

    def test_no_windows_writes(self):
        ps = load("phase14_5a_policy_safety_proof.json")
        win = [ua for ua in ps["unsafe_actions"] if "Windows" in ua["action"]]
        self.assertTrue(all(ua["status"] == "BLOCKED" for ua in win))

    def test_no_deployment(self):
        ps = load("phase14_5a_policy_safety_proof.json")
        dep = [ua for ua in ps["unsafe_actions"] if "Deploying" in ua["action"]]
        self.assertTrue(all(ua["status"] == "BLOCKED" for ua in dep))

    def test_no_stale_firebase_canonization(self):
        ps = load("phase14_5a_policy_safety_proof.json")
        fb = [ua for ua in ps["unsafe_actions"] if "Firebase" in ua["action"]]
        self.assertTrue(all(ua["status"] == "DENIED" for ua in fb))

    def test_no_product_collapse(self):
        ps = load("phase14_5a_policy_safety_proof.json")
        coll = [ua for ua in ps["unsafe_actions"] if "Collapsing" in ua["action"]]
        self.assertTrue(all(ua["status"] == "DENIED" for ua in coll))

    def test_no_hardcoded_projection_names(self):
        for f in os.listdir(DATA_DIR):
            if not f.startswith("phase14_5a_"):
                continue
            content = open(os.path.join(DATA_DIR, f)).read()
            self.assertNotIn("EntrepreneurOS", content, f"{f} contains hardcoded EntrepreneurOS")

    def test_no_fake_data(self):
        for f in os.listdir(DATA_DIR):
            if not f.startswith("phase14_5a_") or not f.endswith(".json"):
                continue
            d = json.load(open(os.path.join(DATA_DIR, f)))
            self.assertIn("phase", d)
            self.assertEqual(d["phase"], "14.5A")


class TestArtifactCompleteness(unittest.TestCase):
    """Verify all required artifacts exist."""

    REQUIRED = [
        "phase14_5a_preflight.json",
        "phase14_5a_eos_13_layer_production_stack.json",
        "phase14_5a_creatoros_13_layer_production_stack.json",
        "phase14_5a_lyfeos_13_layer_production_stack.json",
        "phase14_5a_umh_13_layer_production_stack.json",
        "phase14_5a_os_platform_standard_v2_13_layer_defaults.json",
        "phase14_5a_umh_13_layer_integration_boundary.json",
        "phase14_5a_intent_extrapolation.json",
        "phase14_5a_technical_grounding.json",
        "phase14_5a_operator_question_ledger.json",
        "phase14_5a_contradiction_ledger.json",
        "phase14_5a_clarification_ledger.json",
        "phase14_5a_operator_decision_ledger.json",
        "phase14_5a_13_layer_readiness_gate_report.json",
        "phase14_5a_updated_work_packet_tree.json",
        "phase14_5a_policy_safety_proof.json",
        "phase14_5a_test_gate_results.json",
    ]

    def test_all_required_artifacts_exist(self):
        for f in self.REQUIRED:
            path = os.path.join(DATA_DIR, f)
            self.assertTrue(os.path.exists(path), f"Missing: {f}")

    def test_all_artifacts_valid_json(self):
        for f in self.REQUIRED:
            path = os.path.join(DATA_DIR, f)
            if os.path.exists(path):
                with open(path) as fp:
                    d = json.load(fp)
                self.assertIsInstance(d, dict, f"{f} is not a dict")


if __name__ == "__main__":
    unittest.main()
