"""Tests for Adapter Package Readiness.

Validates maturity percentage computation, gap reporting,
and honest state tracking.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.maturity_enforcement import (
    AdapterPackageSnapshot,
)
from core.adapter_package_manager.adapter_package_readiness import (
    build_package_gap_report,
    compute_access_path_maturity_percent,
    compute_package_maturity_percent,
    package_can_be_used_for_capability,
    package_current_state_is_honest,
    package_targets_100_percent,
)


def _snap(**overrides) -> AdapterPackageSnapshot:
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
        access_path_status="complete",
    )
    defaults.update(overrides)
    return AdapterPackageSnapshot(**defaults)


class TestMaturityPercent(unittest.TestCase):
    def test_target_defaults_to_100(self):
        snap = _snap()
        self.assertTrue(package_targets_100_percent(snap))

    def test_complete_package_is_100(self):
        snap = _snap()
        pct = compute_package_maturity_percent(snap, "extraction")
        self.assertEqual(pct, 100.0)

    def test_incomplete_package_below_100(self):
        snap = _snap(has_tests=False, has_governance_policy=False)
        pct = compute_package_maturity_percent(snap, "extraction")
        self.assertLess(pct, 100.0)

    def test_package_below_100_cannot_execute(self):
        snap = _snap(has_tests=False)
        pct = compute_package_maturity_percent(snap, "extraction")
        self.assertLess(pct, 100.0)
        self.assertFalse(package_can_be_used_for_capability(snap, "extraction"))


class TestAccessPathMaturity(unittest.TestCase):
    def test_complete_path_is_100(self):
        self.assertEqual(compute_access_path_maturity_percent("complete"), 100.0)

    def test_partial_path_is_0(self):
        self.assertEqual(compute_access_path_maturity_percent("partial"), 0.0)


class TestGapReport(unittest.TestCase):
    def test_partial_path_requires_gaps(self):
        snap = _snap(access_path_status="partial")
        report = build_package_gap_report(snap, "extraction")
        self.assertGreater(len(report.gaps_to_100), 0)

    def test_complete_package_no_gaps(self):
        snap = _snap()
        report = build_package_gap_report(snap, "extraction")
        self.assertEqual(len(report.gaps_to_100), 0)
        self.assertTrue(report.can_execute)

    def test_report_serialization(self):
        snap = _snap()
        report = build_package_gap_report(snap, "extraction")
        d = report.to_dict()
        self.assertIn("gaps_to_100", d)
        self.assertIn("current_maturity_percent", d)


class TestHonestyCheck(unittest.TestCase):
    def test_honest_state(self):
        snap = _snap()
        self.assertTrue(package_current_state_is_honest(snap, "extraction"))

    def test_honest_incomplete(self):
        snap = _snap(has_tests=False)
        self.assertTrue(package_current_state_is_honest(snap, "extraction"))


class TestCapabilityUsability(unittest.TestCase):
    def test_can_use_complete(self):
        snap = _snap()
        self.assertTrue(package_can_be_used_for_capability(snap, "extraction"))

    def test_cannot_use_partial_path(self):
        snap = _snap(access_path_status="partial")
        self.assertFalse(package_can_be_used_for_capability(snap, "extraction"))

    def test_cannot_use_no_package(self):
        snap = _snap(has_adapter_package=False)
        self.assertFalse(package_can_be_used_for_capability(snap, "extraction"))


if __name__ == "__main__":
    unittest.main()
