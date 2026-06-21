"""Benchmark 5 — Operator Compression.

Measure operator leverage — fewer touches per production over time.
Deterministic keyword-based message classification. No LLM calls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

_CORRECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bno\b", re.IGNORECASE),
    re.compile(r"\bnot that\b", re.IGNORECASE),
    re.compile(r"\bwrong\b", re.IGNORECASE),
    re.compile(r"\bstop\b", re.IGNORECASE),
    re.compile(r"\bdon'?t\b", re.IGNORECASE),
    re.compile(r"\binstead\b", re.IGNORECASE),
    re.compile(r"\bshould be\b", re.IGNORECASE),
    re.compile(r"\bactually\b", re.IGNORECASE),
    re.compile(r"\bfix\b", re.IGNORECASE),
    re.compile(r"\bbroken\b", re.IGNORECASE),
    re.compile(r"\bthat'?s not\b", re.IGNORECASE),
]

_APPROVAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\byes\b", re.IGNORECASE),
    re.compile(r"\bapproved?\b", re.IGNORECASE),
    re.compile(r"\bgo ahead\b", re.IGNORECASE),
    re.compile(r"\bship it\b", re.IGNORECASE),
    re.compile(r"\blooks good\b", re.IGNORECASE),
    re.compile(r"\blgtm\b", re.IGNORECASE),
    re.compile(r"\bperfect\b", re.IGNORECASE),
    re.compile(r"\bdo it\b", re.IGNORECASE),
    re.compile(r"\bproceed\b", re.IGNORECASE),
]


def classify_operator_message(text: str) -> str:
    """Classify an operator message as correction, approval, or information.

    Uses deterministic keyword matching with word-boundary checks.
    Correction takes priority over approval when both match.
    """
    if not text or not text.strip():
        return "information"

    for pattern in _CORRECTION_PATTERNS:
        if pattern.search(text):
            return "correction"

    for pattern in _APPROVAL_PATTERNS:
        if pattern.search(text):
            return "approval"

    return "information"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class OperatorInteraction:
    """A single operator interaction event."""

    message_id: str = ""
    timestamp: float = 0.0
    message_text: str = ""
    classification: str = ""
    production_id: str = ""

    def __post_init__(self) -> None:
        if not self.classification and self.message_text:
            self.classification = classify_operator_message(self.message_text)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "message_text": self.message_text,
            "classification": self.classification,
            "production_id": self.production_id,
        }


@dataclass
class ProductionInteractions:
    """Aggregated interaction counts for a single production."""

    production_id: str = ""
    operator_messages: int = 0
    operator_corrections: int = 0
    operator_approvals: int = 0
    operator_interventions: int = 0
    autonomous_actions: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "production_id": self.production_id,
            "operator_messages": self.operator_messages,
            "operator_corrections": self.operator_corrections,
            "operator_approvals": self.operator_approvals,
            "operator_interventions": self.operator_interventions,
            "autonomous_actions": self.autonomous_actions,
        }


@dataclass
class CompressionMetrics:
    """Computed metrics for a single production."""

    touches_per_production: float = 0.0
    autonomy_ratio: float = 0.0
    correction_rate: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "touches_per_production": round(self.touches_per_production, 4),
            "autonomy_ratio": round(self.autonomy_ratio, 4),
            "correction_rate": round(self.correction_rate, 4),
        }


@dataclass
class OperatorCompressionResult:
    """Complete benchmark result."""

    productions: int = 0
    per_production_metrics: list[dict[str, Any]] = field(default_factory=list)
    aggregate_metrics: dict[str, float] = field(default_factory=dict)
    trend: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "productions": self.productions,
            "per_production_metrics": self.per_production_metrics,
            "aggregate_metrics": self.aggregate_metrics,
            "trend": self.trend,
        }


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

class OperatorCompressionBenchmark:
    """Measures operator compression across sequential productions."""

    @staticmethod
    def compute_metrics(interactions: ProductionInteractions) -> CompressionMetrics:
        """Compute compression metrics for a single production."""
        total_touches = (
            interactions.operator_messages
            + interactions.operator_interventions
        )

        total_actions = interactions.autonomous_actions + interactions.operator_interventions
        autonomy_ratio = (
            interactions.autonomous_actions / total_actions
            if total_actions > 0
            else 0.0
        )

        correction_rate = (
            interactions.operator_corrections / interactions.operator_messages
            if interactions.operator_messages > 0
            else 0.0
        )

        return CompressionMetrics(
            touches_per_production=float(total_touches),
            autonomy_ratio=autonomy_ratio,
            correction_rate=correction_rate,
        )

    @classmethod
    def from_interactions(cls, interactions: list[OperatorInteraction]) -> dict[str, ProductionInteractions]:
        """Aggregate raw interactions into per-production summaries."""
        by_production: dict[str, ProductionInteractions] = {}
        for oi in interactions:
            pid = oi.production_id or "unknown"
            if pid not in by_production:
                by_production[pid] = ProductionInteractions(production_id=pid)
            pi = by_production[pid]
            pi.operator_messages += 1
            if oi.classification == "correction":
                pi.operator_corrections += 1
            elif oi.classification == "approval":
                pi.operator_approvals += 1
        return by_production

    def run(self, productions: list[ProductionInteractions]) -> OperatorCompressionResult:
        """Run the benchmark across a list of sequential productions.

        Returns per-production metrics, aggregate metrics, and trend.
        """
        if not productions:
            return OperatorCompressionResult()

        per_production: list[dict[str, Any]] = []
        touches_series: list[float] = []
        autonomy_series: list[float] = []
        correction_series: list[float] = []

        for pi in productions:
            m = self.compute_metrics(pi)
            per_production.append({
                "production_id": pi.production_id,
                **m.to_dict(),
            })
            touches_series.append(m.touches_per_production)
            autonomy_series.append(m.autonomy_ratio)
            correction_series.append(m.correction_rate)

        # Aggregate
        n = len(productions)
        aggregate = {
            "avg_touches_per_production": round(sum(touches_series) / n, 4),
            "avg_autonomy_ratio": round(sum(autonomy_series) / n, 4),
            "avg_correction_rate": round(sum(correction_series) / n, 4),
        }

        # Trend: slope of each metric series (positive = increasing)
        trend = {
            "touches_trend": _compute_trend(touches_series),
            "autonomy_trend": _compute_trend(autonomy_series),
            "correction_trend": _compute_trend(correction_series),
        }

        return OperatorCompressionResult(
            productions=n,
            per_production_metrics=per_production,
            aggregate_metrics=aggregate,
            trend=trend,
        )


def _compute_trend(values: list[float]) -> float:
    """Compute simple linear trend (slope) of a series.

    Positive = increasing, negative = decreasing.
    Returns 0.0 for fewer than 2 values.
    """
    n = len(values)
    if n < 2:
        return 0.0

    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n

    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return 0.0

    return round(numerator / denominator, 4)
