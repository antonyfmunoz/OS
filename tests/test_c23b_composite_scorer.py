"""Tests for Campaign 23B composite scorer and routes."""

from __future__ import annotations

import sys
sys.path.insert(0, "/opt/OS")

import json

import pytest

from substrate.organism.benchmarks.competitive import (
    CATEGORY_REGISTRY,
    COMPOSITE_DOMAINS,
    TIER_WEIGHTS,
    CategoryScore,
    ComparisonType,
    CompetitorProfile,
    CompetitorRegistry,
    GapEntry,
)
from substrate.organism.benchmarks.composite_scorer import CompositeScorer


@pytest.fixture
def registry(tmp_path):
    comps = {
        "schema_version": "1.0",
        "competitors": {
            "alpha": {
                "name": "Alpha", "vendor": "ACo", "market_category": "ide_agent",
                "architecture": "cli", "pricing_model": "free",
                "published_scores": {}, "capabilities": {}, "sources": [],
            },
            "beta": {
                "name": "Beta", "vendor": "BCo", "market_category": "coding_model",
                "architecture": "cloud", "pricing_model": "paid",
                "published_scores": {}, "capabilities": {}, "sources": [],
            },
        },
    }
    benchmarks = {"schema_version": "1.0", "benchmarks": {}}
    (tmp_path / "competitors.json").write_text(json.dumps(comps))
    (tmp_path / "industry_benchmarks.json").write_text(json.dumps(benchmarks))
    reg = CompetitorRegistry(data_dir=tmp_path)
    reg.load()
    return reg


class TestCompositeScorer:
    def test_empty_scorer(self, registry):
        scorer = CompositeScorer(registry=registry)
        assert scorer.compute_composite() == 0.0

    def test_register_score(self, registry):
        scorer = CompositeScorer(registry=registry)
        cs = CategoryScore(category_id="A", umh_score=0.85, tier=2)
        scorer.register_score("A", cs)
        assert scorer.get_score("A") is not None
        assert scorer.get_score("A").umh_score == 0.85

    def test_get_missing_score(self, registry):
        scorer = CompositeScorer(registry=registry)
        assert scorer.get_score("Z") is None

    def test_all_scores(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("A", CategoryScore(category_id="A", umh_score=0.8))
        scorer.register_score("B", CategoryScore(category_id="B", umh_score=0.7))
        assert len(scorer.all_scores()) == 2

    def test_scored_categories(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("A", CategoryScore(category_id="A"))
        assert "A" in scorer.scored_categories()

    def test_compute_composite_single(self, registry):
        scorer = CompositeScorer(registry=registry)
        cs = CategoryScore(category_id="A", umh_score=0.8, tier=2)
        scorer.register_score("A", cs)
        composite = scorer.compute_composite()
        assert composite == 0.8

    def test_compute_composite_weighted(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("A", CategoryScore(category_id="A", umh_score=1.0, tier=2))
        scorer.register_score("T", CategoryScore(category_id="T", umh_score=0.5, tier=4))
        composite = scorer.compute_composite()
        w2 = TIER_WEIGHTS[2]
        w4 = TIER_WEIGHTS[4]
        expected = (1.0 * w2 + 0.5 * w4) / (w2 + w4)
        assert abs(composite - expected) < 0.001

    def test_domain_score(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("A", CategoryScore(category_id="A", umh_score=0.9))
        scorer.register_score("E", CategoryScore(category_id="E", umh_score=0.7))
        domain = scorer.compute_domain_score("software_production")
        assert domain > 0

    def test_domain_score_empty(self, registry):
        scorer = CompositeScorer(registry=registry)
        assert scorer.compute_domain_score("software_production") == 0.0

    def test_domain_score_unknown(self, registry):
        scorer = CompositeScorer(registry=registry)
        assert scorer.compute_domain_score("nonexist") == 0.0


class TestCompetitorComposite:
    def test_competitor_composite(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("A", CategoryScore(
            category_id="A", umh_score=0.8,
            competitor_scores={"alpha": 0.6, "beta": 0.7},
        ))
        alpha_comp = scorer.compute_competitor_composite("alpha")
        assert alpha_comp == 0.6

    def test_competitor_composite_missing(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("A", CategoryScore(
            category_id="A", umh_score=0.8,
            competitor_scores={"alpha": 0.6},
        ))
        assert scorer.compute_competitor_composite("beta") == 0.0

    def test_competitor_composite_none_scores(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("A", CategoryScore(
            category_id="A", umh_score=0.8,
            competitor_scores={"alpha": None},
        ))
        assert scorer.compute_competitor_composite("alpha") == 0.0


class TestGapAnalysis:
    def test_no_gaps_when_empty(self, registry):
        scorer = CompositeScorer(registry=registry)
        assert scorer.gap_analysis() == []

    def test_leading(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("A", CategoryScore(
            category_id="A", umh_score=0.9,
            competitor_scores={"alpha": 0.6},
        ))
        gaps = scorer.gap_analysis()
        assert len(gaps) == 1
        assert gaps[0].gap_type == "leading"
        assert gaps[0].delta > 0

    def test_trailing(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("A", CategoryScore(
            category_id="A", umh_score=0.3,
            competitor_scores={"alpha": 0.8},
        ))
        gaps = scorer.gap_analysis()
        assert gaps[0].gap_type == "trailing"
        assert gaps[0].delta < 0

    def test_parity(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("A", CategoryScore(
            category_id="A", umh_score=0.7,
            competitor_scores={"alpha": 0.7},
        ))
        gaps = scorer.gap_analysis()
        assert gaps[0].gap_type == "parity"

    def test_recommendation_significant(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("A", CategoryScore(
            category_id="A", umh_score=0.3,
            competitor_scores={"alpha": 0.9},
        ))
        gaps = scorer.gap_analysis()
        assert "significant" in gaps[0].recommendation

    def test_no_gaps_when_no_competitors(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("F", CategoryScore(category_id="F", umh_score=0.9))
        gaps = scorer.gap_analysis()
        assert len(gaps) == 0


class TestUniqueCategories:
    def test_unique_when_no_competitors(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("F", CategoryScore(category_id="F", umh_score=0.9))
        unique = scorer.umh_unique_categories()
        assert "F" in unique

    def test_not_unique_with_competitors(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("A", CategoryScore(
            category_id="A", umh_score=0.9,
            competitor_scores={"alpha": 0.6},
        ))
        unique = scorer.umh_unique_categories()
        assert "A" not in unique

    def test_unique_when_all_none(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("F", CategoryScore(
            category_id="F", umh_score=0.9,
            competitor_scores={"alpha": None, "beta": None},
        ))
        unique = scorer.umh_unique_categories()
        assert "F" in unique


class TestMarketCategoryComparison:
    def test_groups_by_category(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("A", CategoryScore(
            category_id="A", umh_score=0.8,
            competitor_scores={"alpha": 0.6, "beta": 0.7},
        ))
        mc = scorer.market_category_comparison()
        assert "ide_agent" in mc
        assert "coding_model" in mc

    def test_ranking_includes_umh(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("A", CategoryScore(
            category_id="A", umh_score=0.8,
            competitor_scores={"alpha": 0.6},
        ))
        mc = scorer.market_category_comparison()
        ranking = mc["ide_agent"]["ranking"]
        ids = [r["id"] for r in ranking]
        assert "umh" in ids


class TestGenerateMatrix:
    def test_generates_matrix(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("A", CategoryScore(
            category_id="A", umh_score=0.8,
            competitor_scores={"alpha": 0.6},
        ))
        matrix = scorer.generate_matrix()
        assert matrix.umh_composite > 0
        assert matrix.timestamp > 0
        assert len(matrix.categories) == 1

    def test_matrix_to_dict(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("A", CategoryScore(category_id="A", umh_score=0.8))
        matrix = scorer.generate_matrix()
        d = matrix.to_dict()
        assert isinstance(d["categories"], list)
        assert isinstance(d["umh_composite"], float)

    def test_matrix_serializable(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("A", CategoryScore(category_id="A", umh_score=0.8))
        matrix = scorer.generate_matrix()
        s = json.dumps(matrix.to_dict())
        assert isinstance(s, str)


class TestSummary:
    def test_summary_keys(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("A", CategoryScore(
            category_id="A", umh_score=0.8,
            competitor_scores={"alpha": 0.6},
        ))
        s = scorer.summary()
        assert "umh_composite" in s
        assert "domain_scores" in s
        assert "categories_scored" in s
        assert "categories_total" in s
        assert s["categories_total"] == 20

    def test_summary_counts(self, registry):
        scorer = CompositeScorer(registry=registry)
        scorer.register_score("A", CategoryScore(
            category_id="A", umh_score=0.9,
            competitor_scores={"alpha": 0.6},
        ))
        scorer.register_score("B", CategoryScore(
            category_id="B", umh_score=0.3,
            competitor_scores={"alpha": 0.8},
        ))
        s = scorer.summary()
        assert s["leading_count"] == 1
        assert s["trailing_count"] == 1
