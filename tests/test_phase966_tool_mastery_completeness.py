import sys

sys.path.insert(0, "/opt/OS")

import unittest
from eos_ai.substrate.adapter_engine_contracts import (
    AdapterProfile,
    AdapterType,
    AdapterSafetyPolicy,
    AdapterRegistryEntry,
    ToolMasteryPack,
    tool_mastery_has_completeness_requirements,
    tool_mastery_has_failure_modes,
    tool_mastery_has_anti_patterns,
    tool_mastery_has_validation_checklist,
    tool_mastery_is_mature,
)
from eos_ai.substrate.adapter_quality_gate import (
    adapter_tool_mastery_is_mature,
    evaluate_adapter_maturity,
    adapter_is_promotable,
)


def _make_empty_pack():
    return ToolMasteryPack(adapter_id="test", tool_name="Test Tool")


def _make_mature_pack():
    return ToolMasteryPack(
        adapter_id="test",
        tool_name="Test Tool",
        best_practices=["always verify"],
        common_workflows=["standard flow"],
        anti_patterns=["never skip validation"],
        failure_modes=["timeout on large docs"],
        completeness_requirements=["all tabs extracted"],
        validation_checklist=["tab count matches"],
    )


def _make_full_entry(pack=None, has_mastery=False):
    profile = AdapterProfile(adapter_id="test", adapter_type=AdapterType.API)
    safety = AdapterSafetyPolicy(adapter_id="test")
    return AdapterRegistryEntry(
        profile=profile,
        safety_policy=safety,
        tool_mastery=pack,
        has_tests=True,
        has_docs=True,
        has_contract=True,
        has_tool_mastery=has_mastery,
    )


class TestToolMasteryChecks(unittest.TestCase):
    def test_empty_pack_lacks_completeness(self):
        assert not tool_mastery_has_completeness_requirements(_make_empty_pack())

    def test_empty_pack_lacks_failure_modes(self):
        assert not tool_mastery_has_failure_modes(_make_empty_pack())

    def test_empty_pack_lacks_anti_patterns(self):
        assert not tool_mastery_has_anti_patterns(_make_empty_pack())

    def test_empty_pack_lacks_validation_checklist(self):
        assert not tool_mastery_has_validation_checklist(_make_empty_pack())

    def test_empty_pack_not_mature(self):
        assert not tool_mastery_is_mature(_make_empty_pack())

    def test_mature_pack_has_completeness(self):
        assert tool_mastery_has_completeness_requirements(_make_mature_pack())

    def test_mature_pack_has_failure_modes(self):
        assert tool_mastery_has_failure_modes(_make_mature_pack())

    def test_mature_pack_has_anti_patterns(self):
        assert tool_mastery_has_anti_patterns(_make_mature_pack())

    def test_mature_pack_has_validation_checklist(self):
        assert tool_mastery_has_validation_checklist(_make_mature_pack())

    def test_mature_pack_is_mature(self):
        assert tool_mastery_is_mature(_make_mature_pack())


class TestQualityGateMastery(unittest.TestCase):
    def test_no_pack_fails_maturity(self):
        entry = _make_full_entry(pack=None, has_mastery=False)
        assert not adapter_tool_mastery_is_mature(entry)

    def test_empty_pack_fails_maturity(self):
        entry = _make_full_entry(pack=_make_empty_pack(), has_mastery=True)
        assert not adapter_tool_mastery_is_mature(entry)

    def test_mature_pack_passes_maturity(self):
        entry = _make_full_entry(pack=_make_mature_pack(), has_mastery=True)
        assert adapter_tool_mastery_is_mature(entry)

    def test_maturity_report_has_7_checks(self):
        entry = _make_full_entry(pack=_make_mature_pack(), has_mastery=True)
        report = evaluate_adapter_maturity(entry)
        assert len(report.checks) == 7  # 6 base + 1 maturity

    def test_maturity_report_fails_without_mature_pack(self):
        entry = _make_full_entry(pack=_make_empty_pack(), has_mastery=True)
        report = evaluate_adapter_maturity(entry)
        assert not report.overall_passed

    def test_maturity_report_passes_with_mature_pack(self):
        entry = _make_full_entry(pack=_make_mature_pack(), has_mastery=True)
        report = evaluate_adapter_maturity(entry)
        assert report.overall_passed

    def test_promotable_without_mastery_fails(self):
        entry = _make_full_entry(pack=None, has_mastery=False)
        assert not adapter_is_promotable(entry)

    def test_pack_serializes(self):
        pack = _make_mature_pack()
        d = pack.to_dict()
        assert d["completeness_requirements_count"] == 1
        assert d["anti_patterns_count"] == 1
        assert d["validation_checklist_count"] == 1
        assert "version_scope" in d
        assert "last_verified" in d
        assert "provenance_notes" in d


class TestMaturityScoreAndGaps(unittest.TestCase):
    def test_full_pass_scores_100(self):
        entry = _make_full_entry(pack=_make_mature_pack(), has_mastery=True)
        report = evaluate_adapter_maturity(entry)
        self.assertEqual(report.maturity_score, 100.0)
        self.assertEqual(report.gaps_to_100, [])

    def test_partial_pass_scores_correctly(self):
        entry = _make_full_entry(pack=_make_empty_pack(), has_mastery=True)
        report = evaluate_adapter_maturity(entry)
        self.assertLess(report.maturity_score, 100.0)
        self.assertGreater(report.maturity_score, 0.0)
        self.assertGreater(len(report.gaps_to_100), 0)

    def test_zero_entry_has_gaps(self):
        profile = AdapterProfile(adapter_id="empty", adapter_type=AdapterType.API)
        entry = AdapterRegistryEntry(profile=profile)
        report = evaluate_adapter_maturity(entry)
        self.assertLess(report.maturity_score, 50.0)
        self.assertIn("missing tool mastery pack", report.gaps_to_100)

    def test_gaps_list_missing_checks_by_name(self):
        entry = _make_full_entry(pack=_make_mature_pack(), has_mastery=True)
        entry.has_tests = False
        report = evaluate_adapter_maturity(entry)
        self.assertIn("missing tests", report.gaps_to_100)
        self.assertAlmostEqual(report.maturity_score, 85.7, places=1)

    def test_base_quality_report_also_has_score(self):
        from eos_ai.substrate.adapter_quality_gate import evaluate_adapter_quality
        entry = _make_full_entry(pack=_make_mature_pack(), has_mastery=True)
        report = evaluate_adapter_quality(entry)
        self.assertEqual(report.maturity_score, 100.0)
        self.assertEqual(report.gaps_to_100, [])

    def test_report_serializes_score_and_gaps(self):
        entry = _make_full_entry(pack=_make_mature_pack(), has_mastery=True)
        entry.has_docs = False
        report = evaluate_adapter_maturity(entry)
        d = report.to_dict()
        self.assertIn("maturity_score", d)
        self.assertIn("gaps_to_100", d)
        self.assertLess(d["maturity_score"], 100.0)
        self.assertGreater(len(d["gaps_to_100"]), 0)

    def test_adapter_package_has_maturity_fields(self):
        from eos_ai.substrate.adapter_engine_contracts import AdapterPackage
        pkg = AdapterPackage(
            adapter_profile=AdapterProfile(adapter_id="pkg", adapter_type=AdapterType.API),
            maturity_score=85.7,
            gaps_to_100=["missing governance policy"],
        )
        d = pkg.to_dict()
        self.assertEqual(d["maturity_score"], 85.7)
        self.assertEqual(d["gaps_to_100"], ["missing governance policy"])


if __name__ == "__main__":
    unittest.main()
