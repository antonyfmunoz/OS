"""Efficiency Benchmark — capability per dollar.

Campaign 23B. Category Q. Tier 2: Production Benchmark.
Measures cost efficiency: tokens consumed, API cost, human hours saved,
and cost trend over time. A system that is 5% better but 10x more
expensive loses on this metric.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProductionCost:
    production_id: str = ""
    tokens_consumed: int = 0
    compute_seconds: float = 0.0
    api_cost_usd: float = 0.0
    human_hours: float = 0.0
    output_loc: int = 0
    capabilities_reused: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EfficiencyResult:
    productions_evaluated: int = 0
    avg_cost_per_production: float = 0.0
    avg_tokens_per_production: float = 0.0
    avg_cost_per_loc: float = 0.0
    capability_per_dollar: float = 0.0
    human_hours_saved_ratio: float = 0.0
    cost_trend: str = ""
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    total_loc: int = 0
    total_capabilities_reused: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EfficiencyBenchmark:
    """Evaluates cost efficiency from production cost records."""

    MANUAL_LOC_PER_HOUR: float = 50.0

    def evaluate(self, costs: list[ProductionCost]) -> EfficiencyResult:
        if not costs:
            return EfficiencyResult()

        count = len(costs)
        total_cost = sum(c.api_cost_usd for c in costs)
        total_tokens = sum(c.tokens_consumed for c in costs)
        total_loc = sum(c.output_loc for c in costs)
        total_caps = sum(c.capabilities_reused for c in costs)
        total_human_hours = sum(c.human_hours for c in costs)

        avg_cost_per_loc = total_cost / total_loc if total_loc > 0 else 0.0
        cap_per_dollar = total_caps / total_cost if total_cost > 0 else 0.0

        estimated_manual_hours = total_loc / self.MANUAL_LOC_PER_HOUR if self.MANUAL_LOC_PER_HOUR > 0 else 0.0
        hours_saved_ratio = estimated_manual_hours / total_human_hours if total_human_hours > 0 else 0.0

        cost_trend = self._compute_trend(costs)

        return EfficiencyResult(
            productions_evaluated=count,
            avg_cost_per_production=total_cost / count,
            avg_tokens_per_production=total_tokens / count,
            avg_cost_per_loc=avg_cost_per_loc,
            capability_per_dollar=cap_per_dollar,
            human_hours_saved_ratio=hours_saved_ratio,
            cost_trend=cost_trend,
            total_cost_usd=total_cost,
            total_tokens=total_tokens,
            total_loc=total_loc,
            total_capabilities_reused=total_caps,
        )

    def _compute_trend(self, costs: list[ProductionCost]) -> str:
        if len(costs) < 2:
            return "stable"

        mid = len(costs) // 2
        first_half = costs[:mid]
        second_half = costs[mid:]

        if not first_half or not second_half:
            return "stable"

        first_avg = sum(c.api_cost_usd for c in first_half) / len(first_half)
        second_avg = sum(c.api_cost_usd for c in second_half) / len(second_half)

        if first_avg == 0 and second_avg == 0:
            return "stable"

        threshold = 0.1
        if first_avg > 0:
            change = (second_avg - first_avg) / first_avg
        elif second_avg > 0:
            return "worsening"
        else:
            return "stable"

        if change < -threshold:
            return "improving"
        elif change > threshold:
            return "worsening"
        return "stable"
