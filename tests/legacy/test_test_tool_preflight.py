"""Tests for Test Tool Preflight.

Validates W0-001 tool inventory, preflight blocking, and
readiness reporting.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.maturity_enforcement import (
    AdapterPackageSnapshot,
)
from core.adapter_package_manager.test_tool_preflight import (
    TestToolPreflightStatus,
    build_w0_001_required_tool_inventory,
    preflight_blocks_execution,
    run_test_tool_preflight,
    summarize_test_tool_preflight,
)


def _snap(tool_name: str, **overrides) -> AdapterPackageSnapshot:
    defaults = dict(
        package_id=f"pkg_{tool_name}",
        tool_name=tool_name,
        has_adapter_package=True,
        has_tool_mastery_pack=True,
        tool_mastery_fresh=True,
        tool_mastery_complete=True,
        has_auth_profile=True,
        has_governance_policy=True,
        has_no_secret_policy=True,
        has_contract_mapping=True,
        has_tests=True,
        access_path_id="primary",
        access_path_status="complete",
    )
    defaults.update(overrides)
    return AdapterPackageSnapshot(**defaults)


class TestW0001Inventory(unittest.TestCase):
    def test_inventory_includes_google_workspace(self):
        inv = build_w0_001_required_tool_inventory()
        names = [t.tool_name for t in inv]
        self.assertIn("google_workspace", names)

    def test_inventory_includes_google_docs(self):
        inv = build_w0_001_required_tool_inventory()
        names = [t.tool_name for t in inv]
        self.assertIn("google_docs", names)

    def test_inventory_includes_google_drive(self):
        inv = build_w0_001_required_tool_inventory()
        names = [t.tool_name for t in inv]
        self.assertIn("google_drive", names)

    def test_inventory_includes_build_tools(self):
        inv = build_w0_001_required_tool_inventory()
        names = [t.tool_name for t in inv]
        self.assertIn("claude_code", names)
        self.assertIn("shell_bash", names)
        self.assertIn("python", names)
        self.assertIn("pytest", names)

    def test_git_only_when_commit_requested(self):
        inv = build_w0_001_required_tool_inventory()
        git_req = [t for t in inv if t.tool_name == "git"][0]
        self.assertIn("only if commit requested", git_req.reason_needed)


class TestPreflightBlocking(unittest.TestCase):
    def test_preflight_blocks_when_required_package_missing(self):
        report = run_test_tool_preflight("W0-001 test", {})
        self.assertTrue(preflight_blocks_execution(report))
        self.assertGreater(len(report.missing_packages), 0)

    def test_preflight_blocks_when_access_path_partial(self):
        lookup = {}
        inv = build_w0_001_required_tool_inventory()
        for t in inv:
            lookup[t.tool_name] = _snap(t.tool_name, access_path_status="partial")
        report = run_test_tool_preflight("W0-001 test", lookup)
        self.assertTrue(preflight_blocks_execution(report))

    def test_preflight_ready_when_all_execution_ready(self):
        lookup = {}
        inv = build_w0_001_required_tool_inventory()
        for t in inv:
            lookup[t.tool_name] = _snap(t.tool_name)
        report = run_test_tool_preflight("W0-001 test", lookup)
        self.assertFalse(preflight_blocks_execution(report))
        self.assertEqual(report.final_status, TestToolPreflightStatus.READY)


class TestPreflightSummary(unittest.TestCase):
    def test_summarize_missing(self):
        report = run_test_tool_preflight("W0-001 test", {})
        summary = summarize_test_tool_preflight(report)
        self.assertIn("Missing packages", summary)
        self.assertIn("Blocked", summary)


if __name__ == "__main__":
    unittest.main()
