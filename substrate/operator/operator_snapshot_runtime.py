"""Operator Snapshot Runtime — answers the 5 operator questions.

Structured around what the operator asks, not which subsystem answers:

  1. Situation  — "Where am I? What's the context?"
  2. Attention  — "What needs me right now?"
  3. Changes    — "What changed since I last looked?"
  4. Decisions  — "What's waiting for my decision?"
  5. Next Actions — "What should I do next?"

Composes existing aggregation facades (OperatorContextEngine,
ContinuityEngine, GovernedWorkRuntime, IntentRuntime) into one
unified snapshot. Creates no new authority, no new state.

Gate 4 — Workstation Convergence Runtime. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from substrate.operator.operator_attention_engine import AttentionItem

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Return types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class SituationSnapshot:
    """Answers: 'Where am I?'"""
    device: str = ""
    session_type: str = ""
    active_workspace: str = ""
    active_intents: list[dict[str, Any]] = field(default_factory=list)
    intent_alignment: dict[str, Any] = field(default_factory=dict)
    continuity_state: str = ""
    uptime_seconds: float = 0.0
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "device": self.device,
            "session_type": self.session_type,
            "active_workspace": self.active_workspace,
            "active_intents": self.active_intents,
            "intent_alignment": self.intent_alignment,
            "continuity_state": self.continuity_state,
            "uptime_seconds": self.uptime_seconds,
            "generated_at": self.generated_at,
        }



@dataclass
class ChangeEntry:
    """A single change the operator should know about."""
    domain: str = ""
    change_type: str = ""
    summary: str = ""
    source: str = ""
    timestamp: float = 0.0
    severity: str = "info"

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "change_type": self.change_type,
            "summary": self.summary,
            "source": self.source,
            "timestamp": self.timestamp,
            "severity": self.severity,
        }


@dataclass
class DecisionItem:
    """Something waiting for operator decision."""
    decision_type: str = ""
    title: str = ""
    description: str = ""
    work_id: str = ""
    risk_class: str = "low"
    waiting_since: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_type": self.decision_type,
            "title": self.title,
            "description": self.description,
            "work_id": self.work_id,
            "risk_class": self.risk_class,
            "waiting_since": self.waiting_since,
        }


@dataclass
class OperatorNextAction:
    """A lightweight recommended action for the operator snapshot view."""
    priority: int = 0
    action: str = ""
    rationale: str = ""
    capability_link: str = ""
    source_system: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "priority": self.priority,
            "action": self.action,
            "rationale": self.rationale,
            "capability_link": self.capability_link,
            "source_system": self.source_system,
        }


@dataclass
class OperatorQuestionSnapshot:
    """Complete snapshot answering all 5 operator questions."""
    situation: SituationSnapshot = field(default_factory=SituationSnapshot)
    attention: list[AttentionItem] = field(default_factory=list)
    changes: list[ChangeEntry] = field(default_factory=list)
    decisions: list[DecisionItem] = field(default_factory=list)
    next_actions: list[OperatorNextAction] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "situation": self.situation.to_dict(),
            "attention": [a.to_dict() for a in self.attention],
            "changes": [c.to_dict() for c in self.changes],
            "decisions": [d.to_dict() for d in self.decisions],
            "next_actions": [n.to_dict() for n in self.next_actions],
            "generated_at": self.generated_at,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# OperatorSnapshotRuntime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class OperatorSnapshotRuntime:
    """Aggregation runtime that answers the 5 operator questions.

    Composes existing subsystems — creates no new authority.
    All subsystem access is lazy and fault-tolerant.
    """

    def __init__(
        self,
        context_engine: Any = None,
        continuity_engine: Any = None,
        work_runtime: Any = None,
        intent_runtime: Any = None,
        event_spine: Any = None,
        gap_engine: Any = None,
    ) -> None:
        self._context_engine = context_engine
        self._continuity_engine = continuity_engine
        self._work_runtime = work_runtime
        self._intent_runtime = intent_runtime
        self._event_spine = event_spine
        self._gap_engine = gap_engine

    # ── Lazy subsystem access ────────────────────────────────────

    @property
    def context_engine(self) -> Any:
        if self._context_engine is None:
            try:
                from substrate.operator.operator_context_engine import OperatorContextEngine
                self._context_engine = OperatorContextEngine()
            except Exception:
                logger.debug("OperatorContextEngine unavailable")
        return self._context_engine

    @property
    def continuity_engine(self) -> Any:
        if self._continuity_engine is None:
            try:
                from substrate.operator.continuity_engine import ContinuityEngine
                self._continuity_engine = ContinuityEngine()
            except Exception:
                logger.debug("ContinuityEngine unavailable")
        return self._continuity_engine

    @property
    def work_runtime(self) -> Any:
        if self._work_runtime is None:
            try:
                from substrate.organism.governed_work_runtime import GovernedWorkRuntime
                self._work_runtime = GovernedWorkRuntime()
            except Exception:
                logger.debug("GovernedWorkRuntime unavailable")
        return self._work_runtime

    @property
    def intent_runtime(self) -> Any:
        if self._intent_runtime is None:
            try:
                from substrate.operator.intent_runtime import IntentRuntime
                self._intent_runtime = IntentRuntime()
            except Exception:
                logger.debug("IntentRuntime unavailable")
        return self._intent_runtime

    @property
    def event_spine(self) -> Any:
        if self._event_spine is None:
            try:
                from substrate.organism.event_spine import EventSpine
                self._event_spine = EventSpine()
            except Exception:
                logger.debug("EventSpine unavailable")
        return self._event_spine

    @property
    def gap_engine(self) -> Any:
        if self._gap_engine is None:
            try:
                from substrate.organism.strategic_gap_engine import StrategicGapEngine
                self._gap_engine = StrategicGapEngine()
            except Exception:
                logger.debug("StrategicGapEngine unavailable")
        return self._gap_engine

    # ── Full Snapshot ────────────────────────────────────────────

    def snapshot(self) -> OperatorQuestionSnapshot:
        """Build complete snapshot answering all 5 operator questions."""
        return OperatorQuestionSnapshot(
            situation=self.situation(),
            attention=self.attention(),
            changes=self.changes(),
            decisions=self.decisions(),
            next_actions=self.next_actions(),
        )

    # ── 1. Situation: "Where am I?" ─────────────────────────────

    def situation(self) -> SituationSnapshot:
        """Build situation snapshot from presence, continuity, and intent."""
        sit = SituationSnapshot()

        if self.continuity_engine is not None:
            try:
                state = self.continuity_engine.current_state()
                if isinstance(state, dict):
                    sit.device = state.get("device", "")
                    sit.session_type = state.get("session_type", "")
                    sit.continuity_state = state.get("state", "")
                    sit.uptime_seconds = state.get("uptime_seconds", 0.0)
            except Exception:
                logger.debug("ContinuityEngine.current_state failed")

        if self.context_engine is not None:
            try:
                ctx_snapshot = self.context_engine.snapshot()
                if hasattr(ctx_snapshot, "active_workspaces"):
                    workspaces = ctx_snapshot.active_workspaces
                    if workspaces:
                        sit.active_workspace = (
                            workspaces[0].get("name", "") if isinstance(workspaces[0], dict)
                            else str(workspaces[0])
                        )
            except Exception:
                logger.debug("OperatorContextEngine.snapshot failed")

        if self.intent_runtime is not None:
            try:
                ctx = self.intent_runtime.context_for_session()
                sit.active_intents = [
                    {"scope": scope, "count": len(intents)}
                    for scope, intents in ctx.get("active_intents", {}).items()
                    if intents
                ]
                sit.intent_alignment = {
                    "total_active": ctx.get("total_active", 0),
                    "scopes_with_intents": ctx.get("scopes_with_intents", []),
                    "conflict_count": ctx.get("conflict_count", 0),
                }
            except Exception:
                logger.debug("IntentRuntime.context_for_session failed")

        return sit

    # ── 2. Attention: "What needs me?" ───────────────────────────

    def attention(self, limit: int = 10) -> list[AttentionItem]:
        """Build ranked attention items from all subsystems."""
        items: list[AttentionItem] = []
        priority_counter = 0

        if self.work_runtime is not None:
            try:
                blocked = self.work_runtime.blocked()
                for b in blocked[:5]:
                    priority_counter += 1
                    items.append(AttentionItem(
                        priority=priority_counter,
                        category="blocked",
                        severity="high",
                        title=f"Blocked: {b.get('description', b.get('work_id', 'unknown'))[:80]}",
                        description=str(b.get("blockers", "")),
                        action_hint="Review blockers and unblock or escalate",
                        source_id=b.get("work_id", ""),
                        source_system="governed_work_runtime",
                        capability_link="work",
                    ))
            except Exception:
                logger.debug("GovernedWorkRuntime.blocked failed")

            try:
                recovery = self.work_runtime.recovery()
                for r in recovery[:3]:
                    priority_counter += 1
                    items.append(AttentionItem(
                        priority=priority_counter,
                        category="recovery",
                        severity="high",
                        title=f"Recovery: {r.get('description', r.get('work_id', ''))[:80]}",
                        action_hint="Review recovery options",
                        source_id=r.get("work_id", ""),
                        source_system="work_recovery_runtime",
                        capability_link="work",
                    ))
            except Exception:
                logger.debug("GovernedWorkRuntime.recovery failed")

        if self.context_engine is not None:
            try:
                ctx_snapshot = self.context_engine.snapshot()
                if hasattr(ctx_snapshot, "attention_items"):
                    for ai in ctx_snapshot.attention_items[:5]:
                        priority_counter += 1
                        items.append(AttentionItem(
                            priority=priority_counter,
                            category=ai.attention_type.value if hasattr(ai, "attention_type") else "system",
                            severity=ai.severity.value if hasattr(ai, "severity") else "medium",
                            title=ai.title if hasattr(ai, "title") else str(ai),
                            description=ai.detail if hasattr(ai, "detail") else "",
                            source_system="operator_context_engine",
                            capability_link="commandcenter",
                        ))
            except Exception:
                logger.debug("OperatorContextEngine attention items failed")

        if self.intent_runtime is not None:
            try:
                conflicts = self.intent_runtime.conflicts()
                for c in conflicts[:3]:
                    priority_counter += 1
                    items.append(AttentionItem(
                        priority=priority_counter,
                        category="misalignment",
                        severity="medium",
                        title=f"Intent conflict: {c.description[:60]}",
                        description=f"{c.conflict_type.value}: {c.description}",
                        action_hint="Resolve conflicting intents",
                        source_id=c.conflict_id,
                        source_system="intent_runtime",
                        capability_link="knowledge",
                    ))
            except Exception:
                logger.debug("IntentRuntime.conflicts failed")

        items.sort(key=lambda x: (
            {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x.severity, 4),
            x.priority,
        ))
        for i, item in enumerate(items):
            item.priority = i + 1

        return items[:limit]

    # ── 3. Changes: "What changed?" ──────────────────────────────

    def changes(self, since: float = 0.0, limit: int = 20) -> list[ChangeEntry]:
        """Recent changes from event spine and reality model."""
        if since <= 0.0:
            since = time.time() - 3600

        entries: list[ChangeEntry] = []

        if self.event_spine is not None:
            try:
                events = self.event_spine.recent(limit=limit * 2)
                for ev in events:
                    ts = ev.get("timestamp", 0.0) if isinstance(ev, dict) else getattr(ev, "timestamp", 0.0)
                    if ts >= since:
                        entries.append(ChangeEntry(
                            domain=ev.get("domain", "") if isinstance(ev, dict) else getattr(ev, "domain", ""),
                            change_type=ev.get("event_type", "") if isinstance(ev, dict) else getattr(ev, "event_type", ""),
                            summary=ev.get("summary", "") if isinstance(ev, dict) else getattr(ev, "summary", ""),
                            source=ev.get("source", "") if isinstance(ev, dict) else getattr(ev, "source", ""),
                            timestamp=ts,
                        ))
            except Exception:
                logger.debug("EventSpine.recent failed")

        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]

    # ── 4. Decisions: "What's waiting?" ──────────────────────────

    def decisions(self) -> list[DecisionItem]:
        """Pending decisions from work runtime and approval store."""
        items: list[DecisionItem] = []

        if self.work_runtime is not None:
            try:
                if self.work_runtime.work_graph is not None:
                    pending = self.work_runtime.work_graph.work_by_status("approval_pending")
                    for p in pending:
                        items.append(DecisionItem(
                            decision_type="approval",
                            title=f"Approve: {p.description[:80]}" if hasattr(p, "description") else f"Approve: {p.work_id}",
                            description=p.description if hasattr(p, "description") else "",
                            work_id=p.work_id if hasattr(p, "work_id") else "",
                            risk_class=p.risk_class if hasattr(p, "risk_class") else "low",
                            waiting_since=p.created_at if hasattr(p, "created_at") else 0.0,
                        ))
            except Exception:
                logger.debug("WorkGraph.work_by_status failed")

        items.sort(key=lambda d: (
            {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(d.risk_class, 4),
            d.waiting_since,
        ))
        return items

    # ── 5. Next Actions: "What should I do?" ─────────────────────

    def next_actions(self, limit: int = 5) -> list[OperatorNextAction]:
        """Recommended next actions based on attention + work state."""
        actions: list[OperatorNextAction] = []
        priority = 0

        attention = self.attention(limit=5)
        for item in attention:
            if item.action_hint:
                priority += 1
                actions.append(OperatorNextAction(
                    priority=priority,
                    action=item.action_hint,
                    rationale=item.title,
                    capability_link=item.capability_link,
                    source_system=item.source_system,
                ))

        if self.work_runtime is not None:
            try:
                queue = self.work_runtime.queue()
                if queue:
                    priority += 1
                    actions.append(OperatorNextAction(
                        priority=priority,
                        action=f"Execute queued work ({len(queue)} items ready)",
                        rationale="Work items in queue awaiting execution",
                        capability_link="work",
                        source_system="governed_work_runtime",
                    ))
            except Exception:
                logger.debug("GovernedWorkRuntime.queue failed")

        if self.gap_engine is not None:
            try:
                recs = self.gap_engine.recommendations(limit=3)
                for rec in recs:
                    priority += 1
                    title = rec.get("title", rec.get("description", ""))[:80] if isinstance(rec, dict) else str(rec)[:80]
                    actions.append(OperatorNextAction(
                        priority=priority,
                        action=f"Consider: {title}",
                        rationale="Strategic gap recommendation",
                        capability_link="knowledge",
                        source_system="strategic_gap_engine",
                    ))
            except Exception:
                logger.debug("StrategicGapEngine.recommendations failed")

        return actions[:limit]
