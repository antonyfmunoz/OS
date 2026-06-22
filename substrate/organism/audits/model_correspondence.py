"""Model Correspondence Audit — predicted state vs observed reality.

Campaign 23B. Category T. Tier 4: Reality Model Audit.
Measures accuracy of UMH's reality model predictions across 5 dimensions:
runtime, project, capability, timeline, risk.

Deterministic match scoring. No LLM calls.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


CORRESPONDENCE_DOMAINS = ["runtime", "project", "capability", "timeline", "risk"]


# ---------------------------------------------------------------------------
# Match scoring
# ---------------------------------------------------------------------------

def score_match(predicted: str, observed: str) -> float:
    """Score how well a predicted state matches an observed state.

    Exact string match (case-insensitive) = 1.0
    Substring match (either direction)     = 0.7
    No match                               = 0.0
    """
    p = (predicted or "").strip().lower()
    o = (observed or "").strip().lower()

    if not p or not o:
        return 0.0
    if p == o:
        return 1.0
    if p in o or o in p:
        return 0.7
    return 0.0


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PredictionRecord:
    """A single prediction paired with its observed outcome."""

    prediction_id: str = ""
    domain: str = ""  # one of CORRESPONDENCE_DOMAINS
    predicted_state: str = ""
    observed_state: str = ""
    match_score: float = 0.0  # pre-computed or computed by audit
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def resolved_score(self) -> float:
        """Return the effective match score for this record.

        If match_score is already set (> 0), use it. Otherwise compute
        deterministically from predicted vs observed state.
        """
        if self.match_score > 0:
            return self.match_score
        return score_match(self.predicted_state, self.observed_state)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CorrespondenceDimension:
    """Per-domain correspondence metrics."""

    domain: str = ""
    predictions_evaluated: int = 0
    accuracy: float = 0.0  # average match_score
    mean_error: float = 0.0  # 1 - accuracy
    worst_miss: float = 0.0  # lowest match_score in this domain
    best_hit: float = 0.0  # highest match_score

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ModelCorrespondenceReport:
    """Complete model correspondence audit report."""

    dimensions: list[CorrespondenceDimension] = field(default_factory=list)
    total_predictions: int = 0
    overall_accuracy: float = 0.0
    best_domain: str = ""
    worst_domain: str = ""
    drift_detected: bool = False  # True if any domain accuracy < 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimensions": [d.to_dict() for d in self.dimensions],
            "total_predictions": self.total_predictions,
            "overall_accuracy": self.overall_accuracy,
            "best_domain": self.best_domain,
            "worst_domain": self.worst_domain,
            "drift_detected": self.drift_detected,
        }


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

class ModelCorrespondenceAudit:
    """Audits how well UMH's reality model predicts observed reality."""

    DRIFT_THRESHOLD = 0.5

    def run(self, predictions: list[PredictionRecord]) -> ModelCorrespondenceReport:
        """Evaluate predictions and report correspondence per domain.

        Groups predictions by domain, computes per-domain accuracy, worst
        miss, and best hit. Overall accuracy is the count-weighted average
        across domains. Drift is flagged if any domain falls below 0.5.
        """
        if not predictions:
            return ModelCorrespondenceReport()

        grouped: dict[str, list[float]] = {}
        for record in predictions:
            domain = record.domain or "unknown"
            grouped.setdefault(domain, []).append(record.resolved_score())

        dimensions: list[CorrespondenceDimension] = []
        for domain, scores in grouped.items():
            count = len(scores)
            accuracy = sum(scores) / count if count > 0 else 0.0
            dimensions.append(CorrespondenceDimension(
                domain=domain,
                predictions_evaluated=count,
                accuracy=round(accuracy, 4),
                mean_error=round(1.0 - accuracy, 4),
                worst_miss=round(min(scores), 4),
                best_hit=round(max(scores), 4),
            ))

        # Stable ordering for deterministic output.
        dimensions.sort(key=lambda d: d.domain)

        total = len(predictions)
        weighted_sum = sum(d.accuracy * d.predictions_evaluated for d in dimensions)
        overall_accuracy = weighted_sum / total if total > 0 else 0.0

        best = max(dimensions, key=lambda d: d.accuracy)
        worst = min(dimensions, key=lambda d: d.accuracy)
        drift = any(d.accuracy < self.DRIFT_THRESHOLD for d in dimensions)

        return ModelCorrespondenceReport(
            dimensions=dimensions,
            total_predictions=total,
            overall_accuracy=round(overall_accuracy, 4),
            best_domain=best.domain,
            worst_domain=worst.domain,
            drift_detected=drift,
        )
