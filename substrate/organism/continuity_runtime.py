"""Continuity Runtime — operational continuity engine for UMH.

Phase 7. Provides persistent cognitive workspace so the operator can
leave and return without manually rebuilding context. The runtime
maintains a ContinuitySnapshot of all active work, a ResumeStateEngine
for deterministic state diffing, a WorkContinuityGraph for lineage
reconstruction, an OperatorBriefGenerator for 30-second executive
briefings, a TimelineEngine for decision/event chronology, and an
AttentionModel for tracking operator availability state.

Deterministic-first: all continuity logic uses state comparison and
data aggregation. No LLM dependency in core path.

Composes existing primitives:
  - GoalRegistry / Goal (strategic_gap_engine) — active objectives
  - StrategicGapEngine (strategic_gap_engine) — gaps + recommendations
  - StrategicTickLoop (strategic_tick_loop) — loop state + candidates
  - ProjectionEngine (projection_engine) — projections + risks + opportunities
  - EmpireRouter / RealitySnapshot (empire_router) — current reality
  - ApprovalStore (approval_store) — pending approvals
  - WorkPacket (work_packet) — work packet state
  - ProfileMode (profile_modes) — operator profile
  - DevicePresenceRegistry (device_presence) — operator sessions

Governance boundary: may observe, record, summarize, recommend.
May NOT execute, approve, modify goals, or override governance.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


def _repo_root() -> str:
    return os.environ.get("UMH_ROOT", "/opt/OS")


def _continuity_data_dir() -> str:
    return os.path.join(_repo_root(), "data", "umh", "continuity")


def _ensure_dirs() -> None:
    base = _continuity_data_dir()
    for sub in ("snapshots", "briefs", "timeline", "sessions"):
        os.makedirs(os.path.join(base, sub), exist_ok=True)


# ── Enums ──────────────────────────────────────────────────────────────


class AttentionState(str, Enum):
    ACTIVE = "active"
    AWAY = "away"
    OFFLINE = "offline"
    SLEEPING = "sleeping"

    @property
    def is_present(self) -> bool:
        return self == AttentionState.ACTIVE

    @property
    def is_absent(self) -> bool:
        return self in (AttentionState.AWAY, AttentionState.OFFLINE, AttentionState.SLEEPING)


class TimelineEventType(str, Enum):
    DECISION = "decision"
    OUTCOME = "outcome"
    LEARNING = "learning"
    APPROVAL = "approval"
    EXECUTION = "execution"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    ATTENTION_CHANGE = "attention_change"
    OBJECTIVE_UPDATE = "objective_update"
    WORK_COMPLETED = "work_completed"
    WORK_BLOCKED = "work_blocked"
    RISK_DETECTED = "risk_detected"
    OPPORTUNITY_DETECTED = "opportunity_detected"


class ChangeCategory(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    AVAILABLE = "available"
    NEEDS_REVIEW = "needs_review"
    NEW_RISK = "new_risk"
    NEW_OPPORTUNITY = "new_opportunity"
    GOAL_PROGRESS = "goal_progress"
    DRIFT_WARNING = "drift_warning"


class BriefSection(str, Enum):
    MISSION_STATUS = "mission_status"
    CURRENT_REALITY = "current_reality"
    CRITICAL_CHANGES = "critical_changes"
    PENDING_DECISIONS = "pending_decisions"
    RECOMMENDED_ACTIONS = "recommended_actions"


# ── Data Models ────────────────────────────────────────────────────────


@dataclass
class ContinuitySnapshot:
    """Canonical snapshot of all active operational state."""

    snapshot_id: str = ""
    captured_at: float = 0.0
    active_profile_mode: str = ""
    active_system_modes: list[str] = field(default_factory=list)
    active_session_id: str = ""
    active_objectives: list[dict[str, Any]] = field(default_factory=list)
    active_loops: list[dict[str, Any]] = field(default_factory=list)
    active_work_packets: list[dict[str, Any]] = field(default_factory=list)
    blocked_items: list[dict[str, Any]] = field(default_factory=list)
    approvals_waiting: list[dict[str, Any]] = field(default_factory=list)
    active_projections: list[dict[str, Any]] = field(default_factory=list)
    active_risks: list[dict[str, Any]] = field(default_factory=list)
    active_opportunities: list[dict[str, Any]] = field(default_factory=list)
    current_recommendations: list[dict[str, Any]] = field(default_factory=list)
    last_operator_interaction: float = 0.0
    operator_attention: str = "active"
    reality_hash: str = ""

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            self.snapshot_id = f"snap-{uuid4().hex[:12]}"
        if not self.captured_at:
            self.captured_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "captured_at": self.captured_at,
            "active_profile_mode": self.active_profile_mode,
            "active_system_modes": self.active_system_modes,
            "active_session_id": self.active_session_id,
            "active_objectives": self.active_objectives,
            "active_loops": self.active_loops,
            "active_work_packets": self.active_work_packets,
            "blocked_items": self.blocked_items,
            "approvals_waiting": self.approvals_waiting,
            "active_projections": self.active_projections,
            "active_risks": self.active_risks,
            "active_opportunities": self.active_opportunities,
            "current_recommendations": self.current_recommendations,
            "last_operator_interaction": self.last_operator_interaction,
            "operator_attention": self.operator_attention,
            "reality_hash": self.reality_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContinuitySnapshot:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def compute_hash(self) -> str:
        content = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class TimelineEvent:
    """A single event in the operational timeline."""

    event_id: str = ""
    event_type: str = ""
    timestamp: float = 0.0
    summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    related_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = f"evt-{uuid4().hex[:12]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "summary": self.summary,
            "details": self.details,
            "related_ids": self.related_ids,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimelineEvent:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ResumeReport:
    """What changed between two snapshots — produced by ResumeStateEngine."""

    generated_at: float = 0.0
    absence_duration_seconds: float = 0.0
    changes: list[dict[str, Any]] = field(default_factory=list)
    completed: list[dict[str, Any]] = field(default_factory=list)
    failed: list[dict[str, Any]] = field(default_factory=list)
    blocked: list[dict[str, Any]] = field(default_factory=list)
    became_available: list[dict[str, Any]] = field(default_factory=list)
    needs_review: list[dict[str, Any]] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.generated_at:
            self.generated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "absence_duration_seconds": self.absence_duration_seconds,
            "changes": self.changes,
            "completed": self.completed,
            "failed": self.failed,
            "blocked": self.blocked,
            "became_available": self.became_available,
            "needs_review": self.needs_review,
            "recommended_actions": self.recommended_actions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResumeReport:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def total_changes(self) -> int:
        return (
            len(self.completed)
            + len(self.failed)
            + len(self.blocked)
            + len(self.became_available)
            + len(self.needs_review)
        )

    @property
    def has_critical_changes(self) -> bool:
        return len(self.failed) > 0 or len(self.blocked) > 0 or len(self.needs_review) > 0


@dataclass
class OperatorBrief:
    """30-second executive briefing packet."""

    brief_id: str = ""
    generated_at: float = 0.0
    mission_status: str = ""
    current_reality: str = ""
    critical_changes: list[str] = field(default_factory=list)
    pending_decisions: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    active_objectives_count: int = 0
    active_work_count: int = 0
    blocked_count: int = 0
    approval_count: int = 0
    risk_count: int = 0
    opportunity_count: int = 0

    def __post_init__(self) -> None:
        if not self.brief_id:
            self.brief_id = f"brief-{uuid4().hex[:12]}"
        if not self.generated_at:
            self.generated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "brief_id": self.brief_id,
            "generated_at": self.generated_at,
            "mission_status": self.mission_status,
            "current_reality": self.current_reality,
            "critical_changes": self.critical_changes,
            "pending_decisions": self.pending_decisions,
            "recommended_actions": self.recommended_actions,
            "active_objectives_count": self.active_objectives_count,
            "active_work_count": self.active_work_count,
            "blocked_count": self.blocked_count,
            "approval_count": self.approval_count,
            "risk_count": self.risk_count,
            "opportunity_count": self.opportunity_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OperatorBrief:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class WorkLineage:
    """Graph relationship: objective → workpacket → outcome → projection → recommendation."""

    lineage_id: str = ""
    objective_id: str = ""
    objective_title: str = ""
    work_packet_ids: list[str] = field(default_factory=list)
    outcome_ids: list[str] = field(default_factory=list)
    projection_ids: list[str] = field(default_factory=list)
    recommendation_ids: list[str] = field(default_factory=list)
    next_work_packet_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.lineage_id:
            self.lineage_id = f"lin-{uuid4().hex[:12]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "lineage_id": self.lineage_id,
            "objective_id": self.objective_id,
            "objective_title": self.objective_title,
            "work_packet_ids": self.work_packet_ids,
            "outcome_ids": self.outcome_ids,
            "projection_ids": self.projection_ids,
            "recommendation_ids": self.recommendation_ids,
            "next_work_packet_ids": self.next_work_packet_ids,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkLineage:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def depth(self) -> int:
        return sum(
            1
            for lst in [
                self.work_packet_ids,
                self.outcome_ids,
                self.projection_ids,
                self.recommendation_ids,
                self.next_work_packet_ids,
            ]
            if lst
        )


@dataclass
class SessionHandoff:
    """State transfer record between sessions."""

    handoff_id: str = ""
    from_session_id: str = ""
    to_session_id: str = ""
    from_profile: str = ""
    to_profile: str = ""
    snapshot_id: str = ""
    timestamp: float = 0.0
    context_items: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.handoff_id:
            self.handoff_id = f"handoff-{uuid4().hex[:12]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "handoff_id": self.handoff_id,
            "from_session_id": self.from_session_id,
            "to_session_id": self.to_session_id,
            "from_profile": self.from_profile,
            "to_profile": self.to_profile,
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "context_items": self.context_items,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionHandoff:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ── Attention Model ────────────────────────────────────────────────────


class AttentionModel:
    """Tracks operator attention state based on session activity.

    Integrates with device presence and session heartbeats to determine
    whether operator is active, away, offline, or sleeping.
    """

    def __init__(self) -> None:
        self._state = AttentionState.OFFLINE
        self._last_interaction: float = 0.0
        self._last_state_change: float = time.time()
        self._away_threshold_seconds: float = 300.0  # 5 min
        self._sleeping_threshold_seconds: float = 21600.0  # 6 hours

    @property
    def state(self) -> AttentionState:
        return self._state

    @property
    def last_interaction(self) -> float:
        return self._last_interaction

    @property
    def seconds_since_interaction(self) -> float:
        if self._last_interaction == 0:
            return 0.0
        return time.time() - self._last_interaction

    def record_interaction(self) -> None:
        self._last_interaction = time.time()
        if self._state != AttentionState.ACTIVE:
            self._transition(AttentionState.ACTIVE)

    def update_from_presence(self) -> AttentionState:
        """Derive attention from device presence and time since last interaction."""
        has_sessions = self._check_active_sessions()

        if not has_sessions:
            if self._state != AttentionState.OFFLINE:
                self._transition(AttentionState.OFFLINE)
            return self._state

        elapsed = self.seconds_since_interaction

        if elapsed == 0 or elapsed < self._away_threshold_seconds:
            if self._state != AttentionState.ACTIVE:
                self._transition(AttentionState.ACTIVE)
        elif elapsed >= self._sleeping_threshold_seconds:
            if self._state != AttentionState.SLEEPING:
                self._transition(AttentionState.SLEEPING)
        else:
            if self._state != AttentionState.AWAY:
                self._transition(AttentionState.AWAY)

        return self._state

    def _transition(self, new_state: AttentionState) -> None:
        old = self._state
        self._state = new_state
        self._last_state_change = time.time()
        logger.debug("attention: %s → %s", old.value, new_state.value)

    def _check_active_sessions(self) -> bool:
        try:
            from substrate.workstation.device_presence import DevicePresenceRegistry

            registry = DevicePresenceRegistry()
            sessions = registry.get_active_sessions()
            return len(sessions) > 0
        except Exception:
            return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "last_interaction": self._last_interaction,
            "seconds_since_interaction": self.seconds_since_interaction,
            "last_state_change": self._last_state_change,
        }


# ── Timeline Engine ────────────────────────────────────────────────────


class TimelineEngine:
    """Records and queries operational events in chronological order.

    JSONL-backed. Events include decisions, outcomes, learnings,
    approvals, executions, session changes, and attention changes.
    """

    def __init__(self, data_dir: str | None = None) -> None:
        self._data_dir = data_dir or os.path.join(_continuity_data_dir(), "timeline")
        os.makedirs(self._data_dir, exist_ok=True)
        self._timeline_path = os.path.join(self._data_dir, "events.jsonl")
        self._events: list[TimelineEvent] = []
        self._max_memory_events = 500

    def record(self, event: TimelineEvent) -> None:
        self._events.append(event)
        if len(self._events) > self._max_memory_events:
            self._events = self._events[-self._max_memory_events :]
        self._persist_event(event)

    def record_event(
        self,
        event_type: str,
        summary: str,
        details: dict[str, Any] | None = None,
        related_ids: list[str] | None = None,
    ) -> TimelineEvent:
        event = TimelineEvent(
            event_type=event_type,
            summary=summary,
            details=details or {},
            related_ids=related_ids or [],
        )
        self.record(event)
        return event

    def get_events(
        self,
        since: float = 0.0,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[TimelineEvent]:
        events = self._load_all()
        if since > 0:
            events = [e for e in events if e.timestamp >= since]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def get_events_between(self, start: float, end: float) -> list[TimelineEvent]:
        events = self._load_all()
        return sorted(
            [e for e in events if start <= e.timestamp <= end],
            key=lambda e: e.timestamp,
        )

    def _persist_event(self, event: TimelineEvent) -> None:
        try:
            with open(self._timeline_path, "a") as f:
                f.write(json.dumps(event.to_dict(), default=str, separators=(",", ":")) + "\n")
        except OSError as e:
            logger.error("timeline: persist failed: %s", e)

    def _load_all(self) -> list[TimelineEvent]:
        if not os.path.exists(self._timeline_path):
            return list(self._events)
        events: list[TimelineEvent] = []
        try:
            with open(self._timeline_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(TimelineEvent.from_dict(json.loads(line)))
        except (OSError, json.JSONDecodeError) as e:
            logger.error("timeline: load failed: %s", e)
        return events


# ── Resume State Engine ────────────────────────────────────────────────


class ResumeStateEngine:
    """Deterministic state diffing — compares two ContinuitySnapshots to
    produce a ResumeReport of what changed while the operator was away.

    Pure state comparison. No LLM calls.
    """

    def generate_resume(
        self,
        before: ContinuitySnapshot,
        after: ContinuitySnapshot,
    ) -> ResumeReport:
        report = ResumeReport(
            absence_duration_seconds=after.captured_at - before.captured_at,
        )

        report.completed = self._find_completed(before, after)
        report.failed = self._find_failed(before, after)
        report.blocked = self._find_newly_blocked(before, after)
        report.became_available = self._find_became_available(before, after)
        report.needs_review = self._find_needs_review(before, after)
        report.changes = self._aggregate_changes(before, after)
        report.recommended_actions = self._compute_recommended_actions(report, after)

        return report

    def _find_completed(
        self, before: ContinuitySnapshot, after: ContinuitySnapshot
    ) -> list[dict[str, Any]]:
        before_active_ids = {
            p.get("packet_id", p.get("id", "")) for p in before.active_work_packets
        }
        after_active_ids = {p.get("packet_id", p.get("id", "")) for p in after.active_work_packets}
        completed_ids = before_active_ids - after_active_ids

        completed = []
        for p in before.active_work_packets:
            pid = p.get("packet_id", p.get("id", ""))
            if pid in completed_ids:
                completed.append(
                    {
                        "category": ChangeCategory.COMPLETED.value,
                        "id": pid,
                        "title": p.get("title", ""),
                        "domain": p.get("domain", ""),
                    }
                )
        return completed

    def _find_failed(
        self, before: ContinuitySnapshot, after: ContinuitySnapshot
    ) -> list[dict[str, Any]]:
        failed = []
        for p in after.active_work_packets:
            status = p.get("status", "")
            if status in ("failed", "error", "rejected"):
                pid = p.get("packet_id", p.get("id", ""))
                was_active = any(
                    bp.get("packet_id", bp.get("id", "")) == pid
                    for bp in before.active_work_packets
                )
                if was_active or pid:
                    failed.append(
                        {
                            "category": ChangeCategory.FAILED.value,
                            "id": pid,
                            "title": p.get("title", ""),
                            "status": status,
                        }
                    )
        return failed

    def _find_newly_blocked(
        self, before: ContinuitySnapshot, after: ContinuitySnapshot
    ) -> list[dict[str, Any]]:
        before_blocked_ids = {b.get("id", b.get("packet_id", "")) for b in before.blocked_items}
        newly_blocked = []
        for b in after.blocked_items:
            bid = b.get("id", b.get("packet_id", ""))
            if bid not in before_blocked_ids:
                newly_blocked.append(
                    {
                        "category": ChangeCategory.BLOCKED.value,
                        "id": bid,
                        "title": b.get("title", ""),
                        "reason": b.get("reason", b.get("blocker", "")),
                    }
                )
        return newly_blocked

    def _find_became_available(
        self, before: ContinuitySnapshot, after: ContinuitySnapshot
    ) -> list[dict[str, Any]]:
        before_blocked_ids = {b.get("id", b.get("packet_id", "")) for b in before.blocked_items}
        after_blocked_ids = {b.get("id", b.get("packet_id", "")) for b in after.blocked_items}
        unblocked_ids = before_blocked_ids - after_blocked_ids

        available = []
        for bid in unblocked_ids:
            item = next(
                (b for b in before.blocked_items if b.get("id", b.get("packet_id", "")) == bid),
                None,
            )
            if item:
                available.append(
                    {
                        "category": ChangeCategory.AVAILABLE.value,
                        "id": bid,
                        "title": item.get("title", ""),
                    }
                )
        return available

    def _find_needs_review(
        self, before: ContinuitySnapshot, after: ContinuitySnapshot
    ) -> list[dict[str, Any]]:
        before_approval_ids = {a.get("id", "") for a in before.approvals_waiting}
        needs_review = []

        for a in after.approvals_waiting:
            aid = a.get("id", "")
            if aid not in before_approval_ids:
                needs_review.append(
                    {
                        "category": ChangeCategory.NEEDS_REVIEW.value,
                        "id": aid,
                        "title": a.get("title", ""),
                        "risk_level": a.get("risk_level", ""),
                    }
                )

        for r in after.active_risks:
            rid = r.get("risk_id", r.get("id", ""))
            was_known = any(
                br.get("risk_id", br.get("id", "")) == rid for br in before.active_risks
            )
            if not was_known:
                needs_review.append(
                    {
                        "category": ChangeCategory.NEW_RISK.value,
                        "id": rid,
                        "title": r.get("title", r.get("type", "")),
                        "severity": r.get("severity", ""),
                    }
                )
        return needs_review

    def _aggregate_changes(
        self, before: ContinuitySnapshot, after: ContinuitySnapshot
    ) -> list[dict[str, Any]]:
        changes: list[dict[str, Any]] = []

        if before.active_profile_mode != after.active_profile_mode:
            changes.append(
                {
                    "type": "profile_change",
                    "from": before.active_profile_mode,
                    "to": after.active_profile_mode,
                }
            )

        before_obj_count = len(before.active_objectives)
        after_obj_count = len(after.active_objectives)
        if before_obj_count != after_obj_count:
            changes.append(
                {
                    "type": "objective_count_change",
                    "from": before_obj_count,
                    "to": after_obj_count,
                }
            )

        before_risk_count = len(before.active_risks)
        after_risk_count = len(after.active_risks)
        if before_risk_count != after_risk_count:
            changes.append(
                {
                    "type": "risk_count_change",
                    "from": before_risk_count,
                    "to": after_risk_count,
                }
            )

        for opp in after.active_opportunities:
            oid = opp.get("opportunity_id", opp.get("id", ""))
            was_known = any(
                bo.get("opportunity_id", bo.get("id", "")) == oid
                for bo in before.active_opportunities
            )
            if not was_known:
                changes.append(
                    {
                        "type": "new_opportunity",
                        "id": oid,
                        "title": opp.get("type", opp.get("title", "")),
                    }
                )

        return changes

    def _compute_recommended_actions(
        self, report: ResumeReport, current: ContinuitySnapshot
    ) -> list[str]:
        actions: list[str] = []

        if report.needs_review:
            actions.append(f"Review {len(report.needs_review)} item(s) requiring attention")

        if report.blocked:
            actions.append(f"Unblock {len(report.blocked)} newly blocked item(s)")

        if report.failed:
            actions.append(f"Investigate {len(report.failed)} failed item(s)")

        if current.approvals_waiting:
            actions.append(f"Process {len(current.approvals_waiting)} pending approval(s)")

        if current.active_risks:
            high_risks = [
                r for r in current.active_risks if r.get("severity") in ("critical", "high")
            ]
            if high_risks:
                actions.append(f"Address {len(high_risks)} high/critical risk(s)")

        if current.current_recommendations:
            actions.append(f"Consider {len(current.current_recommendations)} recommendation(s)")

        if report.became_available:
            actions.append(f"Resume {len(report.became_available)} unblocked item(s)")

        if not actions:
            if current.active_work_packets:
                actions.append("Continue active work — no critical changes detected")
            else:
                actions.append("System idle — consider reviewing strategic objectives")

        return actions


# ── Work Continuity Graph ──────────────────────────────────────────────


class WorkContinuityGraph:
    """Constructs lineage relationships: objective → workpacket → outcome
    → projection → recommendation → next workpacket.

    Deterministic graph construction from existing data sources.
    """

    def build_lineage(
        self,
        objectives: list[dict[str, Any]],
        work_packets: list[dict[str, Any]],
        outcomes: list[dict[str, Any]],
        projections: list[dict[str, Any]],
        recommendations: list[dict[str, Any]],
    ) -> list[WorkLineage]:
        lineages: list[WorkLineage] = []

        for obj in objectives:
            obj_id = obj.get("goal_id", obj.get("id", ""))
            obj_title = obj.get("title", "")
            obj_domain = obj.get("domain", "")

            wp_ids = [
                p.get("packet_id", p.get("id", ""))
                for p in work_packets
                if p.get("domain", "") == obj_domain or p.get("goal_id", "") == obj_id
            ]

            outcome_ids = [
                o.get("outcome_id", o.get("id", ""))
                for o in outcomes
                if o.get("domain", "") == obj_domain
            ]

            proj_ids = [
                p.get("projection_id", p.get("id", ""))
                for p in projections
                if p.get("domain", "") == obj_domain
            ]

            rec_ids = [
                r.get("recommendation_id", r.get("id", ""))
                for r in recommendations
                if r.get("domain", "") == obj_domain or r.get("goal_id", "") == obj_id
            ]

            next_wp_ids = [
                p.get("packet_id", p.get("id", ""))
                for p in work_packets
                if (
                    p.get("status", "") in ("draft", "pending", "ready")
                    and (p.get("domain", "") == obj_domain or p.get("goal_id", "") == obj_id)
                )
            ]

            lineage = WorkLineage(
                objective_id=obj_id,
                objective_title=obj_title,
                work_packet_ids=wp_ids,
                outcome_ids=outcome_ids,
                projection_ids=proj_ids,
                recommendation_ids=rec_ids,
                next_work_packet_ids=next_wp_ids,
            )
            lineages.append(lineage)

        return lineages

    def get_lineage_for_objective(
        self, lineages: list[WorkLineage], objective_id: str
    ) -> WorkLineage | None:
        for l in lineages:
            if l.objective_id == objective_id:
                return l
        return None


# ── Operator Brief Generator ───────────────────────────────────────────


class OperatorBriefGenerator:
    """Generates 30-second executive briefing from current state.

    Deterministic aggregation — no LLM calls.
    """

    def generate(
        self,
        snapshot: ContinuitySnapshot,
        resume_report: ResumeReport | None = None,
    ) -> OperatorBrief:
        brief = OperatorBrief(
            active_objectives_count=len(snapshot.active_objectives),
            active_work_count=len(snapshot.active_work_packets),
            blocked_count=len(snapshot.blocked_items),
            approval_count=len(snapshot.approvals_waiting),
            risk_count=len(snapshot.active_risks),
            opportunity_count=len(snapshot.active_opportunities),
        )

        brief.mission_status = self._compute_mission_status(snapshot)
        brief.current_reality = self._compute_current_reality(snapshot)
        brief.critical_changes = self._compute_critical_changes(snapshot, resume_report)
        brief.pending_decisions = self._compute_pending_decisions(snapshot)
        brief.recommended_actions = self._compute_recommended_actions(snapshot, resume_report)

        return brief

    def _compute_mission_status(self, snap: ContinuitySnapshot) -> str:
        active = len(snap.active_objectives)
        work = len(snap.active_work_packets)
        blocked = len(snap.blocked_items)
        risks = len(snap.active_risks)

        if blocked > 0 and risks > 0:
            return f"{active} objectives, {work} active, {blocked} blocked, {risks} risks — attention required"
        elif blocked > 0:
            return f"{active} objectives, {work} active, {blocked} blocked — needs unblocking"
        elif risks > 0:
            return f"{active} objectives, {work} active, {risks} risks to monitor"
        elif work > 0:
            return f"{active} objectives, {work} active — progressing"
        else:
            return f"{active} objectives — idle, consider next actions"

    def _compute_current_reality(self, snap: ContinuitySnapshot) -> str:
        parts = []
        if snap.active_profile_mode:
            parts.append(f"Profile: {snap.active_profile_mode}")
        parts.append(f"Attention: {snap.operator_attention}")
        if snap.active_loops:
            parts.append(f"Loops: {len(snap.active_loops)} active")
        if snap.active_projections:
            parts.append(f"Projections: {len(snap.active_projections)}")
        return " | ".join(parts) if parts else "No active context"

    def _compute_critical_changes(
        self, snap: ContinuitySnapshot, resume: ResumeReport | None
    ) -> list[str]:
        changes: list[str] = []
        if resume:
            if resume.failed:
                changes.append(f"{len(resume.failed)} work item(s) failed")
            if resume.blocked:
                changes.append(f"{len(resume.blocked)} item(s) newly blocked")
            if resume.completed:
                changes.append(f"{len(resume.completed)} item(s) completed")
            if resume.needs_review:
                changes.append(f"{len(resume.needs_review)} item(s) need review")

        high_risks = [r for r in snap.active_risks if r.get("severity") in ("critical", "high")]
        if high_risks:
            changes.append(f"{len(high_risks)} high/critical risk(s) active")

        return changes

    def _compute_pending_decisions(self, snap: ContinuitySnapshot) -> list[str]:
        decisions: list[str] = []
        for a in snap.approvals_waiting:
            title = a.get("title", "Untitled")
            risk = a.get("risk_level", "")
            decisions.append(f"Approve/reject: {title}" + (f" ({risk})" if risk else ""))
        for r in snap.current_recommendations[:3]:
            title = r.get("title", r.get("type", "Recommendation"))
            decisions.append(f"Consider: {title}")
        return decisions

    def _compute_recommended_actions(
        self, snap: ContinuitySnapshot, resume: ResumeReport | None
    ) -> list[str]:
        if resume:
            return resume.recommended_actions
        actions: list[str] = []
        if snap.approvals_waiting:
            actions.append(f"Process {len(snap.approvals_waiting)} pending approval(s)")
        if snap.blocked_items:
            actions.append(f"Unblock {len(snap.blocked_items)} item(s)")
        high_risks = [r for r in snap.active_risks if r.get("severity") in ("critical", "high")]
        if high_risks:
            actions.append(f"Address {len(high_risks)} high/critical risk(s)")
        if snap.active_opportunities:
            actions.append(f"Review {len(snap.active_opportunities)} opportunity(ies)")
        if not actions:
            if snap.active_work_packets:
                actions.append("Continue active work")
            else:
                actions.append("System idle — review objectives")
        return actions


# ── Snapshot Collector ─────────────────────────────────────────────────


class SnapshotCollector:
    """Gathers current state from all UMH subsystems into a ContinuitySnapshot.

    Composes Phase 4 (gap engine), Phase 5 (tick loop), Phase 6 (projections),
    and existing approval/work/reality systems.
    """

    def collect(self, attention: AttentionModel | None = None) -> ContinuitySnapshot:
        snap = ContinuitySnapshot()

        snap.active_profile_mode = self._get_profile_mode()
        snap.active_objectives = self._get_active_objectives()
        snap.active_loops = self._get_active_loops()
        snap.active_work_packets = self._get_active_work_packets()
        snap.blocked_items = self._get_blocked_items()
        snap.approvals_waiting = self._get_pending_approvals()
        snap.active_projections = self._get_active_projections()
        snap.active_risks = self._get_active_risks()
        snap.active_opportunities = self._get_active_opportunities()
        snap.current_recommendations = self._get_current_recommendations()

        if attention:
            snap.operator_attention = attention.state.value
            snap.last_operator_interaction = attention.last_interaction

        snap.reality_hash = snap.compute_hash()
        return snap

    def _get_profile_mode(self) -> str:
        try:
            from substrate.state.runtime_paths import runtime_state_path

            state_path = str(
                runtime_state_path("organism", "daemon_state.json", create_parent=False)
            )
            if os.path.exists(state_path):
                with open(state_path) as f:
                    state = json.load(f)
                return state.get("profile_mode", "")
        except Exception:
            pass
        return ""

    def _get_active_objectives(self) -> list[dict[str, Any]]:
        try:
            from substrate.organism.strategic_gap_engine import GoalRegistry

            registry = GoalRegistry()
            goals = registry.list_goals()
            return [
                {
                    "goal_id": g.goal_id,
                    "title": g.title,
                    "domain": g.domain,
                    "status": g.status.value,
                    "progress": g.progress,
                    "priority": g.priority.value if hasattr(g.priority, "value") else g.priority,
                }
                for g in goals
                if g.status.value == "active"
            ]
        except Exception as e:
            logger.debug("continuity: objectives unavailable: %s", e)
            return []

    def _get_active_loops(self) -> list[dict[str, Any]]:
        try:
            from substrate.organism.strategic_tick_loop import get_tick_loop

            loop = get_tick_loop()
            status = loop.status()
            return [
                {
                    "type": "strategic_tick_loop",
                    "state": status.get("state", ""),
                    "frequency": status.get("frequency", ""),
                    "tick_count": status.get("tick_count", 0),
                }
            ]
        except Exception as e:
            logger.debug("continuity: loops unavailable: %s", e)
            return []

    def _get_active_work_packets(self) -> list[dict[str, Any]]:
        try:
            packets_dir = os.path.join(_repo_root(), "data", "umh", "execution", "packets")
            if not os.path.isdir(packets_dir):
                return []
            active = []
            for fname in os.listdir(packets_dir):
                if not fname.endswith(".json"):
                    continue
                try:
                    with open(os.path.join(packets_dir, fname)) as f:
                        p = json.load(f)
                    status = p.get("status", "")
                    if status in (
                        "active",
                        "executing",
                        "pending",
                        "approved",
                        "ready",
                        "in_progress",
                    ):
                        active.append(
                            {
                                "packet_id": p.get("packet_id", fname.replace(".json", "")),
                                "title": p.get("title", ""),
                                "domain": p.get("domain", ""),
                                "status": status,
                            }
                        )
                except (json.JSONDecodeError, OSError):
                    continue
            return active
        except Exception as e:
            logger.debug("continuity: work packets unavailable: %s", e)
            return []

    def _get_blocked_items(self) -> list[dict[str, Any]]:
        try:
            packets_dir = os.path.join(_repo_root(), "data", "umh", "execution", "packets")
            if not os.path.isdir(packets_dir):
                return []
            blocked = []
            for fname in os.listdir(packets_dir):
                if not fname.endswith(".json"):
                    continue
                try:
                    with open(os.path.join(packets_dir, fname)) as f:
                        p = json.load(f)
                    if p.get("status") == "blocked":
                        blocked.append(
                            {
                                "id": p.get("packet_id", fname.replace(".json", "")),
                                "title": p.get("title", ""),
                                "reason": p.get("blocker", ""),
                            }
                        )
                except (json.JSONDecodeError, OSError):
                    continue
            return blocked
        except Exception as e:
            logger.debug("continuity: blocked items unavailable: %s", e)
            return []

    def _get_pending_approvals(self) -> list[dict[str, Any]]:
        try:
            from substrate.organism.approval_store import ApprovalStore

            store = ApprovalStore()
            all_approvals = store._read_all()
            return [a for a in all_approvals if a.get("status") == "pending"]
        except Exception as e:
            logger.debug("continuity: approvals unavailable: %s", e)
            return []

    def _get_active_projections(self) -> list[dict[str, Any]]:
        try:
            from substrate.organism.projection_engine import get_projection_engine

            engine = get_projection_engine()
            if not engine.last_projections:
                return []
            return [p.to_dict() for p in engine.last_projections[:10]]
        except Exception as e:
            logger.debug("continuity: projections unavailable: %s", e)
            return []

    def _get_active_risks(self) -> list[dict[str, Any]]:
        try:
            from substrate.organism.projection_engine import get_projection_engine

            engine = get_projection_engine()
            if not engine.last_risks:
                return []
            return [r.to_dict() for r in engine.last_risks]
        except Exception as e:
            logger.debug("continuity: risks unavailable: %s", e)
            return []

    def _get_active_opportunities(self) -> list[dict[str, Any]]:
        try:
            from substrate.organism.projection_engine import get_projection_engine

            engine = get_projection_engine()
            if not engine.last_opportunities:
                return []
            return [o.to_dict() for o in engine.last_opportunities]
        except Exception as e:
            logger.debug("continuity: opportunities unavailable: %s", e)
            return []

    def _get_current_recommendations(self) -> list[dict[str, Any]]:
        try:
            from substrate.organism.strategic_tick_loop import get_tick_loop

            loop = get_tick_loop()
            state = loop.strategic_state()
            candidates = state.get("candidates", {}).get("pending", [])
            return candidates[:10]
        except Exception as e:
            logger.debug("continuity: recommendations unavailable: %s", e)
            return []


# ── Continuity Runtime ─────────────────────────────────────────────────


class ContinuityRuntime:
    """Top-level orchestrator — the operational continuity engine.

    Composes: SnapshotCollector, ResumeStateEngine, WorkContinuityGraph,
    OperatorBriefGenerator, TimelineEngine, AttentionModel.

    Singleton via get_continuity_runtime() / reset_continuity_runtime().
    """

    def __init__(self, data_dir: str | None = None) -> None:
        self._data_dir = data_dir or _continuity_data_dir()
        _ensure_dirs()

        self.attention = AttentionModel()
        self.timeline = TimelineEngine(data_dir=os.path.join(self._data_dir, "timeline"))
        self._collector = SnapshotCollector()
        self._resume_engine = ResumeStateEngine()
        self._graph = WorkContinuityGraph()
        self._brief_generator = OperatorBriefGenerator()

        self._last_snapshot: ContinuitySnapshot | None = None
        self._departure_snapshot: ContinuitySnapshot | None = None
        self._session_handoffs: list[SessionHandoff] = []
        self._run_count: int = 0
        self._last_brief: OperatorBrief | None = None

    # ── Core operations ────────────────────────────────────────────

    def capture_snapshot(self) -> ContinuitySnapshot:
        """Capture current operational state from all subsystems."""
        snapshot = self._collector.collect(self.attention)
        self._last_snapshot = snapshot
        self._run_count += 1
        self._persist_snapshot(snapshot)
        return snapshot

    def record_departure(self) -> ContinuitySnapshot:
        """Record operator leaving — snapshot becomes the departure baseline."""
        snapshot = self.capture_snapshot()
        self._departure_snapshot = snapshot
        self.timeline.record_event(
            TimelineEventType.SESSION_END.value,
            "Operator departed",
            {"snapshot_id": snapshot.snapshot_id, "attention": self.attention.state.value},
        )
        return snapshot

    def generate_resume(self) -> ResumeReport:
        """Generate resume report comparing departure state to current state."""
        current = self.capture_snapshot()

        if self._departure_snapshot:
            baseline = self._departure_snapshot
        elif self._last_snapshot:
            baseline = self._last_snapshot
        else:
            baseline = ContinuitySnapshot()

        report = self._resume_engine.generate_resume(baseline, current)
        self._departure_snapshot = None

        self.timeline.record_event(
            TimelineEventType.SESSION_START.value,
            f"Operator resumed — {report.total_changes} change(s)",
            {
                "absence_seconds": report.absence_duration_seconds,
                "total_changes": report.total_changes,
            },
        )

        self._persist_resume(report)
        return report

    def generate_brief(self, include_resume: bool = True) -> OperatorBrief:
        """Generate 30-second executive briefing."""
        snapshot = self.capture_snapshot()
        resume = self.generate_resume() if include_resume and self._departure_snapshot else None
        brief = self._brief_generator.generate(snapshot, resume)
        self._last_brief = brief
        self._persist_brief(brief)
        return brief

    def build_lineage(self) -> list[WorkLineage]:
        """Build work continuity graph from current state."""
        snapshot = self._last_snapshot or self.capture_snapshot()
        return self._graph.build_lineage(
            objectives=snapshot.active_objectives,
            work_packets=snapshot.active_work_packets,
            outcomes=[],
            projections=snapshot.active_projections,
            recommendations=snapshot.current_recommendations,
        )

    def record_session_handoff(
        self,
        from_session_id: str,
        to_session_id: str,
        from_profile: str = "",
        to_profile: str = "",
    ) -> SessionHandoff:
        """Record transfer between sessions."""
        snapshot = self.capture_snapshot()
        handoff = SessionHandoff(
            from_session_id=from_session_id,
            to_session_id=to_session_id,
            from_profile=from_profile,
            to_profile=to_profile,
            snapshot_id=snapshot.snapshot_id,
            context_items=[
                f"{len(snapshot.active_objectives)} objectives",
                f"{len(snapshot.active_work_packets)} work packets",
                f"{len(snapshot.blocked_items)} blocked",
                f"{len(snapshot.approvals_waiting)} approvals",
            ],
        )
        self._session_handoffs.append(handoff)
        self._persist_handoff(handoff)

        self.timeline.record_event(
            TimelineEventType.SESSION_START.value,
            f"Session handoff: {from_session_id} → {to_session_id}",
            handoff.to_dict(),
        )
        return handoff

    def record_interaction(self) -> None:
        """Record operator interaction — updates attention model."""
        self.attention.record_interaction()

    def update_attention(self) -> AttentionState:
        """Update attention state from device presence."""
        return self.attention.update_from_presence()

    # ── Query interface ────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        return {
            "state": "active" if self._last_snapshot else "idle",
            "run_count": self._run_count,
            "last_snapshot_id": self._last_snapshot.snapshot_id if self._last_snapshot else None,
            "has_departure_snapshot": self._departure_snapshot is not None,
            "attention": self.attention.to_dict(),
            "handoff_count": len(self._session_handoffs),
            "last_brief_id": self._last_brief.brief_id if self._last_brief else None,
        }

    def get_snapshot(self) -> dict[str, Any] | None:
        if self._last_snapshot:
            return self._last_snapshot.to_dict()
        return None

    def get_last_brief(self) -> dict[str, Any] | None:
        if self._last_brief:
            return self._last_brief.to_dict()
        return None

    def get_timeline(
        self, since: float = 0.0, event_type: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        events = self.timeline.get_events(since=since, event_type=event_type, limit=limit)
        return [e.to_dict() for e in events]

    def get_handoffs(self) -> list[dict[str, Any]]:
        return [h.to_dict() for h in self._session_handoffs]

    # ── Persistence ────────────────────────────────────────────────

    def _persist_snapshot(self, snapshot: ContinuitySnapshot) -> None:
        snap_dir = os.path.join(self._data_dir, "snapshots")
        os.makedirs(snap_dir, exist_ok=True)
        path = os.path.join(snap_dir, f"{snapshot.snapshot_id}.json")
        try:
            with open(path, "w") as f:
                json.dump(snapshot.to_dict(), f, indent=2, default=str)
        except OSError as e:
            logger.error("continuity: snapshot persist failed: %s", e)

    def _persist_resume(self, report: ResumeReport) -> None:
        brief_dir = os.path.join(self._data_dir, "briefs")
        os.makedirs(brief_dir, exist_ok=True)
        path = os.path.join(brief_dir, f"resume-{int(report.generated_at)}.json")
        try:
            with open(path, "w") as f:
                json.dump(report.to_dict(), f, indent=2, default=str)
        except OSError as e:
            logger.error("continuity: resume persist failed: %s", e)

    def _persist_brief(self, brief: OperatorBrief) -> None:
        brief_dir = os.path.join(self._data_dir, "briefs")
        os.makedirs(brief_dir, exist_ok=True)
        path = os.path.join(brief_dir, f"{brief.brief_id}.json")
        try:
            with open(path, "w") as f:
                json.dump(brief.to_dict(), f, indent=2, default=str)
        except OSError as e:
            logger.error("continuity: brief persist failed: %s", e)

    def _persist_handoff(self, handoff: SessionHandoff) -> None:
        session_dir = os.path.join(self._data_dir, "sessions")
        os.makedirs(session_dir, exist_ok=True)
        path = os.path.join(session_dir, f"{handoff.handoff_id}.json")
        try:
            with open(path, "w") as f:
                json.dump(handoff.to_dict(), f, indent=2, default=str)
        except OSError as e:
            logger.error("continuity: handoff persist failed: %s", e)


# ── Singleton ──────────────────────────────────────────────────────────


_instance: ContinuityRuntime | None = None


def get_continuity_runtime() -> ContinuityRuntime:
    global _instance
    if _instance is None:
        _instance = ContinuityRuntime()
    return _instance


def reset_continuity_runtime() -> None:
    global _instance
    _instance = None
