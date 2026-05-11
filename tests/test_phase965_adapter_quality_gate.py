"""Tests for Phase 96.5 adapter quality gate."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest

from runtime.substrate.adapter_engine_contracts import (
    AdapterProfile,
    AdapterRegistryEntry,
    AdapterSafetyPolicy,
    AdapterType,
    ToolMasteryPack,
)
from runtime.substrate.adapter_quality_gate import (
    adapter_has_docs,
    adapter_has_no_secret_policy,
    adapter_has_required_contracts,
    adapter_has_safety_policy,
    adapter_has_tests,
    adapter_has_tool_mastery,
    adapter_is_promotable,
    evaluate_adapter_quality,
)


def _make_profile(adapter_id: str = "test") -> AdapterProfile:
    return AdapterProfile(adapter_id=adapter_id, adapter_type=AdapterType.API)


def _make_full_entry() -> AdapterRegistryEntry:
    """Entry that passes ALL quality checks."""
    return AdapterRegistryEntry(
        profile=_make_profile("full"),
        safety_policy=AdapterSafetyPolicy(
            adapter_id="full",
            no_secret_exposure=True,
            no_credential_capture=True,
        ),
        tool_mastery=ToolMasteryPack(adapter_id="full", tool_name="Full Tool"),
        has_tests=True,
        has_docs=True,
        has_contract=True,
        has_tool_mastery=True,
    )


class TestIndividualChecks(unittest.TestCase):
    """Tests for individual quality check functions."""

    def test_has_contracts_false(self) -> None:
        entry = AdapterRegistryEntry(profile=_make_profile(), has_contract=False)
        self.assertFalse(adapter_has_required_contracts(entry))

    def test_has_tests_false(self) -> None:
        entry = AdapterRegistryEntry(profile=_make_profile(), has_tests=False)
        self.assertFalse(adapter_has_tests(entry))

    def test_has_safety_policy_false(self) -> None:
        entry = AdapterRegistryEntry(profile=_make_profile(), safety_policy=None)
        self.assertFalse(adapter_has_safety_policy(entry))

    def test_has_no_secret_policy_false(self) -> None:
        entry = AdapterRegistryEntry(profile=_make_profile(), safety_policy=None)
        self.assertFalse(adapter_has_no_secret_policy(entry))

    def test_has_docs_false(self) -> None:
        entry = AdapterRegistryEntry(profile=_make_profile(), has_docs=False)
        self.assertFalse(adapter_has_docs(entry))

    def test_has_tool_mastery_false(self) -> None:
        entry = AdapterRegistryEntry(profile=_make_profile(), has_tool_mastery=False)
        self.assertFalse(adapter_has_tool_mastery(entry))

    def test_has_tool_mastery_true(self) -> None:
        entry = AdapterRegistryEntry(profile=_make_profile(), has_tool_mastery=True)
        self.assertTrue(adapter_has_tool_mastery(entry))


class TestAdapterIsPromotable(unittest.TestCase):
    """Tests for adapter_is_promotable composite check."""

    def test_fails_if_any_check_fails(self) -> None:
        # Missing tool mastery
        entry = AdapterRegistryEntry(
            profile=_make_profile(),
            safety_policy=AdapterSafetyPolicy(
                adapter_id="test",
                no_secret_exposure=True,
                no_credential_capture=True,
            ),
            has_tests=True,
            has_docs=True,
            has_contract=True,
            has_tool_mastery=False,
        )
        self.assertFalse(adapter_is_promotable(entry))

    def test_fails_if_no_tests(self) -> None:
        entry = _make_full_entry()
        entry.has_tests = False
        self.assertFalse(adapter_is_promotable(entry))

    def test_fails_if_no_safety(self) -> None:
        entry = _make_full_entry()
        entry.safety_policy = None
        self.assertFalse(adapter_is_promotable(entry))

    def test_fails_if_no_docs(self) -> None:
        entry = _make_full_entry()
        entry.has_docs = False
        self.assertFalse(adapter_is_promotable(entry))

    def test_fails_if_no_contract(self) -> None:
        entry = _make_full_entry()
        entry.has_contract = False
        self.assertFalse(adapter_is_promotable(entry))

    def test_passes_when_all_6_checks_pass(self) -> None:
        entry = _make_full_entry()
        self.assertTrue(adapter_is_promotable(entry))


class TestEvaluateAdapterQuality(unittest.TestCase):
    """Tests for evaluate_adapter_quality report."""

    def test_report_has_6_checks(self) -> None:
        entry = _make_full_entry()
        report = evaluate_adapter_quality(entry)
        self.assertEqual(len(report.checks), 6)

    def test_check_names(self) -> None:
        entry = _make_full_entry()
        report = evaluate_adapter_quality(entry)
        names = [c.check_name for c in report.checks]
        self.assertIn("has_tool_mastery", names)
        self.assertIn("has_contracts", names)
        self.assertIn("has_tests", names)
        self.assertIn("has_safety_policy", names)
        self.assertIn("has_no_secret_policy", names)
        self.assertIn("has_docs", names)

    def test_overall_false_when_tool_mastery_missing(self) -> None:
        entry = _make_full_entry()
        entry.has_tool_mastery = False
        report = evaluate_adapter_quality(entry)
        self.assertFalse(report.overall_passed)

    def test_overall_true_when_all_pass(self) -> None:
        entry = _make_full_entry()
        report = evaluate_adapter_quality(entry)
        self.assertTrue(report.overall_passed)


if __name__ == "__main__":
    unittest.main()
