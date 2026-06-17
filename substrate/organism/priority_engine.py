"""Priority Engine — deterministic priority synthesis.

Campaign 7.1. UMH substrate layer.

Executive synthesis layer ABOVE StrategicGapEngine. Merges priority
signals from gap analysis, runtime awareness (blocked work), knowledge
awareness (constraints), and tick loop (drift/candidates) into a single
ordered priority list.

Does NOT reimplement gap detection — delegates to StrategicGapEngine.
Does NOT reimplement drift detection — delegates to StrategicTickLoop.

Read-only. Deterministic. Zero LLM calls.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ── Severity → weight map ────────────────────────────────────────────

_SEVERITY_WEIGHTS: dict[str, float] = {
    "critical": 1.0,
    "high": 0.75,
    "medium": 0.5,
    "low": 0.25,
}

# Days-since-creation urgency curve: 0 days → 0.0, 30+ days → 1.0
_URGENCY_MAX_DAYS = 30.0


# ── Types ─────────────────────────────────────────────────────────────


@dataclass
class PrioritizedItem:
    priority_id: str = field(default_factory=lambda: f"pri-{uuid4().hex[:8]}")
    title: str = ""
    rationale: str = ""
    score: float = 0.0
    impact_score: float = 0.0
    urgency_score: float = 0.0
    source: str = ""
    entity_refs: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "priority_id": self.priority_id,
            "title": self.title,
            "rationale": self.rationale,
            "score": round(self.score, 4),
            "impact_score": round(self.impact_score, 4),
            "urgency_score": round(self.urgency_score, 4),
            "source": self.source,
            "entity_refs": self.entity_refs,
            "created_at": self.created_at,
        }


# ── Engine ────────────────────────────────────────────────────────────


class PriorityEngine:
    """Merges priority signals into a single ordered list.

    Sources:
      - StrategicGapEngine → gaps (impact from severity)
      - RuntimeAwareness → blocked work items
      - KnowledgeAwareness → constraints that affect priorities
      - StrategicTickLoop → drift warnings (urgency signal)
    """

    def __init__(
        self,
        gap_engine: Any | None = None,
        runtime_awareness: Any | None = None,
        knowledge_awareness: Any | None = None,
        tick_loop: Any | None = None,
    ) -> None:
        self._gap_engine = gap_engine
        self._runtime_awareness = runtime_awareness
        self._knowledge_awareness = knowledge_awareness
        self._tick_loop = tick_loop
        self._last_priorities: list[PrioritizedItem] = []

    def compute_priorities(self) -> list[PrioritizedItem]:
        """Merge all sources, score, sort. Main entry point."""
        items: list[PrioritizedItem] = []

        items.extend(self._priorities_from_gaps())
        items.extend(self._priorities_from_blocked())
        items.extend(self._priorities_from_drift())

        blocker_titles = {
            i.title for i in items if i.source == "blocker"
        }
        constraint_boost = self._constraint_boost_set()

        for item in items:
            is_blocking = item.title in blocker_titles and item.source != "blocker"
            is_constrained = any(c in item.title.lower() for c in constraint_boost)

            blocker_weight = 1.0 if (item.source == "blocker" or is_blocking) else 0.0
            approval_weight = 1.0 if item.source == "approval" else 0.0
            constrained_bump = 0.1 if is_constrained else 0.0

            item.score = min(1.0, (
                item.impact_score * 0.35
                + item.urgency_score * 0.30
                + blocker_weight * 0.20
                + approval_weight * 0.15
                + constrained_bump
            ))

        items.sort(key=lambda i: i.score, reverse=True)
        self._last_priorities = items
        return items

    def top(self, limit: int = 5) -> list[PrioritizedItem]:
        """Return top N priorities from last computation."""
        if not self._last_priorities:
            self.compute_priorities()
        return self._last_priorities[:limit]

    def by_source(self, source: str) -> list[PrioritizedItem]:
        """Filter priorities by source type."""
        if not self._last_priorities:
            self.compute_priorities()
        return [i for i in self._last_priorities if i.source == source]

    # ── Source extraction (delegates to engines) ──────────────────

    def _priorities_from_gaps(self) -> list[PrioritizedItem]:
        if self._gap_engine is None:
            return []
        try:
            analysis = self._gap_engine.analyze()
            gaps = analysis.get("gaps", [])
            items: list[PrioritizedItem] = []
            for gap in gaps[:20]:
                severity = gap.get("severity", "low")
                impact = _SEVERITY_WEIGHTS.get(severity, 0.25)
                created = gap.get("created_at", time.time())
                urgency = self._urgency_from_age(created)
                items.append(PrioritizedItem(
                    title=gap.get("title", ""),
                    rationale=gap.get("description", ""),
                    impact_score=impact,
                    urgency_score=urgency,
                    source="gap",
                    entity_refs=gap.get("blocking_goals", []),
                    created_at=created,
                ))
            return items
        except Exception as exc:
            logger.debug("priority_engine: gap extraction failed: %s", exc)
            return []

    def _priorities_from_blocked(self) -> list[PrioritizedItem]:
        if self._runtime_awareness is None:
            return []
        try:
            blocked = self._runtime_awareness.blocked_work()
            items: list[PrioritizedItem] = []
            for work in blocked:
                title = work.get("title", work.get("packet_id", "blocked-item"))
                items.append(PrioritizedItem(
                    title=title,
                    rationale=work.get("reason", work.get("blocker_detail", "blocked")),
                    impact_score=0.75,
                    urgency_score=0.8,
                    source="blocker",
                    entity_refs=work.get("entity_refs", []),
                    created_at=work.get("created_at", time.time()),
                ))
            return items
        except Exception as exc:
            logger.debug("priority_engine: blocked extraction failed: %s", exc)
            return []

    def _priorities_from_drift(self) -> list[PrioritizedItem]:
        if self._tick_loop is None:
            return []
        try:
            state = self._tick_loop.get_strategic_state()
            warnings = state.get("drift_warnings", [])
            items: list[PrioritizedItem] = []
            for w in warnings:
                severity = w.get("severity", "warning")
                impact = _SEVERITY_WEIGHTS.get(severity, 0.25)
                items.append(PrioritizedItem(
                    title=w.get("goal_title", w.get("message", "drift")),
                    rationale=w.get("message", ""),
                    impact_score=impact,
                    urgency_score=min(1.0, w.get("days_stagnant", 0) / _URGENCY_MAX_DAYS),
                    source="drift",
                    entity_refs=[w.get("goal_id", "")] if w.get("goal_id") else [],
                    created_at=w.get("created_at", time.time()),
                ))
            return items
        except Exception as exc:
            logger.debug("priority_engine: drift extraction failed: %s", exc)
            return []

    def _constraint_boost_set(self) -> set[str]:
        """Extract constraint keywords for priority boosting."""
        if self._knowledge_awareness is None:
            return set()
        try:
            constraints = self._knowledge_awareness.find_constraints()
            keywords: set[str] = set()
            for c in constraints:
                summary = ""
                if hasattr(c, "summary"):
                    summary = c.summary
                elif isinstance(c, dict):
                    summary = c.get("summary", "")
                for word in summary.lower().split():
                    if len(word) > 3:
                        keywords.add(word)
            return keywords
        except Exception:
            return set()

    @staticmethod
    def _urgency_from_age(created_at: float) -> float:
        """Days-since-creation urgency: 0 days → 0.0, 30+ days → 1.0."""
        age_days = (time.time() - created_at) / 86400.0
        return min(1.0, max(0.0, age_days / _URGENCY_MAX_DAYS))
