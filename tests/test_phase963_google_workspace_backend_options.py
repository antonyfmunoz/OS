"""Tests for eos_ai/substrate/google_workspace_backend_options.py (Phase 96.3)."""

import sys

sys.path.insert(0, "/opt/OS")

import unittest

from eos_ai.substrate.backend_registry_contracts import BackendStatus
from eos_ai.substrate.google_workspace_backend_options import (
    build_google_workspace_backend_options,
    get_candidate_backends,
    get_complete_backends,
)


class TestBuildOptions(unittest.TestCase):
    def test_returns_20_options(self) -> None:
        options = build_google_workspace_backend_options()
        self.assertEqual(len(options), 20)

    def test_option_1_api_tab_aware_is_complete(self) -> None:
        options = build_google_workspace_backend_options()
        opt1 = options[0]
        self.assertEqual(opt1.option_id, 1)
        self.assertIn("API tab-aware", opt1.name)
        self.assertEqual(opt1.current_status, BackendStatus.COMPLETE)

    def test_option_3_cli_wrapper_level_0(self) -> None:
        options = build_google_workspace_backend_options()
        opt3 = options[2]
        self.assertEqual(opt3.option_id, 3)
        self.assertEqual(opt3.independence_level, "level_0")

    def test_option_11_native_cu_partial(self) -> None:
        options = build_google_workspace_backend_options()
        opt11 = options[10]
        self.assertEqual(opt11.option_id, 11)
        self.assertIn("Computer Use", opt11.name)
        self.assertEqual(opt11.current_status, BackendStatus.PARTIAL)

    def test_option_12_browser_automation_blocked(self) -> None:
        options = build_google_workspace_backend_options()
        opt12 = options[11]
        self.assertEqual(opt12.option_id, 12)
        self.assertIn("Browser automation", opt12.name)
        self.assertEqual(opt12.current_status, BackendStatus.BLOCKED)


class TestGetCompleteBackends(unittest.TestCase):
    def test_only_complete(self) -> None:
        complete = get_complete_backends()
        for opt in complete:
            self.assertEqual(opt.current_status, BackendStatus.COMPLETE)
        self.assertTrue(len(complete) > 0)


class TestGetCandidateBackends(unittest.TestCase):
    def test_excludes_blocked_and_complete(self) -> None:
        candidates = get_candidate_backends()
        for opt in candidates:
            self.assertNotEqual(opt.current_status, BackendStatus.BLOCKED)
            self.assertNotEqual(opt.current_status, BackendStatus.COMPLETE)


if __name__ == "__main__":
    unittest.main()
