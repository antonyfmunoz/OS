"""Tests for the TME Mastery Assurance Gate.

Validates blocking/allowing decisions, freshness evaluation,
quality evaluation, completeness checks, and recommended flows.
"""

import sys
import unittest
from datetime import date

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from composition.mastery.management.mastery_assurance import (
    MasteryAssuranceDecision,
    MasteryAssuranceStatus,
    RecommendedFlow,
    determine_required_tme_flow,
    determine_staleness_threshold,
    ensure_mastery_before_execution,
    evaluate_pack_completeness,
    evaluate_pack_freshness,
    evaluate_pack_quality,
    mastery_assurance_blocks_execution,
    normalize_tool_name,
)

COMPLETE_PACK_TEXT = """
This pack covers authentication setup and OAuth flows.
Rate limits are 100 req/min for standard tier.
Error codes include 400, 401, 403, 404, 429, 500.
SDK idioms for the Python client use async context managers.
Anti-patterns include polling without backoff.
The design intent is to provide a unified extraction interface.
Gotchas include silent truncation on large payloads.
""" + ("x" * 10_000)


class TestNormalization(unittest.TestCase):
    def test_alias_postgres(self):
        self.assertEqual(normalize_tool_name("postgres"), "neon_postgres")

    def test_alias_pg(self):
        self.assertEqual(normalize_tool_name("pg"), "neon_postgres")

    def test_alias_gsheets(self):
        self.assertEqual(normalize_tool_name("gsheets"), "google_sheets")

    def test_alias_drizzle(self):
        self.assertEqual(normalize_tool_name("drizzle"), "drizzle_orm")

    def test_passthrough(self):
        self.assertEqual(normalize_tool_name("discord"), "discord")

    def test_special_chars(self):
        self.assertEqual(normalize_tool_name("My Cool Tool!"), "my_cool_tool")


class TestFreshness(unittest.TestCase):
    def test_fresh(self):
        result = evaluate_pack_freshness("2026-04-20", "medium", date(2026, 5, 1))
        self.assertEqual(result, "fresh")

    def test_near_stale(self):
        result = evaluate_pack_freshness("2026-03-20", "medium", date(2026, 5, 1))
        self.assertEqual(result, "near_stale")

    def test_stale(self):
        result = evaluate_pack_freshness("2026-01-01", "medium", date(2026, 5, 1))
        self.assertEqual(result, "stale")

    def test_missing_date(self):
        self.assertEqual(evaluate_pack_freshness(None), "missing_date")

    def test_invalid_date(self):
        self.assertEqual(evaluate_pack_freshness("not-a-date"), "missing_date")

    def test_fast_threshold(self):
        result = evaluate_pack_freshness("2026-04-10", "fast", date(2026, 5, 1))
        self.assertEqual(result, "stale")

    def test_slow_threshold(self):
        result = evaluate_pack_freshness("2026-03-01", "slow", date(2026, 5, 1))
        self.assertEqual(result, "fresh")


class TestQuality(unittest.TestCase):
    def test_pass_standard(self):
        self.assertEqual(evaluate_pack_quality("x" * 8000, "standard"), "pass")

    def test_below_standard(self):
        self.assertEqual(evaluate_pack_quality("short", "standard"), "below_threshold")

    def test_critical_tier(self):
        self.assertEqual(evaluate_pack_quality("x" * 20000, "critical"), "pass")

    def test_light_tier(self):
        self.assertEqual(evaluate_pack_quality("x" * 5000, "light"), "pass")


class TestCompleteness(unittest.TestCase):
    def test_complete(self):
        self.assertEqual(evaluate_pack_completeness(COMPLETE_PACK_TEXT), "complete")

    def test_incomplete(self):
        self.assertEqual(evaluate_pack_completeness("just some text"), "incomplete")


class TestRecommendedFlow(unittest.TestCase):
    def test_no_pack(self):
        self.assertEqual(
            determine_required_tme_flow(False, "fresh", "complete", "pass"),
            RecommendedFlow.CREATE_FLOW,
        )

    def test_stale(self):
        self.assertEqual(
            determine_required_tme_flow(True, "stale", "complete", "pass"),
            RecommendedFlow.RE_RESEARCH_FLOW,
        )

    def test_incomplete(self):
        self.assertEqual(
            determine_required_tme_flow(True, "fresh", "incomplete", "pass"),
            RecommendedFlow.INCREMENTAL_UPDATE_FLOW,
        )

    def test_below_quality(self):
        self.assertEqual(
            determine_required_tme_flow(True, "fresh", "complete", "below_threshold"),
            RecommendedFlow.INCREMENTAL_UPDATE_FLOW,
        )

    def test_proceed(self):
        self.assertEqual(
            determine_required_tme_flow(True, "fresh", "complete", "pass"),
            RecommendedFlow.PROCEED,
        )


class TestEnsureMasteryBeforeExecution(unittest.TestCase):
    def test_missing_pack_blocks(self):
        d = ensure_mastery_before_execution("discord", pack_exists=False)
        self.assertFalse(d.can_execute)
        self.assertEqual(d.status, MasteryAssuranceStatus.MISSING_PACK)
        self.assertEqual(d.recommended_flow, RecommendedFlow.CREATE_FLOW)

    def test_stale_pack_blocks(self):
        d = ensure_mastery_before_execution(
            "discord",
            pack_exists=True,
            pack_text=COMPLETE_PACK_TEXT,
            last_researched="2025-01-01",
            current_date=date(2026, 5, 1),
        )
        self.assertFalse(d.can_execute)
        self.assertEqual(d.status, MasteryAssuranceStatus.STALE_PACK)

    def test_incomplete_pack_blocks(self):
        d = ensure_mastery_before_execution(
            "discord",
            pack_exists=True,
            pack_text="x" * 10000,
            last_researched="2026-04-20",
            current_date=date(2026, 5, 1),
        )
        self.assertFalse(d.can_execute)
        self.assertEqual(d.status, MasteryAssuranceStatus.INCOMPLETE_PACK)

    def test_below_quality_blocks(self):
        complete_but_short = """authentication rate limits error codes
sdk idioms anti-patterns design intent gotchas"""
        d = ensure_mastery_before_execution(
            "discord",
            pack_exists=True,
            pack_text=complete_but_short,
            last_researched="2026-04-20",
            current_date=date(2026, 5, 1),
        )
        self.assertFalse(d.can_execute)
        self.assertEqual(d.status, MasteryAssuranceStatus.QUALITY_BELOW_THRESHOLD)

    def test_assured_allows(self):
        d = ensure_mastery_before_execution(
            "discord",
            pack_exists=True,
            pack_text=COMPLETE_PACK_TEXT,
            last_researched="2026-04-20",
            current_date=date(2026, 5, 1),
        )
        self.assertTrue(d.can_execute)
        self.assertEqual(d.status, MasteryAssuranceStatus.ASSURED)
        self.assertEqual(d.recommended_flow, RecommendedFlow.PROCEED)

    def test_founder_waiver_allows_missing(self):
        d = ensure_mastery_before_execution(
            "discord",
            pack_exists=False,
            founder_waiver=True,
        )
        self.assertTrue(d.can_execute)
        self.assertEqual(d.status, MasteryAssuranceStatus.WAIVED_BY_FOUNDER)

    def test_founder_waiver_allows_stale(self):
        d = ensure_mastery_before_execution(
            "discord",
            pack_exists=True,
            pack_text="short",
            last_researched="2020-01-01",
            founder_waiver=True,
        )
        self.assertTrue(d.can_execute)
        self.assertEqual(d.status, MasteryAssuranceStatus.WAIVED_BY_FOUNDER)

    def test_alias_normalized(self):
        d = ensure_mastery_before_execution("postgres", pack_exists=False)
        self.assertEqual(d.normalized_tool_name, "neon_postgres")


class TestBlocksExecution(unittest.TestCase):
    def test_blocks_when_cannot_execute(self):
        d = MasteryAssuranceDecision(
            tool_name="x", normalized_tool_name="x", can_execute=False
        )
        self.assertTrue(mastery_assurance_blocks_execution(d))

    def test_does_not_block_when_can_execute(self):
        d = MasteryAssuranceDecision(
            tool_name="x",
            normalized_tool_name="x",
            can_execute=True,
            status=MasteryAssuranceStatus.ASSURED,
        )
        self.assertFalse(mastery_assurance_blocks_execution(d))


class TestSerialization(unittest.TestCase):
    def test_decision_to_dict(self):
        d = ensure_mastery_before_execution("discord", pack_exists=False)
        dd = d.to_dict()
        self.assertIn("status", dd)
        self.assertIn("can_execute", dd)
        self.assertIn("recommended_flow", dd)
        self.assertEqual(dd["status"], "missing_pack")
        self.assertEqual(dd["recommended_flow"], "create_flow")

    def test_staleness_threshold_values(self):
        self.assertEqual(determine_staleness_threshold("fast"), 14)
        self.assertEqual(determine_staleness_threshold("medium"), 45)
        self.assertEqual(determine_staleness_threshold("stable"), 90)
        self.assertEqual(determine_staleness_threshold("slow"), 120)
        self.assertEqual(determine_staleness_threshold("unknown"), 45)


if __name__ == "__main__":
    unittest.main()
