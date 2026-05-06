"""Tests for mastery_engine/mastery_requirement_contracts.py — Phase 96.8A.1."""

import sys

sys.path.insert(0, "/opt/OS")

import unittest
from core.mastery_engine.universal_mastery import MasteryCategory, MasteryStatus
from core.mastery_engine.mastery_requirement_contracts import (
    MasteryRequirement,
    build_mastery_requirement,
    mastery_requirement_is_satisfied,
    mastery_requirement_is_stale,
    mastery_requirement_blocks_execution,
    summarize_mastery_requirement,
)


class TestMasteryRequirementBuilds(unittest.TestCase):
    def test_build_returns_requirement(self):
        req = build_mastery_requirement(
            mastery_id="mr-001",
            category=MasteryCategory.TOOL,
            target="google_drive_api",
            capability_scope="read_drive_inventory",
        )
        self.assertIsInstance(req, MasteryRequirement)
        self.assertEqual(req.mastery_id, "mr-001")
        self.assertEqual(req.category, MasteryCategory.TOOL)

    def test_default_status_is_missing(self):
        req = build_mastery_requirement(mastery_id="mr-002")
        self.assertEqual(req.current_status, MasteryStatus.MISSING)


class TestMissingRequirementNotSatisfied(unittest.TestCase):
    def test_missing_is_not_satisfied(self):
        req = build_mastery_requirement(
            mastery_id="mr-010",
            current_status=MasteryStatus.MISSING,
        )
        self.assertFalse(mastery_requirement_is_satisfied(req))

    def test_partial_is_not_satisfied(self):
        req = build_mastery_requirement(
            mastery_id="mr-011",
            current_status=MasteryStatus.PARTIAL,
        )
        self.assertFalse(mastery_requirement_is_satisfied(req))


class TestStaleRequirementDetected(unittest.TestCase):
    def test_stale_detected(self):
        req = build_mastery_requirement(
            mastery_id="mr-020",
            current_status=MasteryStatus.STALE,
        )
        self.assertTrue(mastery_requirement_is_stale(req))

    def test_current_not_stale(self):
        req = build_mastery_requirement(
            mastery_id="mr-021",
            current_status=MasteryStatus.CURRENT,
        )
        self.assertFalse(mastery_requirement_is_stale(req))


class TestSatisfiedRequirementPasses(unittest.TestCase):
    def test_current_is_satisfied(self):
        req = build_mastery_requirement(
            mastery_id="mr-030",
            current_status=MasteryStatus.CURRENT,
        )
        self.assertTrue(mastery_requirement_is_satisfied(req))

    def test_verified_is_satisfied(self):
        req = build_mastery_requirement(
            mastery_id="mr-031",
            current_status=MasteryStatus.VERIFIED,
        )
        self.assertTrue(mastery_requirement_is_satisfied(req))


class TestMissingRequirementBlocksExecution(unittest.TestCase):
    def test_missing_blocks(self):
        req = build_mastery_requirement(
            mastery_id="mr-040",
            current_status=MasteryStatus.MISSING,
        )
        self.assertTrue(mastery_requirement_blocks_execution(req))

    def test_blocked_blocks(self):
        req = build_mastery_requirement(
            mastery_id="mr-041",
            current_status=MasteryStatus.BLOCKED,
        )
        self.assertTrue(mastery_requirement_blocks_execution(req))


class TestHighRiskStaleBlocks(unittest.TestCase):
    def test_stale_high_risk_blocks(self):
        req = build_mastery_requirement(
            mastery_id="mr-050",
            current_status=MasteryStatus.STALE,
            risk_level="high",
        )
        self.assertTrue(mastery_requirement_blocks_execution(req))

    def test_stale_low_risk_does_not_block(self):
        req = build_mastery_requirement(
            mastery_id="mr-051",
            current_status=MasteryStatus.STALE,
            risk_level="low",
        )
        self.assertFalse(mastery_requirement_blocks_execution(req))


class TestProofRequiredMissingProofBlocks(unittest.TestCase):
    def test_proof_required_but_not_verified_blocks(self):
        req = build_mastery_requirement(
            mastery_id="mr-060",
            current_status=MasteryStatus.CURRENT,
            required_proof=["completion_artifact"],
        )
        self.assertTrue(mastery_requirement_blocks_execution(req))

    def test_proof_required_verified_does_not_block(self):
        req = build_mastery_requirement(
            mastery_id="mr-061",
            current_status=MasteryStatus.VERIFIED,
            required_proof=["completion_artifact"],
        )
        self.assertFalse(mastery_requirement_blocks_execution(req))


class TestSummarize(unittest.TestCase):
    def test_summarize_returns_dict(self):
        req = build_mastery_requirement(mastery_id="mr-100")
        s = summarize_mastery_requirement(req)
        self.assertIsInstance(s, dict)
        self.assertIn("mastery_id", s)
        self.assertIn("satisfied", s)
        self.assertIn("blocks_execution", s)


class TestToDict(unittest.TestCase):
    def test_to_dict_has_fields(self):
        req = build_mastery_requirement(mastery_id="mr-200")
        d = req.to_dict()
        self.assertIn("mastery_id", d)
        self.assertIn("category", d)
        self.assertIn("current_status", d)


if __name__ == "__main__":
    unittest.main()
