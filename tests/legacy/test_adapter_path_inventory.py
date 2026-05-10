"""Tests for Adapter Path Inventory.

Validates Google Workspace and W0-001 operational tool inventories,
path classification, and maturity tracking.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.adapter_path_inventory import (
    AdapterPathInventoryItem,
    build_adapter_path_inventory_report,
    classify_declared_vs_candidate_paths,
    inventory_claude_code_paths,
    inventory_google_workspace_paths,
    inventory_w0_001_operational_tools,
)
from core.adapter_package_manager.full_path_maturity import PathDeclarationStatus


class TestGoogleWorkspaceInventory(unittest.TestCase):
    def test_includes_api_path(self):
        inv = inventory_google_workspace_paths()
        names = [i.path_name for i in inv]
        self.assertIn("API tab-aware extractor", names)

    def test_includes_cu_path(self):
        inv = inventory_google_workspace_paths()
        names = [i.path_name for i in inv]
        self.assertIn("Native Computer Use", names)

    def test_includes_sdk_path(self):
        inv = inventory_google_workspace_paths()
        names = [i.path_name for i in inv]
        self.assertIn("SDK tab-aware extractor", names)

    def test_includes_mcp_paths(self):
        inv = inventory_google_workspace_paths()
        names = [i.path_name for i in inv]
        self.assertTrue(any("MCP" in n for n in names))

    def test_includes_browser_automation(self):
        inv = inventory_google_workspace_paths()
        names = [i.path_name for i in inv]
        self.assertIn("Browser automation", names)

    def test_includes_local_export(self):
        inv = inventory_google_workspace_paths()
        names = [i.path_name for i in inv]
        self.assertIn("Local export/archive parser", names)

    def test_all_have_expected_fields(self):
        inv = inventory_google_workspace_paths()
        for item in inv:
            self.assertTrue(item.path_id)
            self.assertTrue(item.path_name)
            self.assertIsInstance(item.declaration_status, PathDeclarationStatus)
            self.assertTrue(item.current_status)
            self.assertEqual(item.target_maturity_percent, 100.0)


class TestW0001OperationalInventory(unittest.TestCase):
    def test_includes_shell_bash(self):
        inv = inventory_w0_001_operational_tools()
        names = [i.path_name for i in inv]
        self.assertIn("Shell/Bash", names)

    def test_includes_python(self):
        inv = inventory_w0_001_operational_tools()
        names = [i.path_name for i in inv]
        self.assertIn("Python runtime", names)

    def test_includes_pytest(self):
        inv = inventory_w0_001_operational_tools()
        names = [i.path_name for i in inv]
        self.assertIn("pytest framework", names)

    def test_includes_git(self):
        inv = inventory_w0_001_operational_tools()
        names = [i.path_name for i in inv]
        self.assertIn("Git VCS", names)

    def test_includes_tmux(self):
        inv = inventory_w0_001_operational_tools()
        names = [i.path_name for i in inv]
        self.assertIn("tmux session manager", names)

    def test_includes_vps(self):
        inv = inventory_w0_001_operational_tools()
        names = [i.path_name for i in inv]
        self.assertIn("VPS/WSL runtime", names)

    def test_claude_code_inventory(self):
        inv = inventory_claude_code_paths()
        self.assertEqual(len(inv), 1)
        self.assertEqual(inv[0].path_name, "Claude Code CLI")


class TestPathClassification(unittest.TestCase):
    def test_distinguishes_declared_from_candidates(self):
        inv = inventory_google_workspace_paths()
        declared, candidates = classify_declared_vs_candidate_paths(inv)
        self.assertGreater(len(declared), 0)
        self.assertGreater(len(candidates), 0)
        for d in declared:
            self.assertEqual(d.declaration_status, PathDeclarationStatus.DECLARED)
        for c in candidates:
            self.assertEqual(c.declaration_status, PathDeclarationStatus.FUTURE_CANDIDATE)

    def test_target_maturity_is_100(self):
        inv = inventory_google_workspace_paths()
        for item in inv:
            self.assertEqual(item.target_maturity_percent, 100.0)

    def test_gaps_present_for_immature_paths(self):
        inv = inventory_google_workspace_paths()
        for item in inv:
            if item.current_maturity_percent < 100.0:
                self.assertGreater(len(item.gaps_to_100), 0, f"{item.path_name} missing gaps")


class TestInventoryReport(unittest.TestCase):
    def test_report_structure(self):
        inv = inventory_google_workspace_paths()
        report = build_adapter_path_inventory_report(inv)
        self.assertIn("total_paths", report)
        self.assertIn("declared_count", report)
        self.assertIn("candidate_count", report)
        self.assertGreater(report["total_paths"], 0)


if __name__ == "__main__":
    unittest.main()
