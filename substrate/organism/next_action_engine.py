"""Next Action Engine — evidence-based action recommender.

Answers: "What should happen next?"

Synthesizes signals from:
  - leverage opportunities (what has highest impact)
  - bottlenecks (what is blocked)
  - pending approvals (what needs operator attention)
  - readiness gaps (what dimensions need improvement)
  - execution state (what is running / stalled)

Every recommended action must:
  - cite evidence (observed system state)
  - explain reasoning (why this action matters)
  - rank by priority (computed from impact + urgency + effort)

Deterministic. No LLM dependency.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ActionPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionCategory(str, Enum):
    FIX = "fix"
    APPROVE = "approve"
    PROMOTE = "promote"
    INVESTIGATE = "investigate"
    CONFIGURE = "configure"
    BUILD = "build"
    DEPLOY = "deploy"


@dataclass
class ActionEvidence:
    source: str
    signal: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "signal": self.signal, "detail": self.detail}


@dataclass
class NextAction:
    action_id: str = field(default_factory=lambda: f"act-{uuid4().hex[:8]}")
    priority: ActionPriority = ActionPriority.MEDIUM
    priority_score: float = 0.0
    action: str = ""
    category: ActionCategory = ActionCategory.INVESTIGATE
    reason: str = ""
    evidence: list[ActionEvidence] = field(default_factory=list)
    estimated_effort: str = ""
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "priority": self.priority.value,
            "priority_score": round(self.priority_score, 3),
            "action": self.action,
            "category": self.category.value,
            "reason": self.reason,
            "evidence": [e.to_dict() for e in self.evidence],
            "estimated_effort": self.estimated_effort,
            "generated_at": self.generated_at,
        }


def _score_to_priority(score: float) -> ActionPriority:
    if score >= 0.8:
        return ActionPriority.CRITICAL
    if score >= 0.6:
        return ActionPriority.HIGH
    if score >= 0.35:
        return ActionPriority.MEDIUM
    return ActionPriority.LOW


class NextActionEngine:
    """Generates ranked next actions from organism intelligence signals.

    Consumes leverage opportunities, bottlenecks, approvals, readiness
    gaps, and execution state. Deduplicates by theme — multiple bottlenecks
    of the same category collapse into one action.
    """

    def __init__(self, event_spine: Any | None = None) -> None:
        self._event_spine = event_spine
        self._actions: list[NextAction] = []
        self._last_computed: float = 0.0

    def compute(
        self,
        leverage_opportunities: list[dict[str, Any]] | None = None,
        bottlenecks: list[dict[str, Any]] | None = None,
        pending_approvals: int = 0,
        readiness_gaps: list[dict[str, Any]] | None = None,
        execution_state: dict[str, Any] | None = None,
    ) -> list[NextAction]:
        actions: list[NextAction] = []
        seen_themes: set[str] = set()

        if leverage_opportunities:
            for opp in leverage_opportunities[:5]:
                theme = opp.get("category", "unknown")
                if theme in seen_themes:
                    continue
                seen_themes.add(theme)

                score = opp.get("impact_score", 0)
                confidence = opp.get("confidence", 0.5)
                adjusted = score * confidence

                evidence_items = [
                    ActionEvidence(
                        source=e.get("source", "leverage_engine"),
                        signal=e.get("signal", ""),
                        detail=e.get("detail", ""),
                    )
                    for e in opp.get("evidence", [])
                ]

                actions.append(NextAction(
                    priority=_score_to_priority(adjusted),
                    priority_score=adjusted,
                    action=opp.get("action", ""),
                    category=self._infer_category(opp.get("action", "")),
                    reason=opp.get("reasoning", opp.get("impact_description", "")),
                    evidence=evidence_items,
                    estimated_effort=self._estimate_effort(opp),
                ))

        if pending_approvals > 0 and "approval_processing" not in seen_themes:
            seen_themes.add("approval_processing")
            score = min(1.0, 0.4 + 0.04 * pending_approvals)
            actions.append(NextAction(
                priority=_score_to_priority(score),
                priority_score=score,
                action=f"Review {pending_approvals} pending approval(s)",
                category=ActionCategory.APPROVE,
                reason=f"{pending_approvals} actions await operator approval, blocking downstream execution",
                evidence=[ActionEvidence(
                    source="approval_store",
                    signal="pending_count",
                    detail=f"{pending_approvals} items in approval queue",
                )],
                estimated_effort="5-15 minutes",
            ))

        if readiness_gaps:
            for gap in readiness_gaps[:3]:
                dim = gap.get("dimension", "unknown")
                theme = f"readiness:{dim}"
                if theme in seen_themes:
                    continue
                seen_themes.add(theme)

                score_val = gap.get("score", 50) / 100.0
                gap_severity = 1.0 - score_val
                adjusted = gap_severity * 0.7

                actions.append(NextAction(
                    priority=_score_to_priority(adjusted),
                    priority_score=adjusted,
                    action=f"Improve {dim.replace('_', ' ')} readiness",
                    category=ActionCategory.BUILD if gap_severity > 0.5 else ActionCategory.CONFIGURE,
                    reason=gap.get("explanation", f"{dim} readiness at {gap.get('score', 0)}%"),
                    evidence=[ActionEvidence(
                        source="readiness_model",
                        signal=f"readiness.{dim}",
                        detail=f"Score: {gap.get('score', 0)}/100, gap factors: {', '.join(gap.get('gap_factors', [])[:3])}",
                    )],
                    estimated_effort=self._effort_from_gap(gap_severity),
                ))

        if execution_state:
            stalled = execution_state.get("stalled_count", 0)
            if stalled > 0 and "stalled_execution" not in seen_themes:
                seen_themes.add("stalled_execution")
                actions.append(NextAction(
                    priority=ActionPriority.HIGH,
                    priority_score=0.7,
                    action=f"Unblock {stalled} stalled execution(s)",
                    category=ActionCategory.INVESTIGATE,
                    reason=f"{stalled} tasks are stalled with no progress — likely blocked on dependencies or missing resources",
                    evidence=[ActionEvidence(
                        source="execution_state",
                        signal="stalled_count",
                        detail=f"{stalled} execution(s) with no progress",
                    )],
                    estimated_effort="15-30 minutes",
                ))

        actions.sort(key=lambda a: a.priority_score, reverse=True)

        previous = self._actions
        self._actions = actions
        self._last_computed = time.time()

        if self._event_spine is not None and actions != previous:
            from substrate.organism.event_spine import EventDomain
            self._event_spine.emit(
                EventDomain.OBSERVABILITY,
                "next_action_changed",
                "next_action_engine",
                {
                    "count": len(actions),
                    "top": actions[0].to_dict() if actions else None,
                },
            )

        return actions

    def _infer_category(self, action_text: str) -> ActionCategory:
        text = action_text.lower()
        if any(w in text for w in ("fix", "resolve", "repair")):
            return ActionCategory.FIX
        if any(w in text for w in ("approve", "review", "process")):
            return ActionCategory.APPROVE
        if any(w in text for w in ("promote", "upgrade", "advance")):
            return ActionCategory.PROMOTE
        if any(w in text for w in ("deploy", "release", "publish")):
            return ActionCategory.DEPLOY
        if any(w in text for w in ("configure", "tune", "adjust")):
            return ActionCategory.CONFIGURE
        if any(w in text for w in ("build", "create", "implement", "improve")):
            return ActionCategory.BUILD
        return ActionCategory.INVESTIGATE

    def _estimate_effort(self, opp: dict[str, Any]) -> str:
        score = opp.get("impact_score", 0)
        if score > 0.8:
            return "30-60 minutes"
        if score > 0.5:
            return "15-30 minutes"
        return "5-15 minutes"

    def _effort_from_gap(self, severity: float) -> str:
        if severity > 0.7:
            return "1-2 hours"
        if severity > 0.4:
            return "30-60 minutes"
        return "15-30 minutes"

    @property
    def actions(self) -> list[NextAction]:
        return list(self._actions)

    def top(self, n: int = 5) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self._actions[:n]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_actions": len(self._actions),
            "last_computed": self._last_computed,
            "actions": [a.to_dict() for a in self._actions],
        }
