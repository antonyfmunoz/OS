"""Tests for Adapter Family Contracts.

Validates that Adapter Families are not monolithic, declared services
are distinguishable from future candidates, and future candidates
do not block the current test.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.adapter_family_contracts import (
    AdapterFamily,
    AdapterFamilyStatus,
    ServiceAdapterPackageRef,
    ServicePackageStatus,
    adapter_family_is_monolithic,
    build_adapter_family,
    family_can_be_fully_mature,
    list_declared_services,
    list_future_candidate_services,
    service_blocks_current_test,
)


class TestAdapterFamilyContracts(unittest.TestCase):
    def test_family_builds(self) -> None:
        family = build_adapter_family(
            family_id="test", family_name="Test", core_package_id="CORE-001"
        )
        self.assertIsInstance(family, AdapterFamily)

    def test_family_serializes(self) -> None:
        family = build_adapter_family(
            family_id="test", family_name="Test", core_package_id="CORE-001"
        )
        d = family.to_dict()
        self.assertEqual(d["family_id"], "test")
        self.assertEqual(d["core_package_id"], "CORE-001")

    def test_family_is_not_monolithic(self) -> None:
        family = build_adapter_family(
            family_id="test", family_name="Test", core_package_id="CORE-001"
        )
        self.assertFalse(adapter_family_is_monolithic(family))

    def test_declared_services_distinguishable(self) -> None:
        declared = ServiceAdapterPackageRef(
            package_id="SVC-001",
            service_name="Svc",
            declaration_status=ServicePackageStatus.DECLARED,
        )
        candidate = ServiceAdapterPackageRef(
            package_id="SVC-002",
            service_name="Svc2",
            declaration_status=ServicePackageStatus.FUTURE_CANDIDATE,
        )
        family = build_adapter_family(
            family_id="test",
            family_name="Test",
            core_package_id="CORE-001",
            service_packages=[declared],
            future_service_candidates=[candidate],
        )
        self.assertEqual(len(list_declared_services(family)), 1)
        self.assertEqual(list_declared_services(family)[0].package_id, "SVC-001")
        self.assertEqual(len(list_future_candidate_services(family)), 1)
        self.assertEqual(
            list_future_candidate_services(family)[0].package_id, "SVC-002"
        )

    def test_future_candidates_do_not_block(self) -> None:
        candidate = ServiceAdapterPackageRef(
            package_id="SVC-002",
            service_name="Svc2",
            declaration_status=ServicePackageStatus.FUTURE_CANDIDATE,
            blocks_current_test=False,
        )
        self.assertFalse(service_blocks_current_test(candidate))

    def test_declared_service_can_block(self) -> None:
        declared = ServiceAdapterPackageRef(
            package_id="SVC-001",
            service_name="Svc",
            declaration_status=ServicePackageStatus.DECLARED,
            blocks_current_test=True,
        )
        self.assertTrue(service_blocks_current_test(declared))

    def test_family_can_be_mature_when_all_declared_at_100(self) -> None:
        svc = ServiceAdapterPackageRef(
            package_id="SVC-001",
            service_name="Svc",
            declaration_status=ServicePackageStatus.DECLARED,
            current_maturity_percent=100.0,
        )
        family = build_adapter_family(
            family_id="test",
            family_name="Test",
            core_package_id="CORE-001",
            service_packages=[svc],
        )
        self.assertTrue(family_can_be_fully_mature(family))

    def test_family_cannot_be_mature_when_declared_partial(self) -> None:
        svc = ServiceAdapterPackageRef(
            package_id="SVC-001",
            service_name="Svc",
            declaration_status=ServicePackageStatus.DECLARED,
            current_maturity_percent=50.0,
        )
        family = build_adapter_family(
            family_id="test",
            family_name="Test",
            core_package_id="CORE-001",
            service_packages=[svc],
        )
        self.assertFalse(family_can_be_fully_mature(family))

    def test_family_without_services_cannot_be_mature(self) -> None:
        family = build_adapter_family(
            family_id="test", family_name="Test", core_package_id="CORE-001"
        )
        self.assertFalse(family_can_be_fully_mature(family))

    def test_family_status_enum(self) -> None:
        self.assertEqual(AdapterFamilyStatus.DRAFT.value, "draft")
        self.assertEqual(AdapterFamilyStatus.FULLY_MATURE.value, "fully_mature")

    def test_service_package_status_enum(self) -> None:
        self.assertEqual(ServicePackageStatus.DECLARED.value, "declared")
        self.assertEqual(
            ServicePackageStatus.FUTURE_CANDIDATE.value, "future_candidate"
        )

    def test_service_ref_to_dict(self) -> None:
        ref = ServiceAdapterPackageRef(
            package_id="SVC-001", service_name="Svc"
        )
        d = ref.to_dict()
        self.assertEqual(d["package_id"], "SVC-001")
        self.assertEqual(d["target_maturity_percent"], 100.0)


if __name__ == "__main__":
    unittest.main()
