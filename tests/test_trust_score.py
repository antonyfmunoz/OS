"""Tests for TrustScoreEngine — C26E Phase 2.

Validates the weakest-link trust gate: min(claim, verification, reality).
"""

from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "/opt/OS/.claude/worktrees/remaining-phases")

from substrate.organism.trust_score import (
    DimensionScore,
    TrustDimension,
    TrustLevel,
    TrustScore,
    TrustScoreEngine,
)


class TestTrustScoreEngine:
    """Core engine tests."""

    def test_composite_is_min_of_all_dimensions(self):
        engine = TrustScoreEngine()
        score = engine.compute("w1", claim_confidence=0.9, verification_confidence=0.5, reality_confidence=0.7)
        assert score.composite_trust == pytest.approx(0.5)

    def test_c25_retroactive_100_claim_0_verification(self):
        """The C25 failure: 100% claim + 0% verification = 0% trust."""
        engine = TrustScoreEngine()
        score = engine.compute("c25", claim_confidence=1.0, verification_confidence=0.0, reality_confidence=0.0)
        assert score.composite_trust == pytest.approx(0.0)
        assert score.trust_level == TrustLevel.UNTRUSTED
        assert not score.can_promote

    def test_all_dimensions_full(self):
        engine = TrustScoreEngine()
        score = engine.compute("perfect", claim_confidence=1.0, verification_confidence=1.0, reality_confidence=1.0)
        assert score.composite_trust == pytest.approx(1.0)
        assert score.trust_level == TrustLevel.FULL
        assert score.can_promote

    def test_reality_0_blocks_everything(self):
        engine = TrustScoreEngine()
        score = engine.compute("broken", claim_confidence=1.0, verification_confidence=1.0, reality_confidence=0.0)
        assert score.composite_trust == pytest.approx(0.0)
        assert score.trust_level == TrustLevel.UNTRUSTED

    def test_scores_clamped_to_0_1(self):
        engine = TrustScoreEngine()
        score = engine.compute("clamped", claim_confidence=1.5, verification_confidence=-0.3, reality_confidence=0.8)
        dims = {d.dimension: d.score for d in score.dimensions}
        assert dims[TrustDimension.CLAIM] == 1.0
        assert dims[TrustDimension.VERIFICATION] == 0.0
        assert score.composite_trust == pytest.approx(0.0)


class TestClassify:
    """TrustLevel classification thresholds."""

    def test_classify_full(self):
        assert TrustScoreEngine.classify(1.0) == TrustLevel.FULL
        assert TrustScoreEngine.classify(0.75) == TrustLevel.FULL

    def test_classify_high(self):
        assert TrustScoreEngine.classify(0.74) == TrustLevel.HIGH
        assert TrustScoreEngine.classify(0.5) == TrustLevel.HIGH

    def test_classify_medium(self):
        assert TrustScoreEngine.classify(0.49) == TrustLevel.MEDIUM
        assert TrustScoreEngine.classify(0.25) == TrustLevel.MEDIUM

    def test_classify_low(self):
        assert TrustScoreEngine.classify(0.24) == TrustLevel.LOW
        assert TrustScoreEngine.classify(0.01) == TrustLevel.LOW

    def test_classify_untrusted(self):
        assert TrustScoreEngine.classify(0.0) == TrustLevel.UNTRUSTED


class TestCanPromote:
    """Only HIGH and FULL can promote to canonical."""

    def test_full_can_promote(self):
        engine = TrustScoreEngine()
        score = engine.compute("ok", 1.0, 1.0, 1.0)
        assert TrustScoreEngine.can_promote(score) is True

    def test_high_can_promote(self):
        engine = TrustScoreEngine()
        score = engine.compute("ok2", 0.6, 0.6, 0.6)
        assert TrustScoreEngine.can_promote(score) is True

    def test_medium_cannot_promote(self):
        engine = TrustScoreEngine()
        score = engine.compute("medium", 0.4, 0.4, 0.4)
        assert TrustScoreEngine.can_promote(score) is False

    def test_low_cannot_promote(self):
        engine = TrustScoreEngine()
        score = engine.compute("low", 0.1, 0.1, 0.1)
        assert TrustScoreEngine.can_promote(score) is False

    def test_untrusted_cannot_promote(self):
        engine = TrustScoreEngine()
        score = engine.compute("bad", 0.0, 0.0, 0.0)
        assert TrustScoreEngine.can_promote(score) is False


class TestCache:
    """In-memory score cache."""

    def test_get_score_returns_cached(self):
        engine = TrustScoreEngine()
        engine.compute("cached", 0.8, 0.9, 0.7)
        retrieved = engine.get_score("cached")
        assert retrieved is not None
        assert retrieved.work_id == "cached"
        assert retrieved.composite_trust == pytest.approx(0.7)

    def test_get_score_returns_none_for_missing(self):
        engine = TrustScoreEngine()
        assert engine.get_score("nonexistent") is None

    def test_overwrite_on_recompute(self):
        engine = TrustScoreEngine()
        engine.compute("w1", 0.5, 0.5, 0.5)
        engine.compute("w1", 0.9, 0.9, 0.9)
        score = engine.get_score("w1")
        assert score is not None
        assert score.composite_trust == pytest.approx(0.9)


class TestSummary:
    """Summary statistics."""

    def test_empty_summary(self):
        engine = TrustScoreEngine()
        s = engine.summary()
        assert s["total"] == 0
        assert s["promotion_eligible"] == 0
        assert s["promotion_blocked"] == 0

    def test_summary_counts_by_level(self):
        engine = TrustScoreEngine()
        engine.compute("full", 1.0, 1.0, 1.0)
        engine.compute("high", 0.6, 0.6, 0.6)
        engine.compute("low", 0.1, 0.1, 0.1)
        s = engine.summary()
        assert s["total"] == 3
        assert s["by_level"]["full"] == 1
        assert s["by_level"]["high"] == 1
        assert s["by_level"]["low"] == 1
        assert s["promotion_eligible"] == 2
        assert s["promotion_blocked"] == 1


class TestSerialization:
    """to_dict contracts."""

    def test_dimension_score_to_dict(self):
        ds = DimensionScore(
            dimension=TrustDimension.CLAIM,
            score=0.85,
            evidence=["proof.md"],
            source="outcome_verification",
        )
        d = ds.to_dict()
        assert d["dimension"] == "claim"
        assert d["score"] == pytest.approx(0.85, abs=0.001)
        assert d["evidence"] == ["proof.md"]
        assert d["source"] == "outcome_verification"

    def test_trust_score_to_dict(self):
        engine = TrustScoreEngine()
        score = engine.compute(
            "w1", 0.8, 0.6, 0.9,
            claim_evidence=["task succeeded"],
            verification_source="outcome_verification",
        )
        d = score.to_dict()
        assert d["work_id"] == "w1"
        assert d["composite_trust"] == pytest.approx(0.6, abs=0.001)
        assert d["trust_level"] == "high"
        assert d["can_promote"] is True
        assert len(d["dimensions"]) == 3
        assert "computed_at" in d


class TestTrustGateIntegration:
    """Test trust gate blocks low-trust writes to canonical reality."""

    def _make_mutation(self, mutation_id, content, metadata=None):
        from substrate.reality_model.reality_mutation import (
            MutationSource,
            MutationType,
            RealityMutation,
        )
        return RealityMutation(
            mutation_id=mutation_id,
            source_system=MutationSource.GOVERNANCE,
            source_id="test",
            mutation_type=MutationType.OBSERVATION_RECORDED,
            content=content,
            confidence=0.9,
            domain="deployment",
            metadata=metadata or {},
        )

    def test_low_trust_blocks_canonical_write(self):
        from substrate.reality_model.canonical_reality_write import CanonicalRealityWritePath

        engine = TrustScoreEngine()
        engine.compute("wp-low-trust", 1.0, 0.0, 0.0)

        write_path = CanonicalRealityWritePath(trust_engine=engine)
        mutation = self._make_mutation("m1", "EOS deployed", {"work_id": "wp-low-trust"})
        receipt = write_path.apply_mutation(mutation)
        assert receipt.accepted is False
        assert "trust gate" in receipt.reason

    def test_high_trust_allows_canonical_write(self):
        from substrate.reality_model.canonical_reality_write import CanonicalRealityWritePath

        engine = TrustScoreEngine()
        engine.compute("wp-high-trust", 1.0, 1.0, 1.0)

        write_path = CanonicalRealityWritePath(trust_engine=engine)
        mutation = self._make_mutation("m2", "EOS deployed", {"work_id": "wp-high-trust"})
        receipt = write_path.apply_mutation(mutation)
        assert receipt.accepted is True

    def test_no_trust_engine_allows_write(self):
        from substrate.reality_model.canonical_reality_write import CanonicalRealityWritePath

        write_path = CanonicalRealityWritePath()
        mutation = self._make_mutation("m3", "No trust engine present")
        receipt = write_path.apply_mutation(mutation)
        assert receipt.accepted is True

    def test_no_work_id_in_metadata_allows_write(self):
        from substrate.reality_model.canonical_reality_write import CanonicalRealityWritePath

        engine = TrustScoreEngine()
        engine.compute("wp-other", 0.0, 0.0, 0.0)

        write_path = CanonicalRealityWritePath(trust_engine=engine)
        mutation = self._make_mutation("m4", "Mutation without work_id")
        receipt = write_path.apply_mutation(mutation)
        assert receipt.accepted is True


class TestCanonicalTypes:
    """Verify types are registered in canonical_types.py."""

    def test_types_registered(self):
        from substrate.canonical_types import lookup
        for name in ("TrustDimension", "TrustLevel", "DimensionScore", "TrustScore"):
            result = lookup(name)
            assert result is not None, f"{name} not registered in canonical_types.py"
            assert "substrate.organism.trust_score" in result
