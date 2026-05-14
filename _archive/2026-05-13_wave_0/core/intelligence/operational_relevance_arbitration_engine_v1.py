"""Operational Relevance Arbitration Engine v1.

Scores signal relevance, prioritizes operational signals,
regulates context focus, suppresses low-value noise.

Cannot mutate prioritization autonomously.
All prioritization traces to operator intent.

UMH substrate subsystem. Phase 96.8CA.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.intelligence.operational_intelligence_contracts_v1 import (
    RelevanceScore,
    OperationalFocusState,
    ContextPriorityState,
    RelevanceClass,
    _now_iso,
)


RELEVANCE_THRESHOLDS: dict[str, float] = {
    "critical": 0.9,
    "high": 0.7,
    "standard": 0.4,
    "low": 0.2,
    "noise": 0.0,
}

SOURCE_WEIGHT: dict[str, float] = {
    "resilience": 1.0,
    "scaling": 0.9,
    "environments": 0.8,
    "workflows": 0.7,
    "operations": 0.7,
    "sessions": 0.6,
    "cognition": 0.6,
    "ingress": 0.5,
    "continuity": 0.5,
    "observability": 0.4,
}

MAX_SCORED_SIGNALS: int = 100
MAX_PRIORITY_SIGNALS: int = 20
NOISE_SUPPRESSION_THRESHOLD: float = 0.2


class OperationalRelevanceArbitrationEngine:
    """Scores and arbitrates signal relevance."""

    def __init__(self, state_dir: str | Path = "data/runtime/intelligence") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._scores: list[RelevanceScore] = []
        self._focus: OperationalFocusState = OperationalFocusState()
        self._total_scored: int = 0
        self._total_suppressed: int = 0

    def score_signal(
        self,
        signal_id: str,
        source: str = "",
        severity: float = 0.0,
        recency: float = 1.0,
        operator_focus: str = "",
    ) -> RelevanceScore:
        source_w = SOURCE_WEIGHT.get(source, 0.3)
        focus_bonus = 0.2 if operator_focus and source == operator_focus else 0.0

        raw_score = (severity * 0.4) + (source_w * 0.3) + (recency * 0.2) + focus_bonus
        score = round(min(1.0, max(0.0, raw_score)), 4)

        relevance_class = self._classify(score)

        rs = RelevanceScore(
            signal_id=signal_id,
            score=score,
            relevance_class=relevance_class,
            source=source,
            reason=f"severity={severity:.2f},source_w={source_w:.2f},recency={recency:.2f}",
        )

        if score >= NOISE_SUPPRESSION_THRESHOLD:
            self._scores.append(rs)
            if len(self._scores) > MAX_SCORED_SIGNALS:
                self._scores = self._scores[-MAX_SCORED_SIGNALS:]
        else:
            self._total_suppressed += 1

        self._total_scored += 1
        return rs

    def get_priority_signals(self, limit: int = MAX_PRIORITY_SIGNALS) -> list[RelevanceScore]:
        sorted_scores = sorted(
            self._scores, key=lambda s: s.score, reverse=True,
        )
        return sorted_scores[:limit]

    def set_focus(
        self,
        focus: str,
        set_by: str = "operator",
    ) -> OperationalFocusState:
        self._focus = OperationalFocusState(
            active_focus=focus,
            focus_source=set_by,
        )
        return self._focus

    def get_focus(self) -> OperationalFocusState:
        return self._focus

    def build_priority_state(
        self,
        set_by: str = "operator",
    ) -> ContextPriorityState:
        top = self.get_priority_signals()
        return ContextPriorityState(
            ordered_signals=[s.signal_id for s in top],
            set_by=set_by,
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_scored": self._total_scored,
            "total_suppressed": self._total_suppressed,
            "active_scores": len(self._scores),
            "current_focus": self._focus.active_focus,
        }

    def _classify(self, score: float) -> str:
        if score >= RELEVANCE_THRESHOLDS["critical"]:
            return "critical"
        if score >= RELEVANCE_THRESHOLDS["high"]:
            return "high"
        if score >= RELEVANCE_THRESHOLDS["standard"]:
            return "standard"
        if score >= RELEVANCE_THRESHOLDS["low"]:
            return "low"
        return "noise"
