"""Composite Scorer — aggregate 20 categories into competitive matrix.

Campaign 23B. Phase 6: Composite Scoring + Matrix Generation.
Tier-aware weighting, market-category-aware comparison, gap analysis.
All scoring deterministic — zero LLM calls.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from substrate.organism.benchmarks.competitive import (
    CATEGORY_REGISTRY,
    COMPOSITE_DOMAINS,
    TIER_WEIGHTS,
    CategoryScore,
    ComparisonType,
    CompetitiveMatrix,
    CompetitorRegistry,
    GapEntry,
    MeasurementType,
)

logger = logging.getLogger(__name__)


class CompositeScorer:
    """Scores all 20 C23B categories and generates the competitive matrix."""

    def __init__(
        self,
        registry: CompetitorRegistry | None = None,
        category_scores: dict[str, CategoryScore] | None = None,
    ) -> None:
        self._registry = registry or CompetitorRegistry()
        self._scores: dict[str, CategoryScore] = category_scores or {}

    def register_score(self, category_id: str, score: CategoryScore) -> None:
        self._scores[category_id] = score

    def get_score(self, category_id: str) -> CategoryScore | None:
        return self._scores.get(category_id)

    def all_scores(self) -> list[CategoryScore]:
        return list(self._scores.values())

    def scored_categories(self) -> list[str]:
        return list(self._scores.keys())

    def compute_domain_score(self, domain: str) -> float:
        categories = COMPOSITE_DOMAINS.get(domain, [])
        if not categories:
            return 0.0

        weighted_sum = 0.0
        weight_sum = 0.0
        for cat_id in categories:
            cs = self._scores.get(cat_id)
            if cs is None:
                continue
            cat_info = CATEGORY_REGISTRY.get(cat_id, {})
            tier = cat_info.get("tier", 3)
            w = TIER_WEIGHTS.get(tier, 0.5)
            weighted_sum += cs.umh_score * w
            weight_sum += w

        return weighted_sum / weight_sum if weight_sum > 0 else 0.0

    def compute_composite(self, category_ids: list[str] | None = None) -> float:
        if category_ids is None:
            category_ids = list(self._scores.keys())

        weighted_sum = 0.0
        weight_sum = 0.0
        for cat_id in category_ids:
            cs = self._scores.get(cat_id)
            if cs is None:
                continue
            cat_info = CATEGORY_REGISTRY.get(cat_id, {})
            tier = cat_info.get("tier", 3)
            w = TIER_WEIGHTS.get(tier, 0.5)
            weighted_sum += cs.umh_score * w
            weight_sum += w

        return weighted_sum / weight_sum if weight_sum > 0 else 0.0

    def compute_competitor_composite(self, competitor_id: str, category_ids: list[str] | None = None) -> float:
        if category_ids is None:
            category_ids = list(self._scores.keys())

        weighted_sum = 0.0
        weight_sum = 0.0
        for cat_id in category_ids:
            cs = self._scores.get(cat_id)
            if cs is None:
                continue
            comp_score = cs.competitor_scores.get(competitor_id)
            if comp_score is None:
                continue
            cat_info = CATEGORY_REGISTRY.get(cat_id, {})
            tier = cat_info.get("tier", 3)
            w = TIER_WEIGHTS.get(tier, 0.5)
            weighted_sum += comp_score * w
            weight_sum += w

        return weighted_sum / weight_sum if weight_sum > 0 else 0.0

    def gap_analysis(self) -> list[GapEntry]:
        gaps: list[GapEntry] = []
        for cat_id, cs in self._scores.items():
            cat_info = CATEGORY_REGISTRY.get(cat_id, {})
            if not cs.competitor_scores:
                continue

            valid_scores = {
                cid: s for cid, s in cs.competitor_scores.items()
                if s is not None
            }
            if not valid_scores:
                continue

            best_cid = max(valid_scores, key=lambda k: valid_scores[k])
            best_score = valid_scores[best_cid]
            delta = cs.umh_score - best_score

            if delta < 0:
                gap_type = "trailing"
            elif delta > 0:
                gap_type = "leading"
            else:
                gap_type = "parity"

            recommendation = ""
            if gap_type == "trailing" and abs(delta) > 0.2:
                recommendation = "significant gap — prioritize improvement"
            elif gap_type == "trailing":
                recommendation = "minor gap — incremental improvement"
            elif gap_type == "leading" and delta > 0.2:
                recommendation = "strong lead — maintain advantage"

            gaps.append(GapEntry(
                category_id=cat_id,
                category_name=cat_info.get("name", cat_id),
                gap_type=gap_type,
                umh_score=cs.umh_score,
                best_competitor=best_cid,
                best_competitor_score=best_score,
                delta=round(delta, 4),
                recommendation=recommendation,
            ))

        return gaps

    def umh_unique_categories(self) -> list[str]:
        unique: list[str] = []
        for cat_id, cs in self._scores.items():
            if not cs.competitor_scores:
                unique.append(cat_id)
                continue
            all_none = all(v is None for v in cs.competitor_scores.values())
            if all_none:
                unique.append(cat_id)
        return unique

    def market_category_comparison(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        competitors = self._registry.all_competitors()

        by_mc: dict[str, list[str]] = {}
        for c in competitors:
            by_mc.setdefault(c.market_category, []).append(c.competitor_id)

        for mc, comp_ids in by_mc.items():
            mc_composites: dict[str, float] = {}
            for cid in comp_ids:
                score = self.compute_competitor_composite(cid)
                if score > 0:
                    mc_composites[cid] = round(score, 4)

            umh_score = self.compute_composite()
            ranking = sorted(
                [("umh", umh_score)] + [(cid, s) for cid, s in mc_composites.items()],
                key=lambda x: x[1],
                reverse=True,
            )

            result[mc] = {
                "competitors": comp_ids,
                "composites": mc_composites,
                "umh_composite": round(umh_score, 4),
                "ranking": [{"id": r[0], "score": round(r[1], 4)} for r in ranking],
                "umh_rank": next((i + 1 for i, r in enumerate(ranking) if r[0] == "umh"), 0),
            }

        return result

    def generate_matrix(self) -> CompetitiveMatrix:
        categories = self.all_scores()

        domain_scores: dict[str, float] = {}
        for domain in COMPOSITE_DOMAINS:
            domain_scores[domain] = round(self.compute_domain_score(domain), 4)

        competitors = self._registry.all_competitors()
        competitor_composites: dict[str, float] = {}
        for c in competitors:
            score = self.compute_competitor_composite(c.competitor_id)
            if score > 0:
                competitor_composites[c.competitor_id] = round(score, 4)

        return CompetitiveMatrix(
            timestamp=time.time(),
            categories=categories,
            umh_composite=round(self.compute_composite(), 4),
            competitor_composites=competitor_composites,
            umh_unique_categories=self.umh_unique_categories(),
            gap_analysis=self.gap_analysis(),
            market_category_comparisons=self.market_category_comparison(),
        )

    def summary(self) -> dict[str, Any]:
        matrix = self.generate_matrix()
        gaps = matrix.gap_analysis

        leading = [g for g in gaps if g.gap_type == "leading"]
        trailing = [g for g in gaps if g.gap_type == "trailing"]
        parity = [g for g in gaps if g.gap_type == "parity"]

        domain_scores: dict[str, float] = {}
        for domain in COMPOSITE_DOMAINS:
            domain_scores[domain] = round(self.compute_domain_score(domain), 4)

        return {
            "umh_composite": matrix.umh_composite,
            "domain_scores": domain_scores,
            "categories_scored": len(self._scores),
            "categories_total": len(CATEGORY_REGISTRY),
            "unique_categories": len(matrix.umh_unique_categories),
            "leading_count": len(leading),
            "trailing_count": len(trailing),
            "parity_count": len(parity),
            "competitor_count": len(matrix.competitor_composites),
        }
