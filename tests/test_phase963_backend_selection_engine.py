"""Tests for runtime/substrate/backend_selection_engine.py (Phase 96.3)."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest

from runtime.substrate.backend_registry_contracts import (
    BackendCategory,
    BackendImplementationType,
    BackendProfile,
    BackendStatus,
)
from runtime.substrate.backend_selection_engine import (
    SelectionResult,
    SelectionTask,
    detect_when_backend_is_interface_only,
    detect_when_backend_is_true_fallback,
    filter_backends_by_policy,
    rank_backends_for_task,
    select_best_backend,
)


def _make_profile(
    backend_id: str,
    category: BackendCategory,
    impl_type: BackendImplementationType,
    status: BackendStatus = BackendStatus.UNKNOWN,
    independence: str = "",
) -> BackendProfile:
    return BackendProfile(
        backend_id=backend_id,
        category=category,
        implementation_type=impl_type,
        current_status=status,
        independence_level=independence,
    )


class TestDetectInterfaceOnly(unittest.TestCase):
    def test_cli_interface_wrapper_is_interface_only(self) -> None:
        p = _make_profile(
            "cli-wrap",
            BackendCategory.CLI,
            BackendImplementationType.CLI_INTERFACE_WRAPPER,
        )
        self.assertTrue(detect_when_backend_is_interface_only(p))

    def test_mcp_interface_wrapper_is_interface_only(self) -> None:
        p = _make_profile(
            "mcp-wrap",
            BackendCategory.MCP,
            BackendImplementationType.MCP_INTERFACE_WRAPPER,
        )
        self.assertTrue(detect_when_backend_is_interface_only(p))

    def test_internal_api_extractor_is_not_interface_only(self) -> None:
        p = _make_profile(
            "api-ext",
            BackendCategory.API,
            BackendImplementationType.INTERNAL_API_EXTRACTOR,
        )
        self.assertFalse(detect_when_backend_is_interface_only(p))


class TestDetectTrueFallback(unittest.TestCase):
    def test_interface_only_is_not_true_fallback(self) -> None:
        p = _make_profile(
            "cli-wrap",
            BackendCategory.CLI,
            BackendImplementationType.CLI_INTERFACE_WRAPPER,
            independence="level_0_interface_wrapper",
        )
        self.assertFalse(detect_when_backend_is_true_fallback(p))

    def test_non_interface_with_independence_is_true_fallback(self) -> None:
        p = _make_profile(
            "sdk-ext",
            BackendCategory.SDK,
            BackendImplementationType.OFFICIAL_SDK,
            independence="level_1",
        )
        self.assertTrue(detect_when_backend_is_true_fallback(p))


class TestFilterBackendsByPolicy(unittest.TestCase):
    def test_excludes_blocked_backends(self) -> None:
        blocked = _make_profile(
            "blocked-1",
            BackendCategory.BROWSER_AUTOMATION,
            BackendImplementationType.MCP_BROWSER_AUTOMATION,
            status=BackendStatus.BLOCKED,
        )
        good = _make_profile(
            "api-1",
            BackendCategory.API,
            BackendImplementationType.INTERNAL_API_EXTRACTOR,
            status=BackendStatus.COMPLETE,
        )
        task = SelectionTask(task_type="ingest")
        result = filter_backends_by_policy(task, [blocked, good])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].backend_id, "api-1")

    def test_excludes_interface_only_when_require_independence(self) -> None:
        wrapper = _make_profile(
            "cli-wrap",
            BackendCategory.CLI,
            BackendImplementationType.CLI_INTERFACE_WRAPPER,
            status=BackendStatus.COMPLETE,
            independence="level_0_interface_wrapper",
        )
        independent = _make_profile(
            "sdk-1",
            BackendCategory.SDK,
            BackendImplementationType.OFFICIAL_SDK,
            status=BackendStatus.PARTIAL,
            independence="level_1",
        )
        task = SelectionTask(task_type="fallback", require_independence=True)
        result = filter_backends_by_policy(task, [wrapper, independent])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].backend_id, "sdk-1")


class TestRankBackends(unittest.TestCase):
    def test_complete_backends_ranked_first(self) -> None:
        partial = _make_profile(
            "partial-1",
            BackendCategory.SDK,
            BackendImplementationType.OFFICIAL_SDK,
            status=BackendStatus.PARTIAL,
            independence="level_1",
        )
        complete = _make_profile(
            "complete-1",
            BackendCategory.API,
            BackendImplementationType.INTERNAL_API_EXTRACTOR,
            status=BackendStatus.COMPLETE,
            independence="reference",
        )
        task = SelectionTask(task_type="ingest")
        ranked = rank_backends_for_task(task, [partial, complete])
        self.assertEqual(ranked[0].backend_id, "complete-1")


class TestSelectBestBackend(unittest.TestCase):
    def test_returns_selection_result_with_explanation(self) -> None:
        p = _make_profile(
            "api-1",
            BackendCategory.API,
            BackendImplementationType.INTERNAL_API_EXTRACTOR,
            status=BackendStatus.COMPLETE,
        )
        task = SelectionTask(task_type="ingest")
        result = select_best_backend(task, [p])
        self.assertIsInstance(result, SelectionResult)
        self.assertIsNotNone(result.selected)
        self.assertIn("api-1", result.explanation)

    def test_api_preferred_over_cu_for_production(self) -> None:
        """Backend selection prefers API for production completeness."""
        api = _make_profile(
            "api-prod",
            BackendCategory.API,
            BackendImplementationType.INTERNAL_API_EXTRACTOR,
            status=BackendStatus.COMPLETE,
            independence="reference",
        )
        cu = _make_profile(
            "cu-prod",
            BackendCategory.COMPUTER_USE,
            BackendImplementationType.VISIBLE_GUI_COMPUTER_USE,
            status=BackendStatus.PARTIAL,
            independence="level_4",
        )
        task = SelectionTask(task_type="production_ingest")
        result = select_best_backend(task, [cu, api])
        self.assertIsNotNone(result.selected)
        self.assertEqual(result.selected.backend_id, "api-prod")


if __name__ == "__main__":
    unittest.main()
