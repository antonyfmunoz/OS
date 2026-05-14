"""Tests for Adapter Package Maturity Enforcement.

Validates that immature packages/paths block execution and
that 100% maturity is required for selected-tool execution.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.maturity_enforcement import (
    AdapterExecutionMaturityStatus,
    AdapterExecutionReadinessDecision,
    AdapterPackageSnapshot,
    adapter_execution_blocks,
    adapter_package_has_required_components,
    build_adapter_execution_readiness_report,
    evaluate_adapter_package_execution_readiness,
    known_gaps_affect_capability,
    require_100_percent_maturity,
    selected_access_path_is_complete,
)


def _complete_snap(**overrides) -> AdapterPackageSnapshot:
    defaults = dict(
        package_id="test_pkg",
        tool_name="test_tool",
        has_adapter_package=True,
        has_tool_mastery_pack=True,
        tool_mastery_fresh=True,
        tool_mastery_complete=True,
        has_auth_profile=True,
        has_governance_policy=True,
        has_no_secret_policy=True,
        has_contract_mapping=True,
        has_tests=True,
        access_path_id="api_path",
        access_path_status="complete",
    )
    defaults.update(overrides)
    return AdapterPackageSnapshot(**defaults)


class TestMissingComponents(unittest.TestCase):
    def test_missing_adapter_package_blocks(self):
        snap = _complete_snap(has_adapter_package=False)
        d = evaluate_adapter_package_execution_readiness(snap, "extraction")
        self.assertFalse(d.can_execute)
        self.assertEqual(d.maturity_status, AdapterExecutionMaturityStatus.MISSING_ADAPTER_PACKAGE)

    def test_missing_tool_mastery_pack_blocks(self):
        snap = _complete_snap(has_tool_mastery_pack=False)
        d = evaluate_adapter_package_execution_readiness(snap, "extraction")
        self.assertFalse(d.can_execute)
        self.assertEqual(d.maturity_status, AdapterExecutionMaturityStatus.MISSING_TOOL_MASTERY_PACK)

    def test_stale_tool_mastery_blocks(self):
        snap = _complete_snap(tool_mastery_fresh=False)
        d = evaluate_adapter_package_execution_readiness(snap, "extraction")
        self.assertFalse(d.can_execute)
        self.assertEqual(d.maturity_status, AdapterExecutionMaturityStatus.STALE_TOOL_MASTERY_PACK)

    def test_incomplete_tool_mastery_blocks(self):
        snap = _complete_snap(tool_mastery_complete=False)
        d = evaluate_adapter_package_execution_readiness(snap, "extraction")
        self.assertFalse(d.can_execute)
        self.assertEqual(d.maturity_status, AdapterExecutionMaturityStatus.INCOMPLETE_TOOL_MASTERY_PACK)


class TestAccessPathBlocking(unittest.TestCase):
    def test_partial_access_path_blocks(self):
        snap = _complete_snap(access_path_status="partial")
        d = evaluate_adapter_package_execution_readiness(snap, "extraction")
        self.assertFalse(d.can_execute)
        self.assertEqual(d.maturity_status, AdapterExecutionMaturityStatus.ACCESS_PATH_PARTIAL)

    def test_blocked_access_path_blocks(self):
        snap = _complete_snap(access_path_status="blocked")
        d = evaluate_adapter_package_execution_readiness(snap, "extraction")
        self.assertFalse(d.can_execute)
        self.assertEqual(d.maturity_status, AdapterExecutionMaturityStatus.ACCESS_PATH_BLOCKED)

    def test_not_implemented_access_path_blocks(self):
        snap = _complete_snap(access_path_status="not_implemented")
        d = evaluate_adapter_package_execution_readiness(snap, "extraction")
        self.assertFalse(d.can_execute)
        self.assertEqual(d.maturity_status, AdapterExecutionMaturityStatus.ACCESS_PATH_NOT_IMPLEMENTED)

    def test_unknown_access_path_blocks(self):
        snap = _complete_snap(access_path_status="unknown")
        d = evaluate_adapter_package_execution_readiness(snap, "extraction")
        self.assertFalse(d.can_execute)
        self.assertEqual(d.maturity_status, AdapterExecutionMaturityStatus.ACCESS_PATH_UNKNOWN)


class TestCompletePackage(unittest.TestCase):
    def test_complete_package_allows_execution(self):
        snap = _complete_snap()
        d = evaluate_adapter_package_execution_readiness(snap, "extraction")
        self.assertTrue(d.can_execute)
        self.assertEqual(d.maturity_status, AdapterExecutionMaturityStatus.EXECUTION_READY)
        self.assertEqual(d.current_maturity_percent, 100.0)


class TestKnownGaps(unittest.TestCase):
    def test_known_gap_affecting_capability_blocks(self):
        snap = _complete_snap(
            gaps_affecting_capability=["tab extraction incomplete"]
        )
        d = evaluate_adapter_package_execution_readiness(snap, "extraction")
        self.assertFalse(d.can_execute)
        self.assertEqual(d.maturity_status, AdapterExecutionMaturityStatus.KNOWN_GAPS_AFFECT_EXECUTION)


class TestFounderWaiver(unittest.TestCase):
    def test_founder_waiver_permits_controlled_execution(self):
        snap = _complete_snap(
            has_governance_policy=False,
            has_tests=False,
            founder_waiver=True,
        )
        d = evaluate_adapter_package_execution_readiness(snap, "extraction")
        self.assertTrue(d.can_execute)
        self.assertEqual(d.maturity_status, AdapterExecutionMaturityStatus.WAIVED_BY_FOUNDER)

    def test_founder_waiver_does_not_mark_100_percent(self):
        snap = _complete_snap(
            has_governance_policy=False,
            has_tests=False,
            founder_waiver=True,
        )
        d = evaluate_adapter_package_execution_readiness(snap, "extraction")
        self.assertLess(d.current_maturity_percent, 100.0)


class TestHelpers(unittest.TestCase):
    def test_adapter_execution_blocks(self):
        d = AdapterExecutionReadinessDecision(tool_name="x", can_execute=False)
        self.assertTrue(adapter_execution_blocks(d))

    def test_adapter_execution_does_not_block(self):
        d = AdapterExecutionReadinessDecision(tool_name="x", can_execute=True)
        self.assertFalse(adapter_execution_blocks(d))

    def test_require_100_percent(self):
        d = AdapterExecutionReadinessDecision(tool_name="x", current_maturity_percent=100.0)
        self.assertTrue(require_100_percent_maturity(d))

    def test_require_100_percent_fails_below(self):
        d = AdapterExecutionReadinessDecision(tool_name="x", current_maturity_percent=80.0)
        self.assertFalse(require_100_percent_maturity(d))

    def test_selected_access_path_complete(self):
        self.assertTrue(selected_access_path_is_complete("complete"))
        self.assertFalse(selected_access_path_is_complete("partial"))

    def test_build_report(self):
        d1 = AdapterExecutionReadinessDecision(tool_name="a", can_execute=True)
        d2 = AdapterExecutionReadinessDecision(tool_name="b", can_execute=False)
        report = build_adapter_execution_readiness_report([d1, d2])
        self.assertEqual(report["total"], 2)
        self.assertEqual(report["ready_count"], 1)
        self.assertEqual(report["blocked_count"], 1)
        self.assertFalse(report["all_ready"])

    def test_serialization(self):
        snap = _complete_snap()
        d = evaluate_adapter_package_execution_readiness(snap, "extraction")
        dd = d.to_dict()
        self.assertIn("maturity_status", dd)
        self.assertIn("can_execute", dd)
        self.assertEqual(dd["maturity_status"], "execution_ready")


if __name__ == "__main__":
    unittest.main()
