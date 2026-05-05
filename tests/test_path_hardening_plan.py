"""Tests for Path Hardening Plan.

Validates that work orders are created for immature paths
with correct hardening steps and blocker tracking.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.full_path_maturity import (
    AdapterPathMaturityDecision,
    AdapterPathSnapshot,
    PathDeclarationStatus,
    evaluate_path_maturity,
)
from core.adapter_package_manager.path_hardening_plan import (
    PathHardeningWorkOrder,
    build_path_hardening_plan_report,
    create_hardening_plan_for_package,
    create_hardening_work_order,
    prioritize_hardening_work_orders,
)


def _partial_decision(path_name: str, **overrides) -> AdapterPathMaturityDecision:
    defaults = dict(
        package_id="pkg",
        path_id=path_name.lower().replace(" ", "_"),
        path_name=path_name,
        current_status="partial",
        current_maturity_percent=14.3,
        is_declared_package_path=True,
        hardening_required=True,
        gaps_to_100=["missing current_status_complete", "missing has_tests"],
    )
    defaults.update(overrides)
    return AdapterPathMaturityDecision(**defaults)


class TestPartialPathCreatesWorkOrder(unittest.TestCase):
    def test_partial_path_creates_work_order(self):
        d = _partial_decision("API path")
        wo = create_hardening_work_order(d)
        self.assertTrue(wo.work_order_id)
        self.assertEqual(wo.target_status, "complete")

    def test_blocked_path_creates_blocker_order(self):
        d = _partial_decision("Blocked path", blockers=["infrastructure not available"])
        wo = create_hardening_work_order(d)
        self.assertFalse(wo.can_be_done_now)
        self.assertIn("infrastructure not available", wo.blockers)


class TestRequiresApproval(unittest.TestCase):
    def test_requires_approval_included(self):
        d = _partial_decision(
            "Browser automation",
            required_approval="founder_or_security_approval",
        )
        wo = create_hardening_work_order(d)
        self.assertIn("founder_or_security_approval", wo.required_approvals)
        self.assertFalse(wo.can_be_done_now)


class TestCUHardening(unittest.TestCase):
    def test_cu_hardening_includes_tab_steps(self):
        d = _partial_decision("Native Computer Use")
        wo = create_hardening_work_order(d)
        steps = wo.required_validation
        self.assertIn("mature UI tab detection", steps)
        self.assertIn("mature tab navigation", steps)
        self.assertIn("mature body extraction", steps)
        self.assertIn("validate against API parity", steps)
        self.assertFalse(wo.can_be_done_now)


class TestMCPHardening(unittest.TestCase):
    def test_mcp_hardening_includes_discovery(self):
        d = _partial_decision("MCP API connector")
        wo = create_hardening_work_order(d)
        steps = wo.required_validation
        self.assertIn("discover available MCP tools", steps)
        self.assertIn("evaluate Google Docs tab support", steps)
        self.assertIn("run parity tests", steps)


class TestCLIDirectHardening(unittest.TestCase):
    def test_cli_direct_includes_implementation(self):
        d = _partial_decision("CLI direct protocol")
        wo = create_hardening_work_order(d)
        steps = wo.required_validation
        self.assertIn("implement direct REST/curl path or standalone CLI", steps)
        self.assertIn("prove includeTabsContent=true", steps)
        self.assertIn("run parity tests", steps)


class TestLocalExportHardening(unittest.TestCase):
    def test_local_export_includes_approval(self):
        d = _partial_decision("Local export/archive parser")
        wo = create_hardening_work_order(d)
        steps = wo.required_validation
        self.assertIn("requires export approval", steps)
        self.assertIn("prove exported format preserves tabs or mark unsupported", steps)
        self.assertFalse(wo.can_be_done_now)


class TestPrioritization(unittest.TestCase):
    def test_doable_now_comes_first(self):
        d1 = _partial_decision("SDK path")
        d2 = _partial_decision("Native Computer Use")
        wo1 = create_hardening_work_order(d1)
        wo2 = create_hardening_work_order(d2)
        prioritized = prioritize_hardening_work_orders([wo2, wo1])
        doable = [wo for wo in prioritized if wo.can_be_done_now]
        blocked = [wo for wo in prioritized if not wo.can_be_done_now]
        self.assertTrue(doable[0].estimated_sequence < blocked[0].estimated_sequence)

    def test_plan_report_structure(self):
        d1 = _partial_decision("API path")
        wo = create_hardening_work_order(d1)
        report = build_path_hardening_plan_report([wo])
        self.assertIn("total_work_orders", report)
        self.assertIn("doable_now", report)
        self.assertIn("blocked", report)

    def test_package_hardening_plan(self):
        decisions = [
            _partial_decision("API path"),
            _partial_decision("Native Computer Use"),
        ]
        work_orders = create_hardening_plan_for_package("pkg", decisions)
        self.assertEqual(len(work_orders), 2)
        for wo in work_orders:
            self.assertGreater(wo.estimated_sequence, 0)


if __name__ == "__main__":
    unittest.main()
