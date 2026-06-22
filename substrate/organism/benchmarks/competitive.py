"""Competitive benchmarking data layer — competitor profiles, market categories, and scoring.

Campaign 23B: UMH vs Industry Benchmark Suite. Provides structured competitor
data, market category classification, and the dataclasses used by CompositeScorer
to generate the competitive matrix.

All competitor data lives in JSON files under data/umh/validation/competitive/.
Adding a competitor is a data edit, not a code change.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class MarketCategory:
    IDE_AGENT = "ide_agent"
    AUTONOMOUS_DEVELOPER = "autonomous_developer"
    CODING_MODEL = "coding_model"
    RUNTIME_PLATFORM = "runtime_platform"
    ORGANISM_SYSTEM = "organism_system"

    ALL = frozenset({
        IDE_AGENT, AUTONOMOUS_DEVELOPER, CODING_MODEL,
        RUNTIME_PLATFORM, ORGANISM_SYSTEM,
    })


class MeasurementType:
    BENCHMARK = "benchmark"
    AUDIT = "audit"
    STRATEGIC = "strategic"


class ComparisonType:
    SAME_CATEGORY = "same_category"
    CROSS_CATEGORY = "cross_category"
    NOT_APPLICABLE = "n_a"


@dataclass
class CompetitorProfile:
    competitor_id: str = ""
    name: str = ""
    vendor: str = ""
    market_category: str = ""
    architecture: str = ""
    pricing_model: str = ""
    published_scores: dict[str, float] = field(default_factory=dict)
    capabilities: dict[str, bool] = field(default_factory=dict)
    sources: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompetitorProfile:
        return cls(
            competitor_id=data.get("competitor_id", ""),
            name=data.get("name", ""),
            vendor=data.get("vendor", ""),
            market_category=data.get("market_category", ""),
            architecture=data.get("architecture", ""),
            pricing_model=data.get("pricing_model", ""),
            published_scores=data.get("published_scores", {}),
            capabilities=data.get("capabilities", {}),
            sources=data.get("sources", []),
        )


@dataclass
class CategoryScore:
    category_id: str = ""
    category_name: str = ""
    tier: int = 0
    measurement_type: str = ""
    umh_score: float = 0.0
    umh_raw: dict[str, float] = field(default_factory=dict)
    competitor_scores: dict[str, float | None] = field(default_factory=dict)
    comparison_type: str = ComparisonType.NOT_APPLICABLE

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CategoryScore:
        return cls(
            category_id=data.get("category_id", ""),
            category_name=data.get("category_name", ""),
            tier=data.get("tier", 0),
            measurement_type=data.get("measurement_type", ""),
            umh_score=data.get("umh_score", 0.0),
            umh_raw=data.get("umh_raw", {}),
            competitor_scores=data.get("competitor_scores", {}),
            comparison_type=data.get("comparison_type", ComparisonType.NOT_APPLICABLE),
        )


@dataclass
class GapEntry:
    category_id: str = ""
    category_name: str = ""
    gap_type: str = ""
    umh_score: float = 0.0
    best_competitor: str = ""
    best_competitor_score: float = 0.0
    delta: float = 0.0
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CompetitiveMatrix:
    timestamp: float = 0.0
    categories: list[CategoryScore] = field(default_factory=list)
    umh_composite: float = 0.0
    competitor_composites: dict[str, float] = field(default_factory=dict)
    umh_unique_categories: list[str] = field(default_factory=list)
    gap_analysis: list[GapEntry] = field(default_factory=list)
    market_category_comparisons: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "categories": [c.to_dict() for c in self.categories],
            "umh_composite": self.umh_composite,
            "competitor_composites": self.competitor_composites,
            "umh_unique_categories": self.umh_unique_categories,
            "gap_analysis": [g.to_dict() for g in self.gap_analysis],
            "market_category_comparisons": self.market_category_comparisons,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompetitiveMatrix:
        return cls(
            timestamp=data.get("timestamp", 0.0),
            categories=[CategoryScore.from_dict(c) for c in data.get("categories", [])],
            umh_composite=data.get("umh_composite", 0.0),
            competitor_composites=data.get("competitor_composites", {}),
            umh_unique_categories=data.get("umh_unique_categories", []),
            gap_analysis=[
                GapEntry(**g) if isinstance(g, dict) else g
                for g in data.get("gap_analysis", [])
            ],
            market_category_comparisons=data.get("market_category_comparisons", {}),
        )


CATEGORY_REGISTRY: dict[str, dict[str, Any]] = {
    "A": {"name": "Software Production", "tier": 2, "type": MeasurementType.BENCHMARK, "comparable": True},
    "B": {"name": "Autonomous Execution", "tier": 2, "type": MeasurementType.BENCHMARK, "comparable": True},
    "C": {"name": "Context Capacity", "tier": 3, "type": MeasurementType.AUDIT, "comparable": True},
    "D": {"name": "Operational Awareness", "tier": 3, "type": MeasurementType.AUDIT, "comparable": True},
    "E": {"name": "Quality Assurance", "tier": 2, "type": MeasurementType.BENCHMARK, "comparable": True},
    "F": {"name": "Capability Reuse", "tier": 2, "type": MeasurementType.BENCHMARK, "comparable": False},
    "G": {"name": "Operator Compression", "tier": 2, "type": MeasurementType.BENCHMARK, "comparable": False},
    "H": {"name": "Production Outcomes", "tier": 2, "type": MeasurementType.BENCHMARK, "comparable": True},
    "I": {"name": "Source Truth", "tier": 3, "type": MeasurementType.AUDIT, "comparable": False},
    "J": {"name": "Compounding", "tier": 2, "type": MeasurementType.BENCHMARK, "comparable": False},
    "K": {"name": "Projection Readiness", "tier": 3, "type": MeasurementType.AUDIT, "comparable": False},
    "L": {"name": "Organism Awareness", "tier": 3, "type": MeasurementType.AUDIT, "comparable": False},
    "M": {"name": "Reality Recovery", "tier": 3, "type": MeasurementType.AUDIT, "comparable": False},
    "N": {"name": "Outcome Accuracy", "tier": 2, "type": MeasurementType.BENCHMARK, "comparable": True},
    "O": {"name": "Strategic Compression", "tier": 5, "type": MeasurementType.STRATEGIC, "comparable": False},
    "P": {"name": "Empire Readiness", "tier": 3, "type": MeasurementType.AUDIT, "comparable": False},
    "Q": {"name": "Efficiency", "tier": 2, "type": MeasurementType.BENCHMARK, "comparable": True},
    "R": {"name": "Reliability", "tier": 2, "type": MeasurementType.BENCHMARK, "comparable": True},
    "S": {"name": "Human Amplification", "tier": 5, "type": MeasurementType.STRATEGIC, "comparable": False},
    "T": {"name": "Model Correspondence", "tier": 4, "type": MeasurementType.AUDIT, "comparable": False},
}

TIER_WEIGHTS: dict[int, float] = {
    1: 1.0,
    2: 0.9,
    3: 0.6,
    4: 0.7,
    5: 0.5,
}

COMPOSITE_DOMAINS: dict[str, list[str]] = {
    "software_production": ["A", "E", "Q", "R"],
    "autonomy": ["B", "G", "N"],
    "awareness": ["C", "D", "L", "M"],
    "compounding": ["F", "J", "K"],
    "outcome": ["H", "O"],
    "reality": ["I", "T"],
    "amplification": ["P", "S"],
}


class CompetitorRegistry:
    """Loads and queries competitive profiles from JSON data files."""

    def __init__(self, data_dir: str | Path = "") -> None:
        if data_dir:
            self._data_dir = Path(data_dir)
        else:
            self._data_dir = Path(_REPO_ROOT) / "data" / "umh" / "validation" / "competitive"
        self._competitors: dict[str, CompetitorProfile] = {}
        self._industry_benchmarks: dict[str, dict[str, Any]] = {}
        self._loaded = False

    def load(self) -> dict[str, CompetitorProfile]:
        competitors_path = self._data_dir / "competitors.json"
        benchmarks_path = self._data_dir / "industry_benchmarks.json"

        if competitors_path.exists():
            try:
                with open(competitors_path) as f:
                    data = json.load(f)
                for cid, cdata in data.get("competitors", {}).items():
                    cdata["competitor_id"] = cid
                    self._competitors[cid] = CompetitorProfile.from_dict(cdata)
            except Exception as e:
                logger.error("Failed to load competitors.json: %s", e)

        if benchmarks_path.exists():
            try:
                with open(benchmarks_path) as f:
                    data = json.load(f)
                self._industry_benchmarks = data.get("benchmarks", {})
            except Exception as e:
                logger.error("Failed to load industry_benchmarks.json: %s", e)

        self._loaded = True
        return self._competitors

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def get_competitor(self, competitor_id: str) -> CompetitorProfile | None:
        self._ensure_loaded()
        return self._competitors.get(competitor_id)

    def all_competitors(self) -> list[CompetitorProfile]:
        self._ensure_loaded()
        return list(self._competitors.values())

    def by_market_category(self, category: str) -> list[CompetitorProfile]:
        self._ensure_loaded()
        return [c for c in self._competitors.values() if c.market_category == category]

    def scores_for_benchmark(self, benchmark_name: str) -> dict[str, float]:
        self._ensure_loaded()
        bench = self._industry_benchmarks.get(benchmark_name, {})
        return bench.get("scores", {})

    def competitor_count(self) -> int:
        self._ensure_loaded()
        return len(self._competitors)

    def industry_benchmark_names(self) -> list[str]:
        self._ensure_loaded()
        return list(self._industry_benchmarks.keys())

    def has_capability(self, competitor_id: str, capability: str) -> bool | None:
        comp = self.get_competitor(competitor_id)
        if comp is None:
            return None
        return comp.capabilities.get(capability)
