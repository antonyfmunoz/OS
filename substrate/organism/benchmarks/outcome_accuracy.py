"""Outcome Accuracy Benchmark — did completed work achieve original intent?

Campaign 23B. Category N. Tier 2: Production Benchmark.
Measures whether productions actually satisfy acceptance criteria,
pass tests, and deploy successfully.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkOutcomeRecord:
    production_id: str = ""
    original_intent: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    criteria_met: list[bool] = field(default_factory=list)
    tests_passed: bool = False
    deployed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OutcomeAccuracyResult:
    productions_evaluated: int = 0
    intent_achievement_rate: float = 0.0
    deployment_success_rate: float = 0.0
    test_pass_rate: float = 0.0
    full_achievement_count: int = 0
    partial_achievement_count: int = 0
    zero_achievement_count: int = 0
    total_criteria: int = 0
    total_criteria_met: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OutcomeAccuracyBenchmark:
    """Evaluates outcome accuracy from production records."""

    def evaluate(self, outcomes: list[BenchmarkOutcomeRecord]) -> OutcomeAccuracyResult:
        if not outcomes:
            return OutcomeAccuracyResult()

        count = len(outcomes)
        total_criteria = 0
        total_met = 0
        full_count = 0
        partial_count = 0
        zero_count = 0
        deployed_count = sum(1 for o in outcomes if o.deployed)
        tests_passed_count = sum(1 for o in outcomes if o.tests_passed)

        for o in outcomes:
            n_criteria = len(o.acceptance_criteria)
            n_met = sum(1 for m in o.criteria_met if m)
            total_criteria += n_criteria
            total_met += n_met

            if n_criteria == 0:
                zero_count += 1
            elif n_met == n_criteria:
                full_count += 1
            elif n_met > 0:
                partial_count += 1
            else:
                zero_count += 1

        return OutcomeAccuracyResult(
            productions_evaluated=count,
            intent_achievement_rate=total_met / total_criteria if total_criteria > 0 else 0.0,
            deployment_success_rate=deployed_count / count,
            test_pass_rate=tests_passed_count / count,
            full_achievement_count=full_count,
            partial_achievement_count=partial_count,
            zero_achievement_count=zero_count,
            total_criteria=total_criteria,
            total_criteria_met=total_met,
        )
