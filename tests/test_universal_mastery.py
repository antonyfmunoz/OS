"""Tests for mastery_engine/universal_mastery.py — Phase 96.8A.1."""

import sys

sys.path.insert(0, "/opt/OS")

import unittest
from core.mastery_engine.universal_mastery import (
    MasteryCategory,
    MasteryStatus,
    UniversalMasteryDecision,
    build_universal_mastery_decision,
    mastery_category_required_for_execution,
    mastery_decision_blocks_execution,
    summarize_universal_mastery_decision,
)


class TestMasteryDecisionBuilds(unittest.TestCase):
    def test_build_returns_decision(self):
        d = build_universal_mastery_decision(
            action_id="um-001",
            required_categories=["tool", "environment"],
            satisfied_categories=["tool", "environment"],
        )
        self.assertIsInstance(d, UniversalMasteryDecision)
        self.assertEqual(d.action_id, "um-001")
        self.assertTrue(d.can_execute)

    def test_default_can_execute_when_no_missing(self):
        d = build_universal_mastery_decision(
            action_id="um-002",
            required_categories=["tool"],
            satisfied_categories=["tool"],
        )
        self.assertTrue(d.can_execute)
        self.assertEqual(len(d.blockers), 0)


class TestMissingCategoryBlocksExecution(unittest.TestCase):
    def test_missing_tool_blocks(self):
        d = build_universal_mastery_decision(
            action_id="um-010",
            required_categories=["tool", "environment"],
            satisfied_categories=["environment"],
            missing_categories=["tool"],
        )
        self.assertFalse(d.can_execute)
        self.assertTrue(mastery_decision_blocks_execution(d))
        self.assertTrue(any("MISSING_MASTERY" in b for b in d.blockers))

    def test_missing_multiple_categories(self):
        d = build_universal_mastery_decision(
            action_id="um-011",
            required_categories=["tool", "environment", "domain"],
            satisfied_categories=[],
            missing_categories=["tool", "environment", "domain"],
        )
        self.assertFalse(d.can_execute)
        self.assertEqual(len(d.missing_categories), 3)


class TestStaleCategoryBlocksOrWarns(unittest.TestCase):
    def test_stale_blocks_execution(self):
        d = build_universal_mastery_decision(
            action_id="um-020",
            required_categories=["tool"],
            satisfied_categories=[],
            stale_categories=["tool"],
        )
        self.assertFalse(d.can_execute)
        self.assertTrue(mastery_decision_blocks_execution(d))
        self.assertTrue(any("STALE_MASTERY" in b for b in d.blockers))


class TestVerifiedCategoriesAllowExecution(unittest.TestCase):
    def test_all_satisfied_allows(self):
        d = build_universal_mastery_decision(
            action_id="um-030",
            required_categories=["tool", "environment", "domain"],
            satisfied_categories=["tool", "environment", "domain"],
        )
        self.assertTrue(d.can_execute)
        self.assertFalse(mastery_decision_blocks_execution(d))
        self.assertEqual(len(d.blockers), 0)


class TestToolMasteryCategoryIsOneSlice(unittest.TestCase):
    def test_tool_is_one_of_many_categories(self):
        all_cats = list(MasteryCategory)
        self.assertIn(MasteryCategory.TOOL, all_cats)
        self.assertGreater(len(all_cats), 1)
        self.assertEqual(len(all_cats), 11)

    def test_tool_not_entire_system(self):
        d = build_universal_mastery_decision(
            action_id="um-040",
            required_categories=["tool", "environment", "adapter_boundary"],
            satisfied_categories=["tool"],
            missing_categories=["environment", "adapter_boundary"],
        )
        self.assertFalse(d.can_execute)


class TestHighRiskRequiresProofBackedMastery(unittest.TestCase):
    def test_proof_required_flag(self):
        d = build_universal_mastery_decision(
            action_id="um-050",
            required_categories=["tool"],
            satisfied_categories=["tool"],
            proof_required=True,
        )
        self.assertTrue(d.proof_required)
        self.assertTrue(d.can_execute)


class TestAllCategoriesRequiredForExecution(unittest.TestCase):
    def test_every_category_required(self):
        for cat in MasteryCategory:
            self.assertTrue(
                mastery_category_required_for_execution(cat),
                f"{cat.value} must be required for execution",
            )


class TestSummarize(unittest.TestCase):
    def test_summarize_returns_dict(self):
        d = build_universal_mastery_decision(action_id="um-100")
        s = summarize_universal_mastery_decision(d)
        self.assertIsInstance(s, dict)
        self.assertIn("can_execute", s)
        self.assertIn("missing_count", s)


class TestToDict(unittest.TestCase):
    def test_to_dict_has_fields(self):
        d = build_universal_mastery_decision(action_id="um-200")
        dd = d.to_dict()
        self.assertIn("action_id", dd)
        self.assertIn("can_execute", dd)
        self.assertIn("blockers", dd)


if __name__ == "__main__":
    unittest.main()
