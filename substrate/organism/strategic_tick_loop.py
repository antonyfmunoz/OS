"""Strategic Tick Loop — continuous governed awareness engine.

Phase 5. Transforms UMH from request-driven to continuously aware.
The tick loop is the heartbeat: observe reality, detect changes,
recompute priorities, surface recommendations, generate candidate
work, monitor drift — without requiring manual operator initiation.

Governance remains mandatory. The tick loop creates awareness and
proposals. The operator remains the final authority.

Composes existing primitives:
  - AutonomousTick (autonomous_tick) — heartbeat engine
  - StrategicGapEngine (strategic_gap_engine) — gap analysis
  - GoalRegistry (strategic_gap_engine) — goal persistence
  - EmpireRouter (empire_router) — reality snapshot
  - ProfileMode (profile_modes) — operator context
  - DevicePresenceRegistry (device_presence) — operator presence
  - EventSpine (event_spine) — event emission

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


def _tick_data_dir() -> str:
    return os.path.join(_repo_root(), "data", "umh", "tick_loop")


def _ensure_tick_dirs() -> None:
    base = _tick_data_dir()
    for sub in ("snapshots", "candidates", "drift_warnings"):
        os.makedirs(os.path.join(base, sub), exist_ok=True)


# ── Enums ──────────────────────────────────────────────────────────────


class TickFrequency(str, Enum):
    FAST = "30s"
    NORMAL = "1m"
    RELAXED = "5m"
    SLOW = "15m"
    MANUAL = "manual"

    @property
    def seconds(self) -> float:
        return {
            "30s": 30.0,
            "1m": 60.0,
            "5m": 300.0,
            "15m": 900.0,
            "manual": 0.0,
        }[self.value]


class RecommendationLifecycle(str, Enum):
    PROPOSED = "proposed"
    REVIEWED = "reviewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"


class DriftSeverity(str, Enum):
    WARNING = "warning"
    ALERT = "alert"
    CRITICAL = "critical"


# ── Change Detection ─────────────────────────────────────────────────


@dataclass
class RealityDelta:
    """Differences between two consecutive reality snapshots."""
    new_outcomes: list[dict[str, Any]] = field(default_factory=list)
    new_failures: list[dict[str, Any]] = field(default_factory=list)
    new_approvals: int = 0
    new_packets: list[dict[str, Any]] = field(default_factory=list)
    goal_changes: list[str] = field(default_factory=list)
    agent_status_changes: list[dict[str, Any]] = field(default_factory=list)
    domain_changes: list[str] = field(default_factory=list)
    has_meaningful_change: bool = False
    snapshot_hash: str = ""
    previous_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "new_outcomes": self.new_outcomes,
            "new_failures": self.new_failures,
            "new_approvals": self.new_approvals,
            "new_packets": self.new_packets,
            "goal_changes": self.goal_changes,
            "agent_status_changes": self.agent_status_changes,
            "domain_changes": self.domain_changes,
            "has_meaningful_change": self.has_meaningful_change,
            "snapshot_hash": self.snapshot_hash,
            "previous_hash": self.previous_hash,
        }


def _snapshot_hash(snapshot: dict[str, Any]) -> str:
    """Deterministic hash of a reality snapshot for change detection."""
    canonical = json.dumps(snapshot, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


class ChangeDetector:
    """Compares consecutive reality snapshots to detect meaningful changes."""

    def __init__(self) -> None:
        self._previous_snapshot: dict[str, Any] | None = None
        self._previous_hash: str = ""
        self._previous_goal_ids: set[str] = set()

    def detect(
        self,
        current: dict[str, Any],
        current_goal_ids: set[str] | None = None,
    ) -> RealityDelta:
        current_hash = _snapshot_hash(current)
        delta = RealityDelta(
            snapshot_hash=current_hash,
            previous_hash=self._previous_hash,
        )

        if self._previous_snapshot is None:
            delta.has_meaningful_change = True
            self._previous_snapshot = current
            self._previous_hash = current_hash
            if current_goal_ids:
                self._previous_goal_ids = current_goal_ids
            return delta

        goal_ids_changed = False
        if current_goal_ids is not None:
            added_goals = current_goal_ids - self._previous_goal_ids
            removed_goals = self._previous_goal_ids - current_goal_ids
            if added_goals or removed_goals:
                delta.goal_changes = sorted(added_goals | removed_goals)
                goal_ids_changed = True

        if current_hash == self._previous_hash and not goal_ids_changed:
            return delta

        prev = self._previous_snapshot

        prev_outcomes = {
            o.get("packet_id", "") for o in prev.get("recent_outcomes", [])
        }
        for o in current.get("recent_outcomes", []):
            pid = o.get("packet_id", "")
            if pid and pid not in prev_outcomes:
                summary = o.get("summary", "")
                if "fail" in str(summary).lower() or "error" in str(summary).lower():
                    delta.new_failures.append(o)
                else:
                    delta.new_outcomes.append(o)

        prev_approval_count = prev.get("open_approvals", 0)
        curr_approval_count = current.get("open_approvals", 0)
        if curr_approval_count > prev_approval_count:
            delta.new_approvals = curr_approval_count - prev_approval_count

        prev_packets = {
            p.get("packet_id", "") for p in prev.get("active_loops", [])
        }
        for p in current.get("active_loops", []):
            pid = p.get("packet_id", "")
            if pid and pid not in prev_packets:
                delta.new_packets.append(p)

        prev_domains = set(prev.get("active_domains", []))
        curr_domains = set(current.get("active_domains", []))
        added = curr_domains - prev_domains
        removed = prev_domains - curr_domains
        if added or removed:
            delta.domain_changes = sorted(added | removed)

        delta.has_meaningful_change = bool(
            delta.new_outcomes
            or delta.new_failures
            or delta.new_approvals > 0
            or delta.new_packets
            or delta.goal_changes
            or delta.domain_changes
        )

        self._previous_snapshot = current
        self._previous_hash = current_hash
        if current_goal_ids is not None:
            self._previous_goal_ids = current_goal_ids

        return delta


# ── Candidate Work Queue ─────────────────────────────────────────────


@dataclass
class CandidateWorkItem:
    """Strategic inventory item — not execution, just a prioritized proposal."""
    candidate_id: str = field(default_factory=lambda: f"cwi-{uuid4().hex[:8]}")
    recommendation_id: str = ""
    title: str = ""
    domain: str = ""
    priority_score: float = 0.0
    impact: str = ""
    risk: str = ""
    dependencies: list[str] = field(default_factory=list)
    lifecycle: RecommendationLifecycle = RecommendationLifecycle.PROPOSED
    proposed_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    decided_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "recommendation_id": self.recommendation_id,
            "title": self.title,
            "domain": self.domain,
            "priority_score": self.priority_score,
            "impact": self.impact,
            "risk": self.risk,
            "dependencies": self.dependencies,
            "lifecycle": self.lifecycle.value,
            "proposed_at": self.proposed_at,
            "expires_at": self.expires_at,
            "decided_at": self.decided_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CandidateWorkItem:
        return cls(
            candidate_id=d.get("candidate_id", f"cwi-{uuid4().hex[:8]}"),
            recommendation_id=d.get("recommendation_id", ""),
            title=d.get("title", ""),
            domain=d.get("domain", ""),
            priority_score=d.get("priority_score", 0.0),
            impact=d.get("impact", ""),
            risk=d.get("risk", ""),
            dependencies=d.get("dependencies", []),
            lifecycle=RecommendationLifecycle(d["lifecycle"]) if "lifecycle" in d else RecommendationLifecycle.PROPOSED,
            proposed_at=d.get("proposed_at", time.time()),
            expires_at=d.get("expires_at", 0.0),
            decided_at=d.get("decided_at", 0.0),
        )


class CandidateWorkQueue:
    """Strategic work inventory. JSONL-backed. Not execution — just proposals."""

    def __init__(self, store_path: str | None = None) -> None:
        _ensure_tick_dirs()
        self._store_path = store_path or os.path.join(
            _tick_data_dir(), "candidates", "queue.jsonl"
        )
        self._items: dict[str, CandidateWorkItem] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._store_path):
            return
        try:
            with open(self._store_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    item = CandidateWorkItem.from_dict(json.loads(line))
                    self._items[item.candidate_id] = item
        except (json.JSONDecodeError, OSError) as e:
            logger.error("failed to load candidate queue: %s", e)

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        with open(self._store_path, "w") as f:
            for item in self._items.values():
                f.write(json.dumps(item.to_dict()) + "\n")

    def add(self, item: CandidateWorkItem) -> CandidateWorkItem:
        self._items[item.candidate_id] = item
        self._save()
        return item

    def get(self, candidate_id: str) -> CandidateWorkItem | None:
        return self._items.get(candidate_id)

    def all_items(self) -> list[CandidateWorkItem]:
        return list(self._items.values())

    def pending(self) -> list[CandidateWorkItem]:
        return sorted(
            [i for i in self._items.values()
             if i.lifecycle == RecommendationLifecycle.PROPOSED],
            key=lambda i: i.priority_score,
            reverse=True,
        )

    def by_domain(self, domain: str) -> list[CandidateWorkItem]:
        return [i for i in self._items.values() if i.domain == domain]

    def update_lifecycle(
        self, candidate_id: str, lifecycle: RecommendationLifecycle
    ) -> bool:
        item = self._items.get(candidate_id)
        if not item:
            return False
        item.lifecycle = lifecycle
        item.decided_at = time.time()
        self._save()
        return True

    def expire_old(self, max_age_hours: float = 72.0) -> int:
        """Expire proposals older than max_age_hours."""
        now = time.time()
        expired = 0
        for item in self._items.values():
            if item.lifecycle != RecommendationLifecycle.PROPOSED:
                continue
            age_hours = (now - item.proposed_at) / 3600
            if age_hours > max_age_hours:
                item.lifecycle = RecommendationLifecycle.EXPIRED
                item.expires_at = now
                expired += 1
        if expired:
            self._save()
        return expired

    def populate_from_recommendations(
        self, recommendations: list[dict[str, Any]]
    ) -> int:
        """Create candidate items from recommendations not already in queue."""
        existing_recs = {i.recommendation_id for i in self._items.values()}
        added = 0
        for rec in recommendations:
            rec_id = rec.get("recommendation_id", "")
            if rec_id and rec_id not in existing_recs:
                item = CandidateWorkItem(
                    recommendation_id=rec_id,
                    title=rec.get("title", ""),
                    domain=rec.get("suggested_domain", ""),
                    priority_score=rec.get("priority_score", 0.0),
                    impact=rec.get("impact_estimate", ""),
                    risk=rec.get("risk_estimate", ""),
                    dependencies=rec.get("dependency_chain", []),
                )
                self._items[item.candidate_id] = item
                added += 1
        if added:
            self._save()
        return added


# ── Goal Drift Detection ─────────────────────────────────────────────


@dataclass
class DriftWarning:
    """Issued when a goal shows no progress over a threshold period."""
    warning_id: str = field(default_factory=lambda: f"drift-{uuid4().hex[:8]}")
    goal_id: str = ""
    goal_title: str = ""
    domain: str = ""
    severity: DriftSeverity = DriftSeverity.WARNING
    days_stagnant: float = 0.0
    last_activity: float = 0.0
    completion_ratio: float = 0.0
    message: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "warning_id": self.warning_id,
            "goal_id": self.goal_id,
            "goal_title": self.goal_title,
            "domain": self.domain,
            "severity": self.severity.value,
            "days_stagnant": round(self.days_stagnant, 1),
            "last_activity": self.last_activity,
            "completion_ratio": round(self.completion_ratio, 2),
            "message": self.message,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DriftWarning:
        return cls(
            warning_id=d.get("warning_id", f"drift-{uuid4().hex[:8]}"),
            goal_id=d.get("goal_id", ""),
            goal_title=d.get("goal_title", ""),
            domain=d.get("domain", ""),
            severity=DriftSeverity(d["severity"]) if "severity" in d else DriftSeverity.WARNING,
            days_stagnant=d.get("days_stagnant", 0.0),
            last_activity=d.get("last_activity", 0.0),
            completion_ratio=d.get("completion_ratio", 0.0),
            message=d.get("message", ""),
            created_at=d.get("created_at", time.time()),
        )


class DriftDetector:
    """Detects when goals stagnate without progress."""

    WARNING_DAYS = 7.0
    ALERT_DAYS = 14.0
    CRITICAL_DAYS = 30.0

    def detect_drift(
        self,
        goals: list[Any],
        recent_outcomes: list[dict[str, Any]],
    ) -> list[DriftWarning]:
        warnings: list[DriftWarning] = []
        now = time.time()

        outcome_domains: set[str] = set()
        latest_by_domain: dict[str, float] = {}
        for o in recent_outcomes:
            domain = o.get("domain", "")
            if domain:
                outcome_domains.add(domain)
                ts = o.get("completed_at", o.get("created_at", 0))
                if ts > latest_by_domain.get(domain, 0):
                    latest_by_domain[domain] = ts

        for goal in goals:
            if hasattr(goal, "status") and goal.status.value != "active":
                continue

            domain = goal.domain if hasattr(goal, "domain") else ""
            updated = goal.updated_at if hasattr(goal, "updated_at") else 0
            last_domain_activity = latest_by_domain.get(domain, 0)
            last_activity = max(updated, last_domain_activity)
            days_since = (now - last_activity) / 86400 if last_activity > 0 else 999

            completion = goal.completion_ratio() if hasattr(goal, "completion_ratio") else 0

            if days_since < self.WARNING_DAYS:
                continue

            if days_since >= self.CRITICAL_DAYS:
                severity = DriftSeverity.CRITICAL
            elif days_since >= self.ALERT_DAYS:
                severity = DriftSeverity.ALERT
            else:
                severity = DriftSeverity.WARNING

            title = goal.title if hasattr(goal, "title") else str(goal)
            goal_id = goal.goal_id if hasattr(goal, "goal_id") else ""

            warning = DriftWarning(
                goal_id=goal_id,
                goal_title=title,
                domain=domain,
                severity=severity,
                days_stagnant=days_since,
                last_activity=last_activity,
                completion_ratio=completion,
                message=(
                    f"Goal '{title}' has not progressed for "
                    f"{days_since:.0f} days ({completion:.0%} complete). "
                    f"Severity: {severity.value}."
                ),
            )
            warnings.append(warning)

        warnings.sort(key=lambda w: w.days_stagnant, reverse=True)
        return warnings


# ── Profile-Aware Prioritization ─────────────────────────────────────


_PROFILE_DOMAIN_AFFINITY: dict[str, list[str]] = {
    "developer": ["engineering", "infrastructure", "operator", "vision"],
    "research": ["research", "intelligence", "knowledge"],
    "music": ["music", "content", "creative"],
    "design": ["design", "content", "creative", "vision"],
    "content": ["content", "creative", "marketing"],
    "command_center": ["strategy", "governance", "operations", "finance"],
    "finance": ["finance", "accounting", "strategy"],
    "learning": ["learning", "research", "knowledge"],
}


def apply_profile_weighting(
    recommendations: list[dict[str, Any]],
    active_profiles: list[str],
) -> list[dict[str, Any]]:
    """Adjust recommendation scores based on active profile modes.

    Does not remove items — only reweights. All domains remain visible.
    """
    if not active_profiles:
        return recommendations

    affinity_domains: set[str] = set()
    for profile in active_profiles:
        for domain in _PROFILE_DOMAIN_AFFINITY.get(profile, []):
            affinity_domains.add(domain)

    weighted = []
    for rec in recommendations:
        rec_copy = dict(rec)
        domain = rec_copy.get("suggested_domain", rec_copy.get("domain", ""))
        score = rec_copy.get("priority_score", 0.0)

        if domain in affinity_domains:
            rec_copy["priority_score"] = round(score * 1.15, 2)
            rec_copy["profile_boosted"] = True
        else:
            rec_copy["profile_boosted"] = False

        weighted.append(rec_copy)

    weighted.sort(key=lambda r: r.get("priority_score", 0), reverse=True)
    return weighted


# ── Tick History ─────────────────────────────────────────────────────


@dataclass
class TickRecord:
    """Record of a single tick cycle's results."""
    tick_id: str = field(default_factory=lambda: f"tick-{uuid4().hex[:8]}")
    cycle_number: int = 0
    timestamp: float = field(default_factory=time.time)
    change_detected: bool = False
    analysis_ran: bool = False
    gaps_found: int = 0
    recommendations_generated: int = 0
    candidates_added: int = 0
    drift_warnings: int = 0
    expired_candidates: int = 0
    operator_present: bool = False
    active_profiles: list[str] = field(default_factory=list)
    elapsed_ms: float = 0.0
    skipped_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick_id": self.tick_id,
            "cycle_number": self.cycle_number,
            "timestamp": self.timestamp,
            "change_detected": self.change_detected,
            "analysis_ran": self.analysis_ran,
            "gaps_found": self.gaps_found,
            "recommendations_generated": self.recommendations_generated,
            "candidates_added": self.candidates_added,
            "drift_warnings": self.drift_warnings,
            "expired_candidates": self.expired_candidates,
            "operator_present": self.operator_present,
            "active_profiles": self.active_profiles,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "skipped_reason": self.skipped_reason,
        }


# ── Strategic Tick Loop (Orchestrator) ────────────────────────────────


class StrategicTickLoop:
    """Continuous governed awareness engine.

    Wires StrategicGapEngine into the organism tick as a registered
    stage. Each cycle: check for reality changes, run analysis if
    changed, populate candidate queue, detect drift, respect profiles.
    """

    def __init__(
        self,
        frequency: TickFrequency = TickFrequency.NORMAL,
        candidate_queue: CandidateWorkQueue | None = None,
    ) -> None:
        _ensure_tick_dirs()
        self._frequency = frequency
        self._candidate_queue = candidate_queue or CandidateWorkQueue()
        self._change_detector = ChangeDetector()
        self._drift_detector = DriftDetector()
        self._tick_history: list[TickRecord] = []
        self._cycle_count = 0
        self._running = False
        self._paused = False
        self._last_analysis: dict[str, Any] | None = None
        self._last_delta: RealityDelta | None = None
        self._last_drift: list[DriftWarning] = []
        self._active_profiles: list[str] = []

    @property
    def frequency(self) -> TickFrequency:
        return self._frequency

    @frequency.setter
    def frequency(self, value: TickFrequency) -> None:
        self._frequency = value

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    @property
    def candidate_queue(self) -> CandidateWorkQueue:
        return self._candidate_queue

    @property
    def last_analysis(self) -> dict[str, Any] | None:
        return self._last_analysis

    @property
    def last_delta(self) -> RealityDelta | None:
        return self._last_delta

    @property
    def last_drift_warnings(self) -> list[DriftWarning]:
        return self._last_drift

    @property
    def tick_history(self) -> list[TickRecord]:
        return list(self._tick_history)

    def set_active_profiles(self, profiles: list[str]) -> None:
        self._active_profiles = profiles

    def start(self) -> None:
        self._running = True
        self._paused = False

    def stop(self) -> None:
        self._running = False

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def execute_tick(self) -> TickRecord:
        """Execute one tick cycle. Core method called by AutonomousTick stage."""
        self._cycle_count += 1
        record = TickRecord(cycle_number=self._cycle_count)
        start = time.monotonic_ns()

        if self._paused:
            record.skipped_reason = "paused"
            self._record_tick(record, start)
            return record

        if self._frequency == TickFrequency.MANUAL and not self._running:
            record.skipped_reason = "manual_mode"
            self._record_tick(record, start)
            return record

        record.active_profiles = list(self._active_profiles)
        record.operator_present = self._check_operator_presence()

        reality = self._get_reality()
        goal_ids = self._get_current_goal_ids()
        delta = self._change_detector.detect(reality, goal_ids)
        self._last_delta = delta
        record.change_detected = delta.has_meaningful_change

        if not delta.has_meaningful_change:
            record.skipped_reason = "no_change"
            expired = self._candidate_queue.expire_old()
            record.expired_candidates = expired
            self._record_tick(record, start)
            return record

        record.analysis_ran = True
        analysis = self._run_analysis()
        self._last_analysis = analysis

        if analysis:
            record.gaps_found = analysis.get("gap_count", 0)
            record.recommendations_generated = analysis.get("recommendation_count", 0)

            recs = analysis.get("recommendations", [])
            if self._active_profiles:
                recs = apply_profile_weighting(recs, self._active_profiles)

            added = self._candidate_queue.populate_from_recommendations(recs)
            record.candidates_added = added

        goals = self._get_active_goals()
        drift = self._drift_detector.detect_drift(
            goals, reality.get("recent_outcomes", [])
        )
        self._last_drift = drift
        record.drift_warnings = len(drift)
        self._persist_drift_warnings(drift)

        expired = self._candidate_queue.expire_old()
        record.expired_candidates = expired

        self._record_tick(record, start)
        return record

    def get_strategic_state(self) -> dict[str, Any]:
        """Return complete current strategic state for cockpit."""
        return {
            "tick": {
                "running": self._running,
                "paused": self._paused,
                "frequency": self._frequency.value,
                "cycle_count": self._cycle_count,
                "last_tick": self._tick_history[-1].to_dict() if self._tick_history else None,
                "next_tick_in": self._frequency.seconds if self._running else None,
            },
            "last_analysis": self._last_analysis,
            "last_delta": self._last_delta.to_dict() if self._last_delta else None,
            "candidate_queue": {
                "total": len(self._candidate_queue.all_items()),
                "pending": len(self._candidate_queue.pending()),
                "items": [i.to_dict() for i in self._candidate_queue.pending()[:10]],
            },
            "drift_warnings": [w.to_dict() for w in self._last_drift],
            "active_profiles": self._active_profiles,
            "operator_present": self._check_operator_presence(),
            "recent_ticks": [t.to_dict() for t in self._tick_history[-10:]],
        }

    def status(self) -> dict[str, Any]:
        """Compact status for health checks."""
        last = self._tick_history[-1] if self._tick_history else None
        return {
            "running": self._running,
            "paused": self._paused,
            "frequency": self._frequency.value,
            "cycle_count": self._cycle_count,
            "last_tick_at": last.timestamp if last else None,
            "last_change_detected": last.change_detected if last else None,
            "pending_candidates": len(self._candidate_queue.pending()),
            "drift_warning_count": len(self._last_drift),
            "active_profiles": self._active_profiles,
            "operator_present": self._check_operator_presence(),
        }

    def to_dict(self) -> dict[str, Any]:
        return self.get_strategic_state()

    # ── Private helpers ────────────────────────────────────────────

    def _get_reality(self) -> dict[str, Any]:
        try:
            from substrate.organism.empire_router import EmpireRouter
            router = EmpireRouter()
            return router.get_reality_snapshot().to_dict()
        except Exception as e:
            logger.error("tick: failed to get reality: %s", e)
            return {
                "active_domains": [],
                "active_loops": [],
                "blocked_items": [],
                "open_approvals": 0,
                "recent_outcomes": [],
                "current_phase": "",
                "next_best_actions": [],
            }

    def _get_current_goal_ids(self) -> set[str]:
        try:
            from substrate.organism.strategic_gap_engine import GoalRegistry
            registry = GoalRegistry()
            return {g.goal_id for g in registry.active_goals()}
        except Exception as e:
            logger.error("tick: failed to get goal ids: %s", e)
            return set()

    def _get_active_goals(self) -> list[Any]:
        try:
            from substrate.organism.strategic_gap_engine import GoalRegistry
            registry = GoalRegistry()
            return registry.active_goals()
        except Exception as e:
            logger.error("tick: failed to get goals: %s", e)
            return []

    def _run_analysis(self) -> dict[str, Any] | None:
        try:
            from substrate.organism.strategic_gap_engine import StrategicGapEngine
            engine = StrategicGapEngine()
            return engine.analyze()
        except Exception as e:
            logger.error("tick: analysis failed: %s", e)
            return None

    def _check_operator_presence(self) -> bool:
        try:
            from substrate.workstation.device_presence import DevicePresenceRegistry
            registry = DevicePresenceRegistry()
            sessions = registry.get_active_sessions()
            return len(sessions) > 0
        except Exception:
            return False

    def _persist_drift_warnings(self, warnings: list[DriftWarning]) -> None:
        if not warnings:
            return
        drift_dir = os.path.join(_tick_data_dir(), "drift_warnings")
        os.makedirs(drift_dir, exist_ok=True)
        for w in warnings:
            path = os.path.join(drift_dir, f"{w.warning_id}.json")
            try:
                with open(path, "w") as f:
                    json.dump(w.to_dict(), f, indent=2)
            except OSError as e:
                logger.error("tick: failed to persist drift warning: %s", e)

    def _record_tick(self, record: TickRecord, start_ns: float) -> None:
        record.elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000
        self._tick_history.append(record)
        if len(self._tick_history) > 100:
            self._tick_history = self._tick_history[-100:]

        snapshot_dir = os.path.join(_tick_data_dir(), "snapshots")
        os.makedirs(snapshot_dir, exist_ok=True)
        path = os.path.join(snapshot_dir, f"{record.tick_id}.json")
        try:
            with open(path, "w") as f:
                json.dump(record.to_dict(), f, indent=2)
        except OSError as e:
            logger.error("tick: failed to persist tick record: %s", e)


# ── Singleton ──────────────────────────────────────────────────────


_tick_loop_instance: StrategicTickLoop | None = None


def get_tick_loop() -> StrategicTickLoop:
    """Module-level singleton for the strategic tick loop."""
    global _tick_loop_instance
    if _tick_loop_instance is None:
        _tick_loop_instance = StrategicTickLoop()
    return _tick_loop_instance


def reset_tick_loop() -> None:
    """Reset singleton (testing only)."""
    global _tick_loop_instance
    _tick_loop_instance = None
