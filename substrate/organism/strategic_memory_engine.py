"""Strategic Memory Engine — institutional memory with timeline and replay.

Captures periodic snapshots of decision/goal/assumption state, enabling
temporal queries: "what was true at time T?", "what changed between
snapshots?", "what patterns are emerging?"

Campaign 9.4 — Decision Intelligence & Strategic Memory.
UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT") or "/opt/OS"


# ── Types ─────────────────────────────────────────────────────────────────


@dataclass
class MemorySnapshot:
    snapshot_id: str = field(default_factory=lambda: f"snap-{uuid4().hex[:8]}")
    timestamp: float = 0.0
    decisions_snapshot: list[dict[str, Any]] = field(default_factory=list)
    goals_snapshot: list[dict[str, Any]] = field(default_factory=list)
    assumptions_snapshot: list[dict[str, Any]] = field(default_factory=list)
    validity_snapshot: list[dict[str, Any]] = field(default_factory=list)
    risks_snapshot: list[dict[str, Any]] = field(default_factory=list)
    health_summary: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "decisions_snapshot": list(self.decisions_snapshot),
            "goals_snapshot": list(self.goals_snapshot),
            "assumptions_snapshot": list(self.assumptions_snapshot),
            "validity_snapshot": list(self.validity_snapshot),
            "risks_snapshot": list(self.risks_snapshot),
            "health_summary": dict(self.health_summary),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MemorySnapshot:
        return cls(
            snapshot_id=d.get("snapshot_id", f"snap-{uuid4().hex[:8]}"),
            timestamp=d.get("timestamp", 0.0),
            decisions_snapshot=d.get("decisions_snapshot", []),
            goals_snapshot=d.get("goals_snapshot", []),
            assumptions_snapshot=d.get("assumptions_snapshot", []),
            validity_snapshot=d.get("validity_snapshot", []),
            risks_snapshot=d.get("risks_snapshot", []),
            health_summary=d.get("health_summary", {}),
            created_at=d.get("created_at", 0.0),
        )


@dataclass
class StrategicMemory:
    current: dict[str, Any] | None = None
    history: list[dict[str, Any]] = field(default_factory=list)
    decision_timeline: list[dict[str, Any]] = field(default_factory=list)
    pattern_observations: list[str] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "current": self.current,
            "history": list(self.history),
            "decision_timeline": list(self.decision_timeline),
            "pattern_observations": list(self.pattern_observations),
            "generated_at": self.generated_at,
        }


# ── Engine ────────────────────────────────────────────────────────────────


class StrategicMemoryEngine:
    """Institutional memory engine with snapshot capture and replay."""

    def __init__(
        self,
        decision_registry: Any | None = None,
        goal_registry: Any | None = None,
        assumption_tracking: Any | None = None,
        validity_engine: Any | None = None,
        risk_engine: Any | None = None,
        priority_engine: Any | None = None,
        data_dir: str = "",
    ) -> None:
        self._decision_registry = decision_registry
        self._goal_registry = goal_registry
        self._assumption_tracking = assumption_tracking
        self._validity_engine = validity_engine
        self._risk_engine = risk_engine
        self._priority_engine = priority_engine
        self._data_dir = data_dir or os.path.join(_ROOT, "data", "umh", "decisions")
        self._snapshots: list[MemorySnapshot] = []
        self._load_snapshots()

    # ── Snapshot Lifecycle ────────────────────────────────────────────

    def capture(self) -> MemorySnapshot:
        """Capture a snapshot of current strategic state."""
        snap = MemorySnapshot(
            timestamp=time.time(),
            created_at=time.time(),
        )

        snap.decisions_snapshot = self._capture_decisions()
        snap.goals_snapshot = self._capture_goals()
        snap.assumptions_snapshot = self._capture_assumptions()
        snap.validity_snapshot = self._capture_validity()
        snap.risks_snapshot = self._capture_risks()
        snap.health_summary = self._compute_health(snap)

        self._snapshots.append(snap)
        self._persist_snapshot(snap)
        return snap

    def get_current(self) -> MemorySnapshot | None:
        """Get the most recent snapshot."""
        if not self._snapshots:
            return None
        return max(self._snapshots, key=lambda s: s.timestamp)

    def get_history(self, limit: int = 10) -> list[MemorySnapshot]:
        """Get recent snapshot history."""
        sorted_snaps = sorted(
            self._snapshots, key=lambda s: s.timestamp, reverse=True
        )
        return sorted_snaps[:limit]

    # ── Timeline ──────────────────────────────────────────────────────

    def decision_timeline(self, since: float = 0.0) -> list[dict[str, Any]]:
        """Chronological list of decision events."""
        if not self._decision_registry:
            return []
        try:
            decisions = self._decision_registry.list_decisions()
            events: list[dict[str, Any]] = []
            for d in decisions:
                if d.created_at < since:
                    continue
                events.append({
                    "timestamp": d.created_at,
                    "decision_id": d.decision_id,
                    "title": d.title,
                    "action": "created",
                    "status": d.status,
                })
                if d.updated_at > d.created_at:
                    events.append({
                        "timestamp": d.updated_at,
                        "decision_id": d.decision_id,
                        "title": d.title,
                        "action": "updated",
                        "status": d.status,
                    })
            return sorted(events, key=lambda e: e["timestamp"], reverse=True)
        except Exception:
            logger.debug("Failed to build decision timeline", exc_info=True)
            return []

    # ── Memory Synthesis ──────────────────────────────────────────────

    def synthesize(self) -> StrategicMemory:
        """Synthesize full strategic memory view."""
        current = self.get_current()
        history = self.get_history(limit=10)
        timeline = self.decision_timeline()
        patterns = self.detect_patterns()

        return StrategicMemory(
            current=current.to_dict() if current else None,
            history=[s.to_dict() for s in history],
            decision_timeline=timeline,
            pattern_observations=patterns,
            generated_at=time.time(),
        )

    # ── Diff ──────────────────────────────────────────────────────────

    def diff(
        self, snap_a_id: str, snap_b_id: str
    ) -> dict[str, Any]:
        """Compare two snapshots and return changes."""
        snap_a = self._find_snapshot(snap_a_id)
        snap_b = self._find_snapshot(snap_b_id)

        if not snap_a or not snap_b:
            return {"error": "snapshot not found"}

        a_decision_ids = {
            d.get("decision_id", "") for d in snap_a.decisions_snapshot
        }
        b_decision_ids = {
            d.get("decision_id", "") for d in snap_b.decisions_snapshot
        }

        a_goal_ids = {g.get("goal_id", "") for g in snap_a.goals_snapshot}
        b_goal_ids = {g.get("goal_id", "") for g in snap_b.goals_snapshot}

        a_asm_ids = {
            a.get("assumption_id", "") for a in snap_a.assumptions_snapshot
        }
        b_asm_ids = {
            a.get("assumption_id", "") for a in snap_b.assumptions_snapshot
        }

        a_statuses = {
            d.get("decision_id", ""): d.get("status", "")
            for d in snap_a.decisions_snapshot
        }
        b_statuses = {
            d.get("decision_id", ""): d.get("status", "")
            for d in snap_b.decisions_snapshot
        }

        status_changes = []
        for did in a_decision_ids & b_decision_ids:
            if a_statuses.get(did) != b_statuses.get(did):
                status_changes.append({
                    "decision_id": did,
                    "old_status": a_statuses.get(did, ""),
                    "new_status": b_statuses.get(did, ""),
                })

        return {
            "added_decisions": list(b_decision_ids - a_decision_ids),
            "removed_decisions": list(a_decision_ids - b_decision_ids),
            "status_changes": status_changes,
            "added_goals": list(b_goal_ids - a_goal_ids),
            "removed_goals": list(a_goal_ids - b_goal_ids),
            "added_assumptions": list(b_asm_ids - a_asm_ids),
            "removed_assumptions": list(a_asm_ids - b_asm_ids),
        }

    # ── Pattern Detection ─────────────────────────────────────────────

    def detect_patterns(self) -> list[str]:
        """Deterministic pattern detection from decision history."""
        patterns: list[str] = []

        if not self._decision_registry:
            return patterns

        try:
            decisions = self._decision_registry.list_decisions()
            if not decisions:
                return patterns

            now = time.time()
            week_ago = now - 7 * 86400

            recent_superseded = [
                d for d in decisions
                if d.status == "superseded" and d.updated_at >= week_ago
            ]
            if len(recent_superseded) >= 3:
                patterns.append(
                    f"{len(recent_superseded)} decisions superseded in last 7 days"
                )

            if self._assumption_tracking:
                try:
                    invalidated = self._assumption_tracking.invalidated()
                    recent_invalid = [
                        a for a in invalidated
                        if hasattr(a, "updated_at") and a.updated_at >= week_ago
                    ]
                    if len(recent_invalid) >= 2:
                        patterns.append(
                            f"{len(recent_invalid)} assumptions invalidated in last 7 days"
                        )
                except Exception:
                    logger.debug("Failed to check assumption patterns", exc_info=True)

            active = [d for d in decisions if d.status == "active"]
            no_goals = [d for d in active if not d.goal_refs]
            if no_goals:
                patterns.append(
                    f"{len(no_goals)} active decisions not linked to any goal"
                )

        except Exception:
            logger.debug("Failed to detect patterns", exc_info=True)

        return patterns

    def summary(self) -> dict[str, Any]:
        """Combined memory summary."""
        current = self.get_current()
        return {
            "snapshot_count": len(self._snapshots),
            "current_health": current.health_summary if current else {},
            "pattern_count": len(self.detect_patterns()),
            "patterns": self.detect_patterns(),
            "generated_at": time.time(),
        }

    # ── Internal Capture Methods ──────────────────────────────────────

    def _capture_decisions(self) -> list[dict[str, Any]]:
        if not self._decision_registry:
            return []
        try:
            return [d.to_dict() for d in self._decision_registry.list_decisions()]
        except Exception:
            logger.debug("Failed to capture decisions", exc_info=True)
            return []

    def _capture_goals(self) -> list[dict[str, Any]]:
        if not self._goal_registry:
            return []
        try:
            goals = self._goal_registry.active_goals()
            return [g.to_dict() for g in goals]
        except Exception:
            logger.debug("Failed to capture goals", exc_info=True)
            return []

    def _capture_assumptions(self) -> list[dict[str, Any]]:
        if not self._assumption_tracking:
            return []
        try:
            return [
                a.to_dict()
                for a in self._assumption_tracking.list_assumptions()
            ]
        except Exception:
            logger.debug("Failed to capture assumptions", exc_info=True)
            return []

    def _capture_validity(self) -> list[dict[str, Any]]:
        if not self._validity_engine:
            return []
        try:
            return [v.to_dict() for v in self._validity_engine.evaluate_all()]
        except Exception:
            logger.debug("Failed to capture validity", exc_info=True)
            return []

    def _capture_risks(self) -> list[dict[str, Any]]:
        if not self._risk_engine:
            return []
        try:
            if hasattr(self._risk_engine, "snapshot"):
                snap = self._risk_engine.snapshot()
                if isinstance(snap, dict):
                    return snap.get("risks", [])
                if hasattr(snap, "to_dict"):
                    return snap.to_dict().get("risks", [])
        except Exception:
            logger.debug("Failed to capture risks", exc_info=True)
        return []

    def _compute_health(self, snap: MemorySnapshot) -> dict[str, Any]:
        """Compute health summary from snapshot data."""
        total_decisions = len(snap.decisions_snapshot)
        total_assumptions = len(snap.assumptions_snapshot)
        invalidated_assumptions = sum(
            1 for a in snap.assumptions_snapshot
            if a.get("status") == "invalidated"
        )
        at_risk_validity = sum(
            1 for v in snap.validity_snapshot
            if v.get("validity") in ("at_risk", "invalid")
        )

        if total_decisions == 0:
            health = "empty"
        elif at_risk_validity > total_decisions * 0.3:
            health = "degraded"
        elif invalidated_assumptions > total_assumptions * 0.2:
            health = "watch"
        else:
            health = "healthy"

        return {
            "overall": health,
            "total_decisions": total_decisions,
            "total_assumptions": total_assumptions,
            "invalidated_assumptions": invalidated_assumptions,
            "at_risk_decisions": at_risk_validity,
        }

    def _find_snapshot(self, snapshot_id: str) -> MemorySnapshot | None:
        for s in self._snapshots:
            if s.snapshot_id == snapshot_id:
                return s
        return None

    # ── Persistence ───────────────────────────────────────────────────

    def _persist_snapshot(self, snapshot: MemorySnapshot) -> None:
        try:
            os.makedirs(self._data_dir, exist_ok=True)
            path = os.path.join(self._data_dir, "snapshots.jsonl")
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(snapshot.to_dict()) + "\n")
        except Exception:
            logger.debug("Failed to persist snapshot", exc_info=True)

    def _load_snapshots(self) -> None:
        path = os.path.join(self._data_dir, "snapshots.jsonl")
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    self._snapshots.append(MemorySnapshot.from_dict(d))
        except Exception:
            logger.debug("Failed to load snapshots", exc_info=True)
