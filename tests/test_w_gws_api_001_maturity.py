"""Tests for W-GWS-API-001 Maturity Gate.

Validates the 10-check maturity evaluation, failure modes,
100% achievement, and full GWS package behavior with CU partial.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.google_workspace_api_adapter_path import (
    W_GWS_API_001_PATH_ID,
)
from core.adapter_package_manager.google_workspace_api_maturity import (
    W_GWS_API_001_MaturityCheck,
    W_GWS_API_001_MaturityDecision,
    build_w_gws_api_001_gap_report,
    build_w_gws_api_001_maturity_decision,
    evaluate_w_gws_api_001_maturity,
    google_workspace_package_is_fully_mature_with_cu_partial,
    w_gws_api_001_is_100_percent_mature,
)


class TestMaturityGate(unittest.TestCase):
    def test_decision_builds(self) -> None:
        decision = evaluate_w_gws_api_001_maturity()
        self.assertIsInstance(decision, W_GWS_API_001_MaturityDecision)

    def test_decision_path_id(self) -> None:
        decision = evaluate_w_gws_api_001_maturity()
        self.assertEqual(decision.path_id, W_GWS_API_001_PATH_ID)

    def test_all_defaults_pass(self) -> None:
        decision = evaluate_w_gws_api_001_maturity()
        self.assertTrue(decision.all_passed)
        self.assertTrue(decision.is_100_percent_mature)
        self.assertTrue(decision.is_execution_ready)
        self.assertEqual(decision.current_maturity_percent, 100.0)
        self.assertEqual(decision.gaps_to_100, [])

    def test_has_10_checks(self) -> None:
        decision = evaluate_w_gws_api_001_maturity()
        self.assertEqual(len(decision.checks), 10)

    def test_check_names(self) -> None:
        decision = evaluate_w_gws_api_001_maturity()
        names = [c.check_name for c in decision.checks]
        expected = [
            "path_exists",
            "path_declared",
            "current_status_complete",
            "has_auth_method",
            "governance_policy_passes",
            "contract_mapping_passes",
            "tool_mastery_pack_present",
            "tests_present",
            "first_tab_only_rejected",
            "w0_001_coverage_contract",
        ]
        self.assertEqual(names, expected)

    def test_fails_without_tool_mastery(self) -> None:
        decision = evaluate_w_gws_api_001_maturity(has_tool_mastery_pack=False)
        self.assertFalse(decision.all_passed)
        self.assertFalse(decision.is_100_percent_mature)
        self.assertIn("tool_mastery_pack_present", decision.gaps_to_100)

    def test_fails_without_contract_mapping(self) -> None:
        decision = evaluate_w_gws_api_001_maturity(has_contract_mapping=False)
        self.assertFalse(decision.all_passed)
        self.assertIn("contract_mapping_passes", decision.gaps_to_100)

    def test_fails_without_governance(self) -> None:
        decision = evaluate_w_gws_api_001_maturity(has_governance=False)
        self.assertFalse(decision.all_passed)
        self.assertIn("governance_policy_passes", decision.gaps_to_100)

    def test_fails_without_tests(self) -> None:
        decision = evaluate_w_gws_api_001_maturity(has_tests=False)
        self.assertFalse(decision.all_passed)
        self.assertIn("tests_present", decision.gaps_to_100)

    def test_fails_without_auth(self) -> None:
        decision = evaluate_w_gws_api_001_maturity(has_auth=False)
        self.assertFalse(decision.all_passed)
        self.assertIn("has_auth_method", decision.gaps_to_100)

    def test_fails_if_first_tab_only_allowed(self) -> None:
        decision = evaluate_w_gws_api_001_maturity(
            first_tab_only_allowed=True
        )
        self.assertFalse(decision.all_passed)
        self.assertIn("first_tab_only_rejected", decision.gaps_to_100)

    def test_fails_without_coverage_contract(self) -> None:
        decision = evaluate_w_gws_api_001_maturity(
            has_w0_001_coverage_contract=False
        )
        self.assertFalse(decision.all_passed)
        self.assertIn("w0_001_coverage_contract", decision.gaps_to_100)

    def test_maturity_percent_calculation(self) -> None:
        decision = evaluate_w_gws_api_001_maturity(
            has_tool_mastery_pack=False,
            has_tests=False,
        )
        self.assertEqual(decision.current_maturity_percent, 80.0)
        self.assertEqual(len(decision.gaps_to_100), 2)

    def test_convenience_function_100_percent(self) -> None:
        self.assertTrue(w_gws_api_001_is_100_percent_mature())

    def test_build_decision_convenience(self) -> None:
        decision = build_w_gws_api_001_maturity_decision()
        self.assertIsInstance(decision, W_GWS_API_001_MaturityDecision)
        self.assertTrue(decision.is_100_percent_mature)

    def test_gap_report(self) -> None:
        report = build_w_gws_api_001_gap_report()
        self.assertEqual(report["path_id"], "W-GWS-API-001")
        self.assertTrue(report["is_100_percent"])
        self.assertEqual(report["current_maturity"], 100.0)
        self.assertEqual(report["gaps"], [])
        self.assertEqual(len(report["checks"]), 10)

    def test_gap_report_with_failures(self) -> None:
        decision = evaluate_w_gws_api_001_maturity(has_governance=False)
        report = {
            "path_id": decision.path_id,
            "is_100_percent": decision.is_100_percent_mature,
            "gaps": decision.gaps_to_100,
        }
        self.assertFalse(report["is_100_percent"])
        self.assertIn("governance_policy_passes", report["gaps"])

    def test_check_to_dict(self) -> None:
        check = W_GWS_API_001_MaturityCheck("test_check", True, "reason")
        d = check.to_dict()
        self.assertEqual(d["check_name"], "test_check")
        self.assertTrue(d["passed"])
        self.assertEqual(d["reason"], "reason")

    def test_decision_to_dict(self) -> None:
        decision = evaluate_w_gws_api_001_maturity()
        d = decision.to_dict()
        self.assertEqual(d["path_id"], "W-GWS-API-001")
        self.assertTrue(d["is_100_percent_mature"])
        self.assertTrue(d["is_execution_ready"])
        self.assertEqual(len(d["checks"]), 10)


class TestFullGWSPackageWithCUPartial(unittest.TestCase):
    def test_full_gws_not_mature_with_cu_partial(self) -> None:
        result = google_workspace_package_is_fully_mature_with_cu_partial()
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
