"""Tests for Full-Path Adapter Package Maturity Gate.

Validates that every declared path must be 100% mature for full
package maturity, and that candidates don't block maturity.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.full_path_maturity import (
    AdapterPathMaturityDecision,
    AdapterPathSnapshot,
    FullAdapterPackageMaturityDecision,
    PathDeclarationStatus,
    evaluate_full_adapter_package_maturity,
    evaluate_path_maturity,
    path_blocks_full_package_maturity,
    path_counts_toward_package_maturity,
    reject_fake_complete_path,
)


def _complete_path(path_id: str = "api", declaration: PathDeclarationStatus = PathDeclarationStatus.DECLARED) -> AdapterPathSnapshot:
    return AdapterPathSnapshot(
        path_id=path_id,
        path_name=f"{path_id} path",
        declaration_status=declaration,
        current_status="complete",
        has_tool_mastery=True,
        has_auth=True,
        has_governance=True,
        has_tests=True,
        has_contract_mapping=True,
    )


def _partial_path(path_id: str = "cu", declaration: PathDeclarationStatus = PathDeclarationStatus.DECLARED) -> AdapterPathSnapshot:
    return AdapterPathSnapshot(
        path_id=path_id,
        path_name=f"{path_id} path",
        declaration_status=declaration,
        current_status="partial",
        has_tool_mastery=True,
    )


class TestAllDeclaredComplete(unittest.TestCase):
    def test_all_declared_paths_complete_passes(self):
        paths = [_complete_path("api"), _complete_path("sdk")]
        d = evaluate_full_adapter_package_maturity("pkg", paths)
        self.assertTrue(d.package_is_100_percent_mature)
        self.assertTrue(d.can_use_for_full_adapter_test)
        self.assertEqual(d.package_current_maturity_percent, 100.0)


class TestPartialDeclaredBlocks(unittest.TestCase):
    def test_complete_api_partial_cu_fails(self):
        paths = [_complete_path("api"), _partial_path("cu")]
        d = evaluate_full_adapter_package_maturity("pkg", paths)
        self.assertFalse(d.package_is_100_percent_mature)
        self.assertFalse(d.can_use_for_full_adapter_test)
        self.assertIn("cu", d.immature_declared_paths)


class TestCandidateDoesNotBlock(unittest.TestCase):
    def test_candidate_path_does_not_block_maturity(self):
        paths = [
            _complete_path("api"),
            _partial_path("mcp", PathDeclarationStatus.FUTURE_CANDIDATE),
        ]
        d = evaluate_full_adapter_package_maturity("pkg", paths)
        self.assertTrue(d.package_is_100_percent_mature)
        self.assertIn("mcp", d.candidate_paths)


class TestDeclaredStatusesBlock(unittest.TestCase):
    def test_declared_unknown_blocks(self):
        snap = AdapterPathSnapshot(
            path_id="cli",
            path_name="CLI path",
            declaration_status=PathDeclarationStatus.DECLARED,
            current_status="unknown",
        )
        d = evaluate_path_maturity(snap, "pkg")
        self.assertTrue(path_blocks_full_package_maturity(d))

    def test_declared_not_implemented_blocks(self):
        snap = AdapterPathSnapshot(
            path_id="cli",
            path_name="CLI path",
            declaration_status=PathDeclarationStatus.DECLARED,
            current_status="not_implemented",
        )
        d = evaluate_path_maturity(snap, "pkg")
        self.assertTrue(path_blocks_full_package_maturity(d))

    def test_declared_requires_approval_blocks(self):
        snap = AdapterPathSnapshot(
            path_id="browser",
            path_name="Browser path",
            declaration_status=PathDeclarationStatus.DECLARED,
            current_status="blocked",
            requires_approval=True,
        )
        d = evaluate_path_maturity(snap, "pkg")
        self.assertTrue(path_blocks_full_package_maturity(d))


class TestFakeCompletePath(unittest.TestCase):
    def test_fake_complete_rejected_with_gaps(self):
        snap = AdapterPathSnapshot(
            path_id="x",
            path_name="X path",
            current_status="complete",
            known_gaps=["tab extraction incomplete"],
        )
        self.assertTrue(reject_fake_complete_path(snap))

    def test_fake_complete_rejected_without_mastery(self):
        snap = AdapterPathSnapshot(
            path_id="x",
            path_name="X path",
            current_status="complete",
            has_tool_mastery=False,
        )
        self.assertTrue(reject_fake_complete_path(snap))

    def test_real_complete_accepted(self):
        snap = _complete_path("api")
        self.assertFalse(reject_fake_complete_path(snap))


class TestFullAdapterTest(unittest.TestCase):
    def test_full_adapter_test_cannot_run_with_immature_declared(self):
        paths = [_complete_path("api"), _partial_path("cu")]
        d = evaluate_full_adapter_package_maturity("pkg", paths)
        self.assertFalse(d.can_use_for_full_adapter_test)

    def test_serialization(self):
        paths = [_complete_path("api")]
        d = evaluate_full_adapter_package_maturity("pkg", paths)
        dd = d.to_dict()
        self.assertIn("package_is_100_percent_mature", dd)
        self.assertIn("can_use_for_full_adapter_test", dd)
        self.assertIn("declared_paths", dd)


if __name__ == "__main__":
    unittest.main()
