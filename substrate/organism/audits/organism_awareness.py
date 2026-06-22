"""Audit — Organism Self-Awareness.

Campaign 23B — Category L Audit.
Tier 3: organism audit (inspects system state, generates a report — no task execution).

Measures how accurately the organism's reported view of itself matches reality
across four dimensions: self_model, runtime, workforce, and subsystem_count.
All metrics deterministic. No LLM calls.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


_DIMENSION_GROUPS = ("self_model", "runtime", "workforce", "subsystem")


@dataclass
class AwarenessDimension:
    """Reported vs actual value for a single awareness dimension."""

    dimension: str = ""
    reported_value: Any = None
    actual_value: Any = None
    match: bool = False
    accuracy: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrganismAwarenessReport:
    """Result of an organism-self-awareness audit."""

    dimensions_checked: int = 0
    self_model_accuracy: float = 0.0
    runtime_accuracy: float = 0.0
    workforce_accuracy: float = 0.0
    subsystem_count_accuracy: float = 0.0
    overall_accuracy: float = 0.0
    details: list[AwarenessDimension] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OrganismAwarenessAudit:
    """Audits the accuracy of the organism's self-knowledge."""

    def __init__(self, test_mode: bool = False) -> None:
        self._test_mode = test_mode

    def run(
        self, dimensions: list[AwarenessDimension] | None = None
    ) -> OrganismAwarenessReport:
        """Run the organism-self-awareness audit.

        Each dimension's accuracy is scored: exact match for strings/bools,
        proximity for numerics. Dimensions are grouped by name prefix into the
        four reported accuracy categories.
        """
        dims = list(dimensions or [])

        if not dims:
            return OrganismAwarenessReport()

        for dim in dims:
            dim.accuracy, dim.match = self._score(dim.reported_value, dim.actual_value)

        grouped: dict[str, list[float]] = {g: [] for g in _DIMENSION_GROUPS}
        for dim in dims:
            group = self._group_for(dim.dimension)
            if group is not None:
                grouped[group].append(dim.accuracy)

        def avg(values: list[float]) -> float:
            return round(sum(values) / len(values), 4) if values else 0.0

        self_model_acc = avg(grouped["self_model"])
        runtime_acc = avg(grouped["runtime"])
        workforce_acc = avg(grouped["workforce"])
        subsystem_acc = avg(grouped["subsystem"])

        category_values = [self_model_acc, runtime_acc, workforce_acc, subsystem_acc]
        overall = round(sum(category_values) / len(category_values), 4)

        return OrganismAwarenessReport(
            dimensions_checked=len(dims),
            self_model_accuracy=self_model_acc,
            runtime_accuracy=runtime_acc,
            workforce_accuracy=workforce_acc,
            subsystem_count_accuracy=subsystem_acc,
            overall_accuracy=overall,
            details=dims,
        )

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    @staticmethod
    def _group_for(dimension: str) -> str | None:
        name = (dimension or "").lower()
        for group in _DIMENSION_GROUPS:
            if name.startswith(group):
                return group
        return None

    @staticmethod
    def _score(reported: Any, actual: Any) -> tuple[float, bool]:
        if OrganismAwarenessAudit._is_numeric(reported) and OrganismAwarenessAudit._is_numeric(actual):
            r = float(reported)
            a = float(actual)
            denom = max(abs(r), abs(a), 1.0)
            accuracy = round(1.0 - min(1.0, abs(r - a) / denom), 4)
            return accuracy, r == a
        # Exact match for strings / bools / everything else.
        match = reported == actual
        return (1.0 if match else 0.0), match

    @staticmethod
    def _is_numeric(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
