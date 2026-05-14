"""Tests for Phase 96.4 template promotion contracts."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest

from runtime.substrate.template_promotion_contracts import (
    PromotionStatus,
    TemplatePatternCandidate,
)


class TestPromotionStatus(unittest.TestCase):
    """Tests for PromotionStatus enum."""

    def test_has_7_values(self) -> None:
        self.assertEqual(len(PromotionStatus), 7)

    def test_expected_members(self) -> None:
        expected = {
            "IDENTIFIED",
            "ABSTRACTED",
            "PRIVACY_REVIEWED",
            "APPROVED",
            "PROMOTED",
            "REJECTED",
            "REQUIRES_REVIEW",
        }
        self.assertEqual(set(PromotionStatus.__members__.keys()), expected)


class TestTemplatePatternCandidate(unittest.TestCase):
    """Tests for TemplatePatternCandidate."""

    def test_default_not_ready(self) -> None:
        c = TemplatePatternCandidate(source_instance_id="test")
        self.assertFalse(c.is_ready_for_promotion())

    def test_ready_when_all_conditions_met(self) -> None:
        c = TemplatePatternCandidate(
            source_instance_id="test",
            raw_instance_details_removed=True,
            privacy_review_status="passed",
            promotion_status=PromotionStatus.APPROVED,
        )
        self.assertTrue(c.is_ready_for_promotion())

    def test_not_ready_missing_details_removed(self) -> None:
        c = TemplatePatternCandidate(
            source_instance_id="test",
            raw_instance_details_removed=False,
            privacy_review_status="passed",
            promotion_status=PromotionStatus.APPROVED,
        )
        self.assertFalse(c.is_ready_for_promotion())

    def test_not_ready_missing_privacy_review(self) -> None:
        c = TemplatePatternCandidate(
            source_instance_id="test",
            raw_instance_details_removed=True,
            privacy_review_status="not_reviewed",
            promotion_status=PromotionStatus.APPROVED,
        )
        self.assertFalse(c.is_ready_for_promotion())

    def test_not_ready_missing_approval(self) -> None:
        c = TemplatePatternCandidate(
            source_instance_id="test",
            raw_instance_details_removed=True,
            privacy_review_status="passed",
            promotion_status=PromotionStatus.REQUIRES_REVIEW,
        )
        self.assertFalse(c.is_ready_for_promotion())

    def test_to_dict_serializes(self) -> None:
        c = TemplatePatternCandidate(
            source_instance_id="test",
            pattern_name="test_pattern",
        )
        d = c.to_dict()
        self.assertEqual(d["source_instance_id"], "test")
        self.assertEqual(d["pattern_name"], "test_pattern")
        self.assertEqual(d["promotion_status"], "requires_review")
        self.assertIn("raw_instance_details_removed", d)
        self.assertIn("privacy_review_status", d)


if __name__ == "__main__":
    unittest.main()
