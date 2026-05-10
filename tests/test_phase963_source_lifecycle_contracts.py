"""Tests for eos_ai/substrate/source_lifecycle_contracts.py (Phase 96.3)."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest

from eos_ai.substrate.source_lifecycle_contracts import (
    SourceIngestionRule,
    SourceLifecycleRecord,
    SourceLifecycleStage,
    SourceReviewType,
    can_ingest_without_review,
    is_interpretation_separate_from_raw,
    is_raw_record_immutable,
    requires_review_before_promotion,
    requires_safety_auth_before_ingestion,
)


class TestSourceLifecycleStage(unittest.TestCase):
    def test_has_11_values(self) -> None:
        self.assertEqual(len(SourceLifecycleStage), 11)

    def test_first_value(self) -> None:
        self.assertEqual(SourceLifecycleStage.DISCOVERED.value, "discovered")

    def test_last_value(self) -> None:
        self.assertEqual(
            SourceLifecycleStage.REQUIRES_FOUNDER_DECISION.value,
            "requires_founder_decision",
        )


class TestSourceReviewType(unittest.TestCase):
    def test_has_7_values(self) -> None:
        self.assertEqual(len(SourceReviewType), 7)


class TestSourceIngestionRule(unittest.TestCase):
    def test_has_6_values(self) -> None:
        self.assertEqual(len(SourceIngestionRule), 6)


class TestLifecycleFunctions(unittest.TestCase):
    def test_ingested_raw_can_exist_before_review(self) -> None:
        """Ingested raw can exist before review."""
        self.assertTrue(can_ingest_without_review(SourceLifecycleStage.INGESTED_RAW))

    def test_promoted_cannot_ingest_without_review(self) -> None:
        self.assertFalse(can_ingest_without_review(SourceLifecycleStage.PROMOTED))

    def test_review_gates_block_promotion_not_ingestion(self) -> None:
        """Review gates block promotion, not ingestion."""
        self.assertTrue(requires_review_before_promotion(SourceLifecycleStage.PROMOTED))

    def test_reviewed_requires_review_before_promotion(self) -> None:
        self.assertTrue(requires_review_before_promotion(SourceLifecycleStage.REVIEWED))

    def test_raw_source_records_immutable(self) -> None:
        """Raw source records immutable."""
        self.assertTrue(is_raw_record_immutable())

    def test_interpretation_separate_from_raw(self) -> None:
        self.assertTrue(is_interpretation_separate_from_raw())

    def test_safety_auth_before_ingestion(self) -> None:
        self.assertTrue(requires_safety_auth_before_ingestion())


class TestSourceLifecycleRecord(unittest.TestCase):
    def test_can_proceed_to_ingestion_all_true(self) -> None:
        record = SourceLifecycleRecord(
            source_id="test-1",
            authorized=True,
            scope_verified=True,
            safety_verified=True,
        )
        self.assertTrue(record.can_proceed_to_ingestion())

    def test_can_proceed_to_ingestion_missing_auth(self) -> None:
        record = SourceLifecycleRecord(
            source_id="test-2",
            authorized=False,
            scope_verified=True,
            safety_verified=True,
        )
        self.assertFalse(record.can_proceed_to_ingestion())

    def test_can_proceed_to_ingestion_missing_scope(self) -> None:
        record = SourceLifecycleRecord(
            source_id="test-3",
            authorized=True,
            scope_verified=False,
            safety_verified=True,
        )
        self.assertFalse(record.can_proceed_to_ingestion())

    def test_can_proceed_to_ingestion_missing_safety(self) -> None:
        record = SourceLifecycleRecord(
            source_id="test-4",
            authorized=True,
            scope_verified=True,
            safety_verified=False,
        )
        self.assertFalse(record.can_proceed_to_ingestion())

    def test_can_proceed_to_promotion_reviewed_not_promoted(self) -> None:
        record = SourceLifecycleRecord(
            source_id="test-5",
            reviewed=True,
            promoted=False,
        )
        self.assertTrue(record.can_proceed_to_promotion())

    def test_cannot_proceed_to_promotion_not_reviewed(self) -> None:
        record = SourceLifecycleRecord(source_id="test-6", reviewed=False)
        self.assertFalse(record.can_proceed_to_promotion())

    def test_cannot_proceed_to_promotion_already_promoted(self) -> None:
        record = SourceLifecycleRecord(
            source_id="test-7",
            reviewed=True,
            promoted=True,
        )
        self.assertFalse(record.can_proceed_to_promotion())

    def test_to_dict_serializes_correctly(self) -> None:
        record = SourceLifecycleRecord(
            source_id="test-8",
            current_stage=SourceLifecycleStage.INGESTED_RAW,
            authorized=True,
            scope_verified=True,
            safety_verified=True,
            raw_ingested=True,
            review_types_completed=[SourceReviewType.SAFETY_REVIEW],
            notes="test note",
        )
        d = record.to_dict()
        self.assertEqual(d["source_id"], "test-8")
        self.assertEqual(d["current_stage"], "ingested_raw")
        self.assertTrue(d["authorized"])
        self.assertTrue(d["raw_ingested"])
        self.assertEqual(d["review_types_completed"], ["safety_review"])
        self.assertEqual(d["notes"], "test note")


if __name__ == "__main__":
    unittest.main()
