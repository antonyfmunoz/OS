"""Recommendation Engine — unified action recommendation synthesis.

Campaign 7.3. UMH substrate layer.

Executive synthesis layer ABOVE StrategicGapEngine, NextActionEngine,
and StrategicTickLoop. Merges recommendations from all three sources
into a single deduplicated, priority-sorted action list.

Does NOT generate new recommendations — delegates to existing engines.
Adds cross-engine deduplication and priority-weighted ordering.

Read-only. Deterministic. Zero LLM calls.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────


@dataclass
class UnifiedRecommendation:
    recommendation_id: str = field(default_factory=lambda: f"urec-{uuid4().hex[:8]}")
    action: str = ""
    reason: str = ""
    confidence: float = 0.5
    priority_score: float = 0.0
    source: str = ""
    entity_refs: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "action": self.action,
            "reason": self.reason,
            "confidence": round(self.confidence, 4),
            "priority_score": round(self.priority_score, 4),
            "source": self.source,
            "entity_refs": self.entity_refs,
            "created_at": self.created_at,
        }


# ── Deduplication ────────────────────────────────────────────────────


def _token_overlap(a: str, b: str) -> float:
    """Token-level Jaccard similarity between two strings."""
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


_DEDUP_THRESHOLD = 0.6


# ── Engine ────────────────────────────────────────────────────────────


class RecommendationEngine:
    """Unified recommendation synthesis — merges and deduplicates.

    Sources:
      - StrategicGapEngine → gap-based recommendations
      - NextActionEngine → evidence-based next actions
      - StrategicTickLoop → tick candidate work items
      - PriorityEngine (C7.1) → priority scores for ordering
    """

    def __init__(
        self,
        gap_engine: Any | None = None,
        next_action_engine: Any | None = None,
        tick_loop: Any | None = None,
        priority_engine: Any | None = None,
    ) -> None:
        self._gap_engine = gap_engine
        self._next_action_engine = next_action_engine
        self._tick_loop = tick_loop
        self._priority_engine = priority_engine
        self._last_recommendations: list[UnifiedRecommendation] = []

    def generate_recommendations(self) -> list[UnifiedRecommendation]:
        """Merge, deduplicate, sort. Main entry point."""
        raw: list[UnifiedRecommendation] = []

        raw.extend(self._from_gap_engine())
        raw.extend(self._from_next_action())
        raw.extend(self._from_tick_candidates())

        deduped = self._deduplicate(raw)

        self._boost_from_priorities(deduped)

        deduped.sort(key=lambda r: r.priority_score, reverse=True)
        self._last_recommendations = deduped
        return deduped

    def top(self, limit: int = 5) -> list[UnifiedRecommendation]:
        """Return top N recommendations."""
        if not self._last_recommendations:
            self.generate_recommendations()
        return self._last_recommendations[:limit]

    def next(self) -> UnifiedRecommendation | None:
        """Single highest-priority recommendation."""
        top = self.top(limit=1)
        return top[0] if top else None

    # ── Source extraction ─────────────────────────────────────────

    def _from_gap_engine(self) -> list[UnifiedRecommendation]:
        if self._gap_engine is None:
            return []
        try:
            recs = self._gap_engine.get_top_recommendations(limit=10)
            results: list[UnifiedRecommendation] = []
            for r in recs:
                if hasattr(r, "to_dict"):
                    rd = r.to_dict()
                elif isinstance(r, dict):
                    rd = r
                else:
                    continue
                results.append(UnifiedRecommendation(
                    action=rd.get("title", ""),
                    reason=rd.get("rationale", ""),
                    confidence=min(1.0, rd.get("priority_score", 0.5)),
                    priority_score=rd.get("priority_score", 0.0),
                    source="gap_engine",
                    entity_refs=rd.get("dependency_chain", []),
                    created_at=rd.get("created_at", time.time()),
                ))
            return results
        except Exception as exc:
            logger.debug("recommendation_engine: gap extraction failed: %s", exc)
            return []

    def _from_next_action(self) -> list[UnifiedRecommendation]:
        if self._next_action_engine is None:
            return []
        try:
            actions = self._next_action_engine.actions
            results: list[UnifiedRecommendation] = []
            for a in actions[:10]:
                if hasattr(a, "to_dict"):
                    ad = a.to_dict()
                elif isinstance(a, dict):
                    ad = a
                else:
                    continue
                results.append(UnifiedRecommendation(
                    action=ad.get("action", ""),
                    reason=ad.get("reason", ""),
                    confidence=min(1.0, ad.get("priority_score", 0.5)),
                    priority_score=ad.get("priority_score", 0.0),
                    source="next_action",
                    created_at=ad.get("generated_at", time.time()),
                ))
            return results
        except Exception as exc:
            logger.debug("recommendation_engine: next_action extraction failed: %s", exc)
            return []

    def _from_tick_candidates(self) -> list[UnifiedRecommendation]:
        if self._tick_loop is None:
            return []
        try:
            state = self._tick_loop.get_strategic_state()
            candidates = state.get("candidate_queue", {}).get("items", [])
            results: list[UnifiedRecommendation] = []
            for c in candidates[:10]:
                results.append(UnifiedRecommendation(
                    action=c.get("title", ""),
                    reason=f"Tick candidate: {c.get('domain', 'general')}",
                    confidence=min(1.0, c.get("priority_score", 0.3)),
                    priority_score=c.get("priority_score", 0.0),
                    source="tick_candidate",
                    created_at=c.get("proposed_at", time.time()),
                ))
            return results
        except Exception as exc:
            logger.debug("recommendation_engine: tick extraction failed: %s", exc)
            return []

    # ── Deduplication ─────────────────────────────────────────────

    def _deduplicate(self, items: list[UnifiedRecommendation]) -> list[UnifiedRecommendation]:
        """Merge items with similar action text, keeping highest confidence."""
        if not items:
            return []

        kept: list[UnifiedRecommendation] = []
        for item in items:
            merged = False
            for existing in kept:
                if _token_overlap(item.action, existing.action) >= _DEDUP_THRESHOLD:
                    if item.confidence > existing.confidence:
                        existing.confidence = item.confidence
                    if item.priority_score > existing.priority_score:
                        existing.priority_score = item.priority_score
                    for ref in item.entity_refs:
                        if ref and ref not in existing.entity_refs:
                            existing.entity_refs.append(ref)
                    merged = True
                    break
            if not merged:
                kept.append(item)
        return kept

    # ── Priority boost ────────────────────────────────────────────

    def _boost_from_priorities(self, items: list[UnifiedRecommendation]) -> None:
        """Boost recommendations that align with top priorities."""
        if self._priority_engine is None:
            return
        try:
            priorities = self._priority_engine.top(limit=5)
            priority_titles = {p.title.lower() for p in priorities}
            for item in items:
                action_lower = item.action.lower()
                for pt in priority_titles:
                    if _token_overlap(action_lower, pt) > 0.3:
                        item.priority_score = min(1.0, item.priority_score + 0.1)
                        break
        except Exception:
            pass
