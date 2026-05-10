"""Tests for eos_ai/substrate/backend_registry_contracts.py (Phase 96.3)."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest

from eos_ai.substrate.backend_registry_contracts import (
    BackendCategory,
    BackendImplementationType,
    BackendProfile,
    BackendSelectionFactor,
    BackendStatus,
)


class TestBackendCategory(unittest.TestCase):
    def test_has_16_values(self) -> None:
        self.assertEqual(len(BackendCategory), 16)

    def test_all_values_lowercase(self) -> None:
        for member in BackendCategory:
            self.assertEqual(member.value, member.value.lower())


class TestBackendImplementationType(unittest.TestCase):
    def test_has_23_values(self) -> None:
        self.assertEqual(len(BackendImplementationType), 23)


class TestBackendSelectionFactor(unittest.TestCase):
    def test_has_13_values(self) -> None:
        self.assertEqual(len(BackendSelectionFactor), 13)


class TestBackendStatus(unittest.TestCase):
    def test_has_5_values(self) -> None:
        self.assertEqual(len(BackendStatus), 5)

    def test_complete_through_unknown(self) -> None:
        self.assertEqual(BackendStatus.COMPLETE.value, "complete")
        self.assertEqual(BackendStatus.UNKNOWN.value, "unknown")


class TestBackendProfile(unittest.TestCase):
    def test_to_dict_serializes_correctly(self) -> None:
        profile = BackendProfile(
            backend_id="test-api",
            category=BackendCategory.API,
            implementation_type=BackendImplementationType.INTERNAL_API_EXTRACTOR,
            source_type="google_docs",
            supported_capabilities=["read_metadata", "read_body"],
            independence_level="reference",
            current_status=BackendStatus.COMPLETE,
            coverage_contract_status="complete",
            failure_modes=["rate_limit"],
            safety_constraints=["read_only"],
            required_auth_methods=["oauth"],
            required_approvals=[],
            notes="test profile",
        )
        d = profile.to_dict()
        self.assertEqual(d["backend_id"], "test-api")
        self.assertEqual(d["category"], "api")
        self.assertEqual(d["implementation_type"], "internal_api_extractor")
        self.assertEqual(d["source_type"], "google_docs")
        self.assertEqual(d["supported_capabilities"], ["read_metadata", "read_body"])
        self.assertEqual(d["independence_level"], "reference")
        self.assertEqual(d["current_status"], "complete")
        self.assertEqual(d["coverage_contract_status"], "complete")
        self.assertEqual(d["notes"], "test profile")


if __name__ == "__main__":
    unittest.main()
