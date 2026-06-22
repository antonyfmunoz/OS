"""Tests for Campaign 23B competitive data layer and composite scorer."""

from __future__ import annotations

import sys
sys.path.insert(0, "/opt/OS")

import json
import os
import tempfile

import pytest

from substrate.organism.benchmarks.competitive import (
    CATEGORY_REGISTRY,
    COMPOSITE_DOMAINS,
    TIER_WEIGHTS,
    CategoryScore,
    ComparisonType,
    CompetitiveMatrix,
    CompetitorProfile,
    CompetitorRegistry,
    GapEntry,
    MarketCategory,
    MeasurementType,
)


class TestMarketCategory:
    def test_all_contains_five(self):
        assert len(MarketCategory.ALL) == 5

    def test_ide_agent_in_all(self):
        assert MarketCategory.IDE_AGENT in MarketCategory.ALL

    def test_organism_system_in_all(self):
        assert MarketCategory.ORGANISM_SYSTEM in MarketCategory.ALL


class TestMeasurementType:
    def test_benchmark(self):
        assert MeasurementType.BENCHMARK == "benchmark"

    def test_audit(self):
        assert MeasurementType.AUDIT == "audit"

    def test_strategic(self):
        assert MeasurementType.STRATEGIC == "strategic"


class TestCategoryRegistry:
    def test_has_20_categories(self):
        assert len(CATEGORY_REGISTRY) == 20

    def test_categories_a_through_t(self):
        for letter in "ABCDEFGHIJKLMNOPQRST":
            assert letter in CATEGORY_REGISTRY, f"Missing category {letter}"

    def test_each_has_required_keys(self):
        for cat_id, info in CATEGORY_REGISTRY.items():
            assert "name" in info, f"Missing name for {cat_id}"
            assert "tier" in info, f"Missing tier for {cat_id}"
            assert "type" in info, f"Missing type for {cat_id}"

    def test_tiers_in_range(self):
        for cat_id, info in CATEGORY_REGISTRY.items():
            assert 1 <= info["tier"] <= 5, f"Tier out of range for {cat_id}"

    def test_audits_are_tier_3_or_4(self):
        for cat_id, info in CATEGORY_REGISTRY.items():
            if info["type"] == MeasurementType.AUDIT:
                assert info["tier"] in (3, 4), f"Audit {cat_id} not tier 3 or 4"


class TestTierWeights:
    def test_five_tiers(self):
        assert len(TIER_WEIGHTS) == 5

    def test_tier1_highest(self):
        assert TIER_WEIGHTS[1] >= max(TIER_WEIGHTS.values())

    def test_all_positive(self):
        for w in TIER_WEIGHTS.values():
            assert w > 0


class TestCompositeDomains:
    def test_seven_domains(self):
        assert len(COMPOSITE_DOMAINS) == 7

    def test_all_categories_covered(self):
        covered = set()
        for cats in COMPOSITE_DOMAINS.values():
            covered.update(cats)
        for letter in "ABCDEFGHIJKLMNOPQRST":
            assert letter in covered, f"Category {letter} not in any domain"


class TestCompetitorProfile:
    def test_to_dict(self):
        p = CompetitorProfile(competitor_id="test", name="Test", vendor="V")
        d = p.to_dict()
        assert d["competitor_id"] == "test"
        assert d["name"] == "Test"
        assert isinstance(d["published_scores"], dict)

    def test_from_dict(self):
        data = {"competitor_id": "x", "name": "X", "vendor": "V", "market_category": "ide_agent"}
        p = CompetitorProfile.from_dict(data)
        assert p.competitor_id == "x"
        assert p.market_category == "ide_agent"

    def test_roundtrip(self):
        p = CompetitorProfile(
            competitor_id="rt", name="RT", vendor="V",
            published_scores={"a": 0.5}, capabilities={"x": True}
        )
        p2 = CompetitorProfile.from_dict(p.to_dict())
        assert p2.competitor_id == p.competitor_id
        assert p2.published_scores == p.published_scores


class TestCategoryScore:
    def test_to_dict(self):
        cs = CategoryScore(category_id="A", umh_score=0.85)
        d = cs.to_dict()
        assert d["category_id"] == "A"
        assert d["umh_score"] == 0.85

    def test_from_dict(self):
        cs = CategoryScore.from_dict({"category_id": "B", "tier": 2, "umh_score": 0.7})
        assert cs.category_id == "B"
        assert cs.tier == 2

    def test_default_comparison_type(self):
        cs = CategoryScore()
        assert cs.comparison_type == ComparisonType.NOT_APPLICABLE


class TestGapEntry:
    def test_to_dict(self):
        g = GapEntry(category_id="A", gap_type="leading", delta=0.15)
        d = g.to_dict()
        assert d["gap_type"] == "leading"
        assert d["delta"] == 0.15


class TestCompetitiveMatrix:
    def test_to_dict(self):
        m = CompetitiveMatrix(umh_composite=0.75)
        d = m.to_dict()
        assert d["umh_composite"] == 0.75
        assert isinstance(d["categories"], list)

    def test_from_dict(self):
        d = {"umh_composite": 0.8, "categories": [], "timestamp": 100.0}
        m = CompetitiveMatrix.from_dict(d)
        assert m.umh_composite == 0.8

    def test_from_dict_with_categories(self):
        d = {
            "categories": [{"category_id": "A", "umh_score": 0.9}],
            "gap_analysis": [{"category_id": "A", "gap_type": "leading", "delta": 0.1}],
        }
        m = CompetitiveMatrix.from_dict(d)
        assert len(m.categories) == 1
        assert m.categories[0].category_id == "A"


class TestCompetitorRegistry:
    @pytest.fixture
    def tmp_data_dir(self, tmp_path):
        comps = {
            "schema_version": "1.0",
            "competitors": {
                "alpha": {
                    "name": "Alpha",
                    "vendor": "AlphaCo",
                    "market_category": "ide_agent",
                    "architecture": "cli",
                    "pricing_model": "free",
                    "published_scores": {"swe_bench": 0.8},
                    "capabilities": {"autonomous_execution": True},
                    "sources": [],
                },
                "beta": {
                    "name": "Beta",
                    "vendor": "BetaCo",
                    "market_category": "coding_model",
                    "architecture": "cloud",
                    "pricing_model": "paid",
                    "published_scores": {},
                    "capabilities": {},
                    "sources": [],
                },
            },
        }
        benchmarks = {
            "schema_version": "1.0",
            "benchmarks": {
                "swe_bench": {
                    "name": "SWE-bench",
                    "scores": {"alpha": 80.0, "beta": 70.0},
                },
            },
        }
        (tmp_path / "competitors.json").write_text(json.dumps(comps))
        (tmp_path / "industry_benchmarks.json").write_text(json.dumps(benchmarks))
        return tmp_path

    def test_load(self, tmp_data_dir):
        reg = CompetitorRegistry(data_dir=tmp_data_dir)
        result = reg.load()
        assert len(result) == 2

    def test_get_competitor(self, tmp_data_dir):
        reg = CompetitorRegistry(data_dir=tmp_data_dir)
        c = reg.get_competitor("alpha")
        assert c is not None
        assert c.name == "Alpha"

    def test_get_missing(self, tmp_data_dir):
        reg = CompetitorRegistry(data_dir=tmp_data_dir)
        assert reg.get_competitor("nonexist") is None

    def test_all_competitors(self, tmp_data_dir):
        reg = CompetitorRegistry(data_dir=tmp_data_dir)
        assert len(reg.all_competitors()) == 2

    def test_by_market_category(self, tmp_data_dir):
        reg = CompetitorRegistry(data_dir=tmp_data_dir)
        ide = reg.by_market_category("ide_agent")
        assert len(ide) == 1
        assert ide[0].competitor_id == "alpha"

    def test_scores_for_benchmark(self, tmp_data_dir):
        reg = CompetitorRegistry(data_dir=tmp_data_dir)
        scores = reg.scores_for_benchmark("swe_bench")
        assert scores["alpha"] == 80.0

    def test_competitor_count(self, tmp_data_dir):
        reg = CompetitorRegistry(data_dir=tmp_data_dir)
        assert reg.competitor_count() == 2

    def test_industry_benchmark_names(self, tmp_data_dir):
        reg = CompetitorRegistry(data_dir=tmp_data_dir)
        assert "swe_bench" in reg.industry_benchmark_names()

    def test_has_capability(self, tmp_data_dir):
        reg = CompetitorRegistry(data_dir=tmp_data_dir)
        assert reg.has_capability("alpha", "autonomous_execution") is True

    def test_has_capability_missing(self, tmp_data_dir):
        reg = CompetitorRegistry(data_dir=tmp_data_dir)
        assert reg.has_capability("nonexist", "x") is None

    def test_auto_load(self, tmp_data_dir):
        reg = CompetitorRegistry(data_dir=tmp_data_dir)
        assert reg.competitor_count() == 2

    def test_empty_dir(self, tmp_path):
        reg = CompetitorRegistry(data_dir=tmp_path)
        reg.load()
        assert reg.competitor_count() == 0


class TestProductionDataFiles:
    _DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "umh", "validation", "competitive")

    def test_competitors_json_loads(self):
        path = os.path.join(self._DATA_DIR, "competitors.json")
        with open(path) as f:
            data = json.load(f)
        assert len(data["competitors"]) == 13

    def test_industry_benchmarks_json_loads(self):
        path = os.path.join(self._DATA_DIR, "industry_benchmarks.json")
        with open(path) as f:
            data = json.load(f)
        assert len(data["benchmarks"]) >= 4

    def test_production_registry_loads_13(self):
        reg = CompetitorRegistry(data_dir=self._DATA_DIR)
        reg.load()
        assert reg.competitor_count() == 13

    def test_production_market_categories(self):
        reg = CompetitorRegistry(data_dir=self._DATA_DIR)
        reg.load()
        for c in reg.all_competitors():
            assert c.market_category in MarketCategory.ALL, f"{c.name} has unknown category"
