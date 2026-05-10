"""Tests for Package Set Contracts.

Validates package set construction, required member tracking,
API_READY vs FULL_READY distinction, and memory review blocking.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.package_set_contracts import (
    PackageSet,
    PackageSetMember,
    PackageSetStatus,
    build_package_set,
    package_set_all_required_members_mature,
    package_set_api_ready,
    package_set_blocks_memory_review,
    package_set_cu_ready,
    summarize_package_set,
)


def _api_member(mature: bool = True) -> PackageSetMember:
    return PackageSetMember(
        package_id="API-001",
        role="service_api",
        service_name="TestAPI",
        required_for_test=True,
        current_maturity_percent=100.0 if mature else 0.0,
    )


def _cu_member(mature: bool = False) -> PackageSetMember:
    return PackageSetMember(
        package_id="CU-001",
        role="service_cu",
        service_name="TestCU",
        required_for_test=True,
        current_maturity_percent=100.0 if mature else 0.0,
    )


class TestPackageSetContracts(unittest.TestCase):
    def test_package_set_builds(self) -> None:
        ps = build_package_set("PS-001", "Test Set", "family")
        self.assertIsInstance(ps, PackageSet)

    def test_package_set_serializes(self) -> None:
        ps = build_package_set("PS-001", "Test Set", "family")
        d = ps.to_dict()
        self.assertEqual(d["package_set_id"], "PS-001")

    def test_all_mature_when_all_100(self) -> None:
        ps = build_package_set(
            "PS-001",
            "Test",
            "family",
            included_packages=[_api_member(True), _cu_member(True)],
        )
        self.assertTrue(package_set_all_required_members_mature(ps))

    def test_not_all_mature_when_cu_partial(self) -> None:
        ps = build_package_set(
            "PS-001",
            "Test",
            "family",
            included_packages=[_api_member(True), _cu_member(False)],
        )
        self.assertFalse(package_set_all_required_members_mature(ps))

    def test_api_ready_when_api_mature(self) -> None:
        ps = build_package_set(
            "PS-001",
            "Test",
            "family",
            included_packages=[_api_member(True), _cu_member(False)],
        )
        self.assertTrue(package_set_api_ready(ps))

    def test_cu_not_ready_when_cu_partial(self) -> None:
        ps = build_package_set(
            "PS-001",
            "Test",
            "family",
            included_packages=[_api_member(True), _cu_member(False)],
        )
        self.assertFalse(package_set_cu_ready(ps))

    def test_status_api_ready(self) -> None:
        ps = build_package_set(
            "PS-001",
            "Test",
            "family",
            included_packages=[_api_member(True), _cu_member(False)],
        )
        self.assertEqual(ps.current_status, PackageSetStatus.API_READY)

    def test_status_ready_when_all_mature(self) -> None:
        ps = build_package_set(
            "PS-001",
            "Test",
            "family",
            included_packages=[_api_member(True), _cu_member(True)],
        )
        self.assertEqual(ps.current_status, PackageSetStatus.READY)

    def test_status_not_ready_when_empty(self) -> None:
        ps = build_package_set("PS-001", "Test", "family")
        self.assertEqual(ps.current_status, PackageSetStatus.NOT_READY)

    def test_blocks_memory_review_when_cu_incomplete(self) -> None:
        ps = build_package_set(
            "PS-001",
            "Test",
            "family",
            included_packages=[_api_member(True), _cu_member(False)],
        )
        self.assertTrue(package_set_blocks_memory_review(ps))

    def test_does_not_block_memory_when_all_mature(self) -> None:
        ps = build_package_set(
            "PS-001",
            "Test",
            "family",
            included_packages=[_api_member(True), _cu_member(True)],
        )
        self.assertFalse(package_set_blocks_memory_review(ps))

    def test_summarize_package_set(self) -> None:
        ps = build_package_set(
            "PS-001",
            "Test",
            "family",
            included_packages=[_api_member(True), _cu_member(False)],
        )
        s = summarize_package_set(ps)
        self.assertEqual(s["package_set_id"], "PS-001")
        self.assertTrue(s["api_ready"])
        self.assertFalse(s["cu_ready"])
        self.assertFalse(s["all_ready"])

    def test_blockers_list(self) -> None:
        ps = build_package_set(
            "PS-001",
            "Test",
            "family",
            included_packages=[_api_member(True), _cu_member(False)],
        )
        self.assertTrue(len(ps.blockers) > 0)
        self.assertTrue(any("CU-001" in b for b in ps.blockers))

    def test_maturity_summary(self) -> None:
        ps = build_package_set(
            "PS-001",
            "Test",
            "family",
            included_packages=[_api_member(True), _cu_member(False)],
        )
        self.assertEqual(ps.maturity_summary["total_members"], 2)
        self.assertEqual(ps.maturity_summary["mature_members"], 1)
        self.assertEqual(ps.maturity_summary["percent"], 50.0)

    def test_member_to_dict(self) -> None:
        m = _api_member(True)
        d = m.to_dict()
        self.assertEqual(d["package_id"], "API-001")
        self.assertTrue(d["required_for_test"])

    def test_status_enum_values(self) -> None:
        self.assertEqual(PackageSetStatus.API_READY.value, "api_ready")
        self.assertEqual(PackageSetStatus.CU_BLOCKED.value, "cu_blocked")
        self.assertEqual(PackageSetStatus.READY.value, "ready")

    def test_excluded_candidates_tracked(self) -> None:
        ps = build_package_set(
            "PS-001",
            "Test",
            "family",
            excluded_future_candidates=["Gmail", "Sheets"],
        )
        self.assertIn("Gmail", ps.excluded_future_candidates)
        self.assertIn("Sheets", ps.excluded_future_candidates)


if __name__ == "__main__":
    unittest.main()
