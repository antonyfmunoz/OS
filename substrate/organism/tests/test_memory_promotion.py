"""Tests for memory promotion pipeline."""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

import pytest

from substrate.organism.memory_promotion import (
    CanonicalMemoryEntry,
    MemoryCandidate,
    MemoryCategory,
    MemoryEvidence,
    MemoryPromotionDecision,
    MemoryPromotionPipeline,
    MemoryPromotionStatus,
    MemoryScope,
)


@pytest.fixture
def pipeline():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield MemoryPromotionPipeline(store_dir=tmpdir)


def _good_evidence() -> list[MemoryEvidence]:
    return [MemoryEvidence(source="test", detail="verified", confidence=0.8)]


class TestMemoryEvidence:
    def test_creation(self):
        ev = MemoryEvidence(source="learning", detail="observed", confidence=0.7)
        assert ev.source == "learning"
        assert ev.confidence == 0.7

    def test_to_dict(self):
        ev = MemoryEvidence(source="test", detail="d", confidence=0.5)
        d = ev.to_dict()
        assert d["confidence"] == 0.5


class TestMemoryCandidate:
    def test_creation(self):
        c = MemoryCandidate(content="Test observation", category=MemoryCategory.OBSERVATION)
        assert c.status == MemoryPromotionStatus.RAW
        assert c.id

    def test_average_evidence_confidence(self):
        c = MemoryCandidate(
            content="test",
            evidence=[
                MemoryEvidence(source="a", detail="x", confidence=0.6),
                MemoryEvidence(source="b", detail="y", confidence=0.8),
            ],
        )
        assert abs(c.average_evidence_confidence - 0.7) < 0.01

    def test_no_evidence_confidence(self):
        c = MemoryCandidate(content="test")
        assert c.average_evidence_confidence == 0.0

    def test_to_dict(self):
        c = MemoryCandidate(
            content="test",
            category=MemoryCategory.PATTERN,
            scope=MemoryScope.CANONICAL,
        )
        d = c.to_dict()
        assert d["category"] == "pattern"
        assert d["scope"] == "canonical"


class TestCanonicalMemoryEntry:
    def test_creation(self):
        e = CanonicalMemoryEntry(content="Canonical fact", confidence=0.9)
        assert e.confidence == 0.9

    def test_to_dict(self):
        e = CanonicalMemoryEntry(content="test", category=MemoryCategory.STRATEGY)
        d = e.to_dict()
        assert d["category"] == "strategy"


class TestMemoryPromotionDecision:
    def test_creation(self):
        d = MemoryPromotionDecision(
            candidate_id="abc",
            decision=MemoryPromotionStatus.PROMOTED,
            decided_by="operator",
        )
        assert d.decision == MemoryPromotionStatus.PROMOTED

    def test_to_dict(self):
        d = MemoryPromotionDecision(
            candidate_id="x",
            decision=MemoryPromotionStatus.REJECTED,
            reason="Low confidence",
        )
        dd = d.to_dict()
        assert dd["decision"] == "rejected"
        assert dd["reason"] == "Low confidence"


class TestPipelineSubmission:
    def test_submit_candidate(self, pipeline):
        c = pipeline.submit_candidate(
            content="Docker restart takes 15 seconds",
            category=MemoryCategory.OBSERVATION,
            evidence=_good_evidence(),
        )
        assert c.status == MemoryPromotionStatus.RAW
        assert pipeline.get_candidate(c.id) is not None

    def test_submit_with_source(self, pipeline):
        c = pipeline.submit_candidate(
            content="test",
            source_action="outcome_learning",
        )
        assert c.source_action == "outcome_learning"


class TestContradictionBlocking:
    def test_contradiction_check(self, pipeline):
        c = pipeline.submit_candidate(content="Test fact", evidence=_good_evidence())
        result = pipeline.run_contradiction_check(c.id)
        assert result is True
        assert c.contradiction_check is True

    def test_missing_candidate(self, pipeline):
        result = pipeline.run_contradiction_check("nonexistent")
        assert result is False


class TestEvidenceValidation:
    def test_eligible_with_evidence(self, pipeline):
        c = pipeline.submit_candidate(
            content="Valid observation",
            evidence=_good_evidence(),
        )
        pipeline.run_contradiction_check(c.id)
        eligible, reason = pipeline.evaluate_for_promotion(c.id)
        assert eligible is True

    def test_ineligible_no_evidence(self, pipeline):
        c = pipeline.submit_candidate(content="No evidence observation")
        pipeline.run_contradiction_check(c.id)
        eligible, reason = pipeline.evaluate_for_promotion(c.id)
        assert eligible is False
        assert "evidence" in reason.lower()

    def test_ineligible_low_confidence(self, pipeline):
        c = pipeline.submit_candidate(
            content="Low confidence",
            evidence=[MemoryEvidence(source="test", detail="weak", confidence=0.2)],
        )
        pipeline.run_contradiction_check(c.id)
        eligible, reason = pipeline.evaluate_for_promotion(c.id)
        assert eligible is False
        assert "confidence" in reason.lower()

    def test_ineligible_no_contradiction_check(self, pipeline):
        c = pipeline.submit_candidate(
            content="Unchecked",
            evidence=_good_evidence(),
        )
        eligible, reason = pipeline.evaluate_for_promotion(c.id)
        assert eligible is False
        assert "contradiction" in reason.lower()


class TestPromotionApproval:
    def test_promote_observation(self, pipeline):
        c = pipeline.submit_candidate(
            content="Probes run in 5 seconds",
            category=MemoryCategory.OBSERVATION,
            evidence=_good_evidence(),
        )
        pipeline.run_contradiction_check(c.id)
        entry = pipeline.promote(c.id)
        assert entry is not None
        assert c.status == MemoryPromotionStatus.PROMOTED

    def test_constraint_requires_operator(self, pipeline):
        c = pipeline.submit_candidate(
            content="Never restart all containers",
            category=MemoryCategory.CONSTRAINT,
            evidence=_good_evidence(),
        )
        pipeline.run_contradiction_check(c.id)
        entry = pipeline.promote(c.id)
        assert entry is None
        assert c.status == MemoryPromotionStatus.CANDIDATE

    def test_operator_approval_promotes(self, pipeline):
        c = pipeline.submit_candidate(
            content="Strategy fact",
            category=MemoryCategory.STRATEGY,
            evidence=_good_evidence(),
        )
        pipeline.run_contradiction_check(c.id)
        pipeline.promote(c.id)
        entry = pipeline.promote(c.id, decided_by="operator")
        assert entry is not None
        assert c.approved_by == "operator"


class TestRejection:
    def test_reject(self, pipeline):
        c = pipeline.submit_candidate(content="Bad fact", evidence=_good_evidence())
        result = pipeline.reject(c.id, reason="Factually incorrect", decided_by="operator")
        assert result is True
        assert c.status == MemoryPromotionStatus.REJECTED
        assert c.rejection_reason == "Factually incorrect"

    def test_reject_nonexistent(self, pipeline):
        result = pipeline.reject("nope")
        assert result is False


class TestSupersession:
    def test_supersede(self, pipeline):
        c1 = pipeline.submit_candidate(content="Old fact", evidence=_good_evidence())
        c2 = pipeline.submit_candidate(content="New fact", evidence=_good_evidence())
        result = pipeline.supersede(c1.id, c2.id)
        assert result is True
        assert c1.status == MemoryPromotionStatus.SUPERSEDED


class TestCanonicalInstanceSeparation:
    def test_instance_scope(self, pipeline):
        c = pipeline.submit_candidate(
            content="Instance fact",
            scope=MemoryScope.INSTANCE,
            evidence=_good_evidence(),
        )
        assert c.scope == MemoryScope.INSTANCE

    def test_canonical_scope(self, pipeline):
        c = pipeline.submit_candidate(
            content="Universal truth",
            scope=MemoryScope.CANONICAL,
            evidence=_good_evidence(),
        )
        assert c.scope == MemoryScope.CANONICAL


class TestSerialization:
    def test_pipeline_to_dict(self, pipeline):
        pipeline.submit_candidate(content="test", evidence=_good_evidence())
        d = pipeline.to_dict()
        serialized = json.dumps(d, default=str)
        parsed = json.loads(serialized)
        assert "summary" in parsed
        assert "candidates" in parsed
        assert "canonical" in parsed
        assert "pending_approvals" in parsed

    def test_summary(self, pipeline):
        pipeline.submit_candidate(content="a", evidence=_good_evidence())
        pipeline.submit_candidate(content="b", evidence=_good_evidence())
        s = pipeline.summary()
        assert s["total_candidates"] == 2


class TestListOperations:
    def test_list_candidates(self, pipeline):
        pipeline.submit_candidate(content="a", evidence=_good_evidence())
        pipeline.submit_candidate(content="b", evidence=_good_evidence())
        all_cands = pipeline.list_candidates()
        assert len(all_cands) == 2

    def test_list_by_status(self, pipeline):
        c = pipeline.submit_candidate(content="a", evidence=_good_evidence())
        pipeline.run_contradiction_check(c.id)
        pipeline.promote(c.id)
        promoted = pipeline.list_candidates(status=MemoryPromotionStatus.PROMOTED)
        assert len(promoted) == 1

    def test_list_canonical(self, pipeline):
        c = pipeline.submit_candidate(content="canon", evidence=_good_evidence())
        pipeline.run_contradiction_check(c.id)
        pipeline.promote(c.id)
        entries = pipeline.list_canonical()
        assert len(entries) == 1
        assert entries[0].content == "canon"

    def test_pending_approvals(self, pipeline):
        c = pipeline.submit_candidate(
            content="Strategy",
            category=MemoryCategory.STRATEGY,
            evidence=_good_evidence(),
        )
        pipeline.run_contradiction_check(c.id)
        pipeline.promote(c.id)
        pending = pipeline.pending_approvals()
        assert len(pending) == 1
