"""Work Portfolio Runtime — execution health, velocity, and drift detection.

Campaign 11.2. UMH substrate layer. Instance-agnostic.

Composes (does not replace):
  - WorkReadinessRuntime (C11.0) — readiness classification
  - DelegationReadinessRuntime (C11.1) — delegation feasibility
  - WorkGraph (Gate 3) — work node counts and timelines
  - OutcomeTrackingRuntime (C8.2) — goal progress/health
  - CapabilityPortfolioRuntime (C10.2) — capability portfolio health
  - DriftDetectionEngine (C7) — unified drift detection
  - GoalDriftEngine (C8.5) — goal-specific drift

Authority remains with the source systems. This runtime ONLY computes
portfolio metrics, health classification, and drift signals.

Read-only. No mutation. No execution. Deterministic. Zero LLM calls.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from substrate.state.runtime_paths import runtime_state_dir

logger = logging.getLogger(__name__)


def _portfolio_dir() -> str:
    return str(runtime_state_dir("work_portfolio", create=False))


# ── Types ─────────────────────────────────────────────────────────────────


class WorkPortfolioHealth(str, Enum):
    THRIVING = "thriving"
    HEALTHY = "healthy"
    CONSTRAINED = "constrained"
    STALLED = "stalled"


class WorkDriftType(str, Enum):
    READINESS_DRIFT = "readiness_drift"
    DELEGATION_DRIFT = "delegation_drift"
    EXECUTION_DRIFT = "execution_drift"
    OUTCOME_DRIFT = "outcome_drift"


@dataclass
class WorkDriftWarning:
    drift_type: str = ""
    severity: float = 0.0
    description: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    work_ids: list[str] = field(default_factory=list)
    detected_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "drift_type": self.drift_type,
            "severity": round(self.severity, 4),
            "description": self.description,
            "evidence": self.evidence,
            "work_ids": self.work_ids,
            "detected_at": self.detected_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkDriftWarning:
        return cls(
            drift_type=d.get("drift_type", ""),
            severity=d.get("severity", 0.0),
            description=d.get("description", ""),
            evidence=d.get("evidence", {}),
            work_ids=d.get("work_ids", []),
            detected_at=d.get("detected_at", 0.0),
        )


@dataclass
class WorkPortfolioSnapshot:
    total_work: int = 0
    by_readiness: dict[str, int] = field(default_factory=dict)
    ready: int = 0
    blocked: int = 0
    delegatable: int = 0
    at_risk: int = 0
    execution_velocity: float = 0.0
    completion_rate: float = 0.0
    block_rate: float = 0.0
    health: WorkPortfolioHealth = WorkPortfolioHealth.STALLED
    drift_warnings: list[WorkDriftWarning] = field(default_factory=list)
    capability_health: str = "unknown"
    goals_at_risk: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_work": self.total_work,
            "by_readiness": self.by_readiness,
            "ready": self.ready,
            "blocked": self.blocked,
            "delegatable": self.delegatable,
            "at_risk": self.at_risk,
            "execution_velocity": round(self.execution_velocity, 4),
            "completion_rate": round(self.completion_rate, 4),
            "block_rate": round(self.block_rate, 4),
            "health": self.health.value
            if isinstance(self.health, WorkPortfolioHealth)
            else self.health,
            "drift_warnings": [w.to_dict() for w in self.drift_warnings],
            "drift_warning_count": len(self.drift_warnings),
            "capability_health": self.capability_health,
            "goals_at_risk": self.goals_at_risk,
            "timestamp": self.timestamp,
        }


# ── Velocity tracking ────────────────────────────────────────────────────


class _VelocityTracker:
    """Tracks completion events to compute rolling velocity."""

    def __init__(self, store_path: str = "") -> None:
        self._store_path = store_path or os.path.join(_portfolio_dir(), "velocity.jsonl")
        self._events: list[dict[str, Any]] | None = None

    def _load(self) -> list[dict[str, Any]]:
        if self._events is not None:
            return self._events
        self._events = []
        if os.path.exists(self._store_path):
            try:
                with open(self._store_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self._events.append(json.loads(line))
            except Exception:
                logger.debug("Failed to load velocity store")
        return self._events

    def record_snapshot(self, completed: int, blocked: int, total: int) -> None:
        """Record a point-in-time snapshot for velocity computation."""
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        event = {
            "ts": time.time(),
            "completed": completed,
            "blocked": blocked,
            "total": total,
        }
        try:
            with open(self._store_path, "a") as f:
                f.write(json.dumps(event) + "\n")
            if self._events is not None:
                self._events.append(event)
        except Exception:
            logger.debug("Failed to write velocity event")

    def completions_per_day(self, window_days: float = 7.0) -> float:
        """Rolling completions per day over window."""
        events = self._load()
        if len(events) < 2:
            return 0.0
        cutoff = time.time() - (window_days * 86400)
        recent = [e for e in events if e.get("ts", 0) >= cutoff]
        if len(recent) < 2:
            return 0.0
        first = recent[0]
        last = recent[-1]
        elapsed_days = (last["ts"] - first["ts"]) / 86400
        if elapsed_days < 0.01:
            return 0.0
        delta_completed = last.get("completed", 0) - first.get("completed", 0)
        return max(0.0, delta_completed / elapsed_days)

    def block_rate_change(self, window_days: float = 7.0) -> float:
        """Change in block rate over window. Positive = more blocking."""
        events = self._load()
        if len(events) < 2:
            return 0.0
        cutoff = time.time() - (window_days * 86400)
        recent = [e for e in events if e.get("ts", 0) >= cutoff]
        if len(recent) < 2:
            return 0.0
        first = recent[0]
        last = recent[-1]
        first_rate = first.get("blocked", 0) / max(1, first.get("total", 1))
        last_rate = last.get("blocked", 0) / max(1, last.get("total", 1))
        return last_rate - first_rate


# ── Runtime ───────────────────────────────────────────────────────────────


class WorkPortfolioRuntime:
    """Read-only portfolio health + velocity + drift for all work.

    Composes:
      - WorkReadinessRuntime (C11.0) — readiness classification
      - DelegationReadinessRuntime (C11.1) — delegation feasibility
      - WorkGraph (Gate 3) — work node data
      - OutcomeTrackingRuntime (C8.2) — goal health
      - CapabilityPortfolioRuntime (C10.2) — capability health
      - DriftDetectionEngine (C7) — upstream drift
      - GoalDriftEngine (C8.5) — goal drift

    Owns nothing except velocity tracking store. Mutates nothing in
    source systems. Authority stays with source systems.
    """

    def __init__(
        self,
        work_readiness: Any | None = None,
        delegation_readiness: Any | None = None,
        work_graph: Any | None = None,
        outcome_tracking: Any | None = None,
        capability_portfolio: Any | None = None,
        drift_detection: Any | None = None,
        goal_drift: Any | None = None,
        velocity_store_path: str = "",
    ) -> None:
        self._readiness = work_readiness
        self._delegation = delegation_readiness
        self._work_graph = work_graph
        self._outcome = outcome_tracking
        self._cap_portfolio = capability_portfolio
        self._drift_engine = drift_detection
        self._goal_drift = goal_drift
        self._velocity = _VelocityTracker(velocity_store_path)

    # ── Lazy subsystem access ─────────────────────────────────────

    @property
    def readiness(self) -> Any | None:
        if self._readiness is None:
            try:
                from substrate.organism.work_readiness_runtime import WorkReadinessRuntime

                self._readiness = WorkReadinessRuntime()
            except Exception:
                logger.debug("WorkReadinessRuntime unavailable")
        return self._readiness

    @property
    def delegation(self) -> Any | None:
        if self._delegation is None:
            try:
                from substrate.organism.delegation_readiness_runtime import (
                    DelegationReadinessRuntime,
                )

                self._delegation = DelegationReadinessRuntime()
            except Exception:
                logger.debug("DelegationReadinessRuntime unavailable")
        return self._delegation

    @property
    def work_graph(self) -> Any | None:
        if self._work_graph is None:
            try:
                from substrate.organism.work_graph import WorkGraph

                self._work_graph = WorkGraph()
            except Exception:
                logger.debug("WorkGraph unavailable")
        return self._work_graph

    @property
    def outcome(self) -> Any | None:
        if self._outcome is None:
            try:
                from substrate.organism.outcome_tracking_runtime import OutcomeTrackingRuntime

                self._outcome = OutcomeTrackingRuntime()
            except Exception:
                logger.debug("OutcomeTrackingRuntime unavailable")
        return self._outcome

    @property
    def cap_portfolio(self) -> Any | None:
        if self._cap_portfolio is None:
            try:
                from substrate.organism.capability_portfolio_runtime import (
                    CapabilityPortfolioRuntime,
                )

                self._cap_portfolio = CapabilityPortfolioRuntime()
            except Exception:
                logger.debug("CapabilityPortfolioRuntime unavailable")
        return self._cap_portfolio

    @property
    def drift_engine(self) -> Any | None:
        if self._drift_engine is None:
            try:
                from substrate.organism.drift_detection_engine import DriftDetectionEngine

                self._drift_engine = DriftDetectionEngine()
            except Exception:
                logger.debug("DriftDetectionEngine unavailable")
        return self._drift_engine

    @property
    def goal_drift(self) -> Any | None:
        if self._goal_drift is None:
            try:
                from substrate.organism.goal_drift_engine import GoalDriftEngine

                self._goal_drift = GoalDriftEngine()
            except Exception:
                logger.debug("GoalDriftEngine unavailable")
        return self._goal_drift

    # ── Data collection ───────────────────────────────────────────

    def _get_readiness_snapshot(self) -> Any | None:
        if self.readiness is None:
            return None
        try:
            return self.readiness.snapshot()
        except Exception:
            logger.debug("Failed to get readiness snapshot")
            return None

    def _get_delegation_snapshot(self) -> Any | None:
        if self.delegation is None:
            return None
        try:
            return self.delegation.snapshot()
        except Exception:
            logger.debug("Failed to get delegation snapshot")
            return None

    def _get_work_graph_snapshot(self) -> Any | None:
        if self.work_graph is None:
            return None
        try:
            return self.work_graph.snapshot()
        except Exception:
            logger.debug("Failed to get work graph snapshot")
            return None

    def _get_goals_at_risk(self) -> list[str]:
        if self.outcome is None:
            return []
        try:
            at_risk = self.outcome.goals_at_risk()
            if isinstance(at_risk, list):
                results: list[str] = []
                for g in at_risk:
                    if hasattr(g, "goal_id"):
                        results.append(g.goal_id)
                    elif isinstance(g, dict):
                        results.append(g.get("goal_id", ""))
                return [r for r in results if r]
            return []
        except Exception:
            return []

    def _get_capability_health(self) -> str:
        if self.cap_portfolio is None:
            return "unknown"
        try:
            h = self.cap_portfolio.health()
            if hasattr(h, "value"):
                return h.value
            return str(h)
        except Exception:
            return "unknown"

    # ── Drift detection ───────────────────────────────────────────

    def _detect_readiness_drift(
        self,
        readiness_snap: Any | None,
    ) -> list[WorkDriftWarning]:
        """Detect when readiness is degrading — more items becoming blocked."""
        warnings: list[WorkDriftWarning] = []
        block_change = self._velocity.block_rate_change()
        if block_change > 0.1:
            warnings.append(
                WorkDriftWarning(
                    drift_type=WorkDriftType.READINESS_DRIFT.value,
                    severity=min(1.0, block_change * 2),
                    description=(f"block rate increasing by {block_change:.1%} over 7 days"),
                    evidence={"block_rate_change": round(block_change, 4)},
                )
            )
        return warnings

    def _detect_delegation_drift(
        self,
        delegation_snap: Any | None,
    ) -> list[WorkDriftWarning]:
        """Detect when delegation feasibility is degrading."""
        warnings: list[WorkDriftWarning] = []
        if delegation_snap is None:
            return warnings
        total = getattr(delegation_snap, "total_assessed", 0)
        not_del = getattr(delegation_snap, "not_delegatable", 0)
        if total > 0 and not_del / total > 0.5:
            warnings.append(
                WorkDriftWarning(
                    drift_type=WorkDriftType.DELEGATION_DRIFT.value,
                    severity=not_del / total,
                    description=(f"{not_del}/{total} work items not delegatable"),
                    evidence={
                        "not_delegatable": not_del,
                        "total": total,
                        "top_missing": getattr(delegation_snap, "top_missing_capabilities", []),
                    },
                )
            )
        return warnings

    def _detect_execution_drift(self) -> list[WorkDriftWarning]:
        """Detect when execution velocity is dropping."""
        warnings: list[WorkDriftWarning] = []
        vel = self._velocity.completions_per_day()
        if vel == 0.0:
            events = self._velocity._load()
            if len(events) >= 2:
                warnings.append(
                    WorkDriftWarning(
                        drift_type=WorkDriftType.EXECUTION_DRIFT.value,
                        severity=0.8,
                        description="execution velocity is zero — no completions in window",
                        evidence={"completions_per_day": 0.0},
                    )
                )
        return warnings

    def _detect_outcome_drift(self) -> list[WorkDriftWarning]:
        """Detect when goal outcomes are drifting — goals at risk increasing."""
        warnings: list[WorkDriftWarning] = []
        at_risk = self._get_goals_at_risk()
        if len(at_risk) > 0:
            warnings.append(
                WorkDriftWarning(
                    drift_type=WorkDriftType.OUTCOME_DRIFT.value,
                    severity=min(1.0, len(at_risk) * 0.2),
                    description=f"{len(at_risk)} goals at risk",
                    evidence={"goals_at_risk": at_risk[:5]},
                    work_ids=[],
                )
            )
        return warnings

    def _collect_upstream_drift(self) -> list[WorkDriftWarning]:
        """Collect drift from upstream engines and convert to WorkDriftWarning."""
        warnings: list[WorkDriftWarning] = []
        if self.drift_engine is not None:
            try:
                upstream = self.drift_engine.detect_drift()
                if isinstance(upstream, list):
                    for w in upstream:
                        dtype = getattr(w, "drift_type", "")
                        if hasattr(dtype, "value"):
                            dtype = dtype.value
                        sev = getattr(w, "severity", 0.5)
                        if isinstance(sev, (int, float)) and sev >= 0.5:
                            warnings.append(
                                WorkDriftWarning(
                                    drift_type=f"upstream:{dtype}",
                                    severity=float(sev),
                                    description=getattr(w, "description", ""),
                                )
                            )
            except Exception:
                logger.debug("Upstream drift detection failed")

        if self.goal_drift is not None:
            try:
                goal_warnings = self.goal_drift.detect()
                if isinstance(goal_warnings, list):
                    for w in goal_warnings:
                        dtype = getattr(w, "drift_type", "")
                        if hasattr(dtype, "value"):
                            dtype = dtype.value
                        sev = getattr(w, "severity", 0.5)
                        if isinstance(sev, (int, float)) and sev >= 0.5:
                            warnings.append(
                                WorkDriftWarning(
                                    drift_type=f"goal:{dtype}",
                                    severity=float(sev),
                                    description=getattr(w, "description", ""),
                                )
                            )
            except Exception:
                logger.debug("Goal drift detection failed")

        return warnings

    # ── Health classification ─────────────────────────────────────

    def _classify_health(
        self,
        total: int,
        ready: int,
        blocked: int,
        velocity: float,
    ) -> WorkPortfolioHealth:
        """Deterministic health from portfolio metrics."""
        if total == 0:
            return WorkPortfolioHealth.STALLED

        ready_pct = ready / total
        blocked_pct = blocked / total

        if ready_pct > 0.7 and velocity > 0:
            return WorkPortfolioHealth.THRIVING
        if ready_pct > 0.5 and velocity >= 0:
            return WorkPortfolioHealth.HEALTHY
        if blocked_pct > 0.5 or velocity == 0.0:
            return WorkPortfolioHealth.STALLED
        return WorkPortfolioHealth.CONSTRAINED

    # ── Public API ────────────────────────────────────────────────

    def snapshot(self) -> WorkPortfolioSnapshot:
        """Full portfolio snapshot."""
        readiness_snap = self._get_readiness_snapshot()
        delegation_snap = self._get_delegation_snapshot()
        wg_snap = self._get_work_graph_snapshot()

        total = 0
        by_readiness: dict[str, int] = {}
        ready = 0
        blocked = 0
        completed = 0

        if readiness_snap is not None:
            total = getattr(readiness_snap, "total", 0)
            by_readiness = getattr(readiness_snap, "by_status", {})
            ready = len(getattr(readiness_snap, "ready_work", []))
            blocked = len(getattr(readiness_snap, "blocked_work", []))

        if wg_snap is not None:
            completed = getattr(wg_snap, "completed", 0)

        delegatable = 0
        if delegation_snap is not None:
            delegatable = getattr(delegation_snap, "delegatable", 0)

        at_risk_goals = self._get_goals_at_risk()
        cap_health = self._get_capability_health()
        vel = self._velocity.completions_per_day()

        total_with_completed = total + completed
        completion_rate = completed / max(1, total_with_completed)
        block_rate = blocked / max(1, total)

        self._velocity.record_snapshot(completed, blocked, total)

        drift_warnings: list[WorkDriftWarning] = []
        drift_warnings.extend(self._detect_readiness_drift(readiness_snap))
        drift_warnings.extend(self._detect_delegation_drift(delegation_snap))
        drift_warnings.extend(self._detect_execution_drift())
        drift_warnings.extend(self._detect_outcome_drift())
        drift_warnings.extend(self._collect_upstream_drift())

        health = self._classify_health(total, ready, blocked, vel)

        return WorkPortfolioSnapshot(
            total_work=total,
            by_readiness=by_readiness if isinstance(by_readiness, dict) else {},
            ready=ready,
            blocked=blocked,
            delegatable=delegatable,
            at_risk=len(at_risk_goals),
            execution_velocity=vel,
            completion_rate=completion_rate,
            block_rate=block_rate,
            health=health,
            drift_warnings=drift_warnings,
            capability_health=cap_health,
            goals_at_risk=at_risk_goals,
            timestamp=time.time(),
        )

    def health(self) -> WorkPortfolioHealth:
        """Deterministic health classification."""
        snap = self.snapshot()
        return snap.health

    def velocity(self) -> dict[str, float]:
        """Execution velocity metrics."""
        vel = self._velocity.completions_per_day()
        block_change = self._velocity.block_rate_change()
        return {
            "completions_per_day": round(vel, 4),
            "block_rate_change_7d": round(block_change, 4),
        }

    def at_risk_work(self) -> list[Any]:
        """Work items linked to at-risk goals."""
        if self.readiness is None:
            return []
        try:
            at_risk_goals = self._get_goals_at_risk()
            results: list[Any] = []
            for gid in at_risk_goals:
                items = self.readiness.work_for_goal(gid)
                results.extend(items)
            return results
        except Exception:
            logger.debug("Failed to get at-risk work")
            return []

    def detect_drift(self) -> list[WorkDriftWarning]:
        """All drift warnings across all types."""
        readiness_snap = self._get_readiness_snapshot()
        delegation_snap = self._get_delegation_snapshot()
        warnings: list[WorkDriftWarning] = []
        warnings.extend(self._detect_readiness_drift(readiness_snap))
        warnings.extend(self._detect_delegation_drift(delegation_snap))
        warnings.extend(self._detect_execution_drift())
        warnings.extend(self._detect_outcome_drift())
        warnings.extend(self._collect_upstream_drift())
        return warnings

    def drift_by_type(self, drift_type: str) -> list[WorkDriftWarning]:
        """Filter drift warnings by type."""
        return [w for w in self.detect_drift() if w.drift_type == drift_type]

    def summary(self) -> dict[str, Any]:
        """Compact dict for API."""
        snap = self.snapshot()
        return {
            "total_work": snap.total_work,
            "ready": snap.ready,
            "blocked": snap.blocked,
            "delegatable": snap.delegatable,
            "at_risk": snap.at_risk,
            "execution_velocity": round(snap.execution_velocity, 4),
            "completion_rate": round(snap.completion_rate, 4),
            "block_rate": round(snap.block_rate, 4),
            "health": snap.health.value
            if isinstance(snap.health, WorkPortfolioHealth)
            else snap.health,
            "drift_warning_count": len(snap.drift_warnings),
            "capability_health": snap.capability_health,
            "goals_at_risk_count": len(snap.goals_at_risk),
        }
