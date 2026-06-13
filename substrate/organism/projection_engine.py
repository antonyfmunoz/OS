"""Projection Engine — predictive world-model layer for UMH.

Phase 6. Produces forward-looking projections from current reality,
outcome history, goal progress, and trend analysis. Feeds into the
Gap Engine and Tick Loop so governance operates against predicted
future state, not just current state.

Deterministic-first: all projection calculations use mathematical
extrapolation from historical data. No LLM dependency in core path.

Composes existing primitives:
  - GoalRegistry / Goal (strategic_gap_engine) — goal targets
  - StrategicGapEngine (strategic_gap_engine) — gap analysis
  - EmpireRouter / RealitySnapshot (empire_router) — current reality
  - OutcomeRecords (reality model) — historical outcomes
  - StrategicTickLoop (strategic_tick_loop) — tick integration
  - CandidateWorkQueue (strategic_tick_loop) — queue metrics
  - DriftDetector (strategic_tick_loop) — drift data

Governance boundary: may forecast/analyze/recommend.
May NOT execute, approve, modify goals, or override governance.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


def _repo_root() -> str:
    return os.environ.get("UMH_ROOT", "/opt/OS")


def _projection_data_dir() -> str:
    return os.path.join(_repo_root(), "data", "umh", "projections")


def _ensure_dirs() -> None:
    base = _projection_data_dir()
    for sub in ("forecasts", "risks", "opportunities", "accuracy", "trends"):
        os.makedirs(os.path.join(base, sub), exist_ok=True)


# ── Enums ──────────────────────────────────────────────────────────────


class TimeHorizon(str, Enum):
    DAY = "24h"
    WEEK = "7d"
    MONTH = "30d"
    QUARTER = "90d"

    @property
    def seconds(self) -> float:
        return {
            "24h": 86400.0,
            "7d": 604800.0,
            "30d": 2592000.0,
            "90d": 7776000.0,
        }[self.value]

    @property
    def days(self) -> float:
        return self.seconds / 86400.0


class TrendDirection(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    STAGNANT = "stagnant"
    ACCELERATING = "accelerating"
    DECELERATING = "decelerating"


class RiskSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProjectionConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SPECULATIVE = "speculative"


# ── Domain Constants ──────────────────────────────────────────────────

PROJECTION_DOMAINS = [
    "engineering",
    "business_ops",
    "content",
    "sales",
    "marketing",
    "finance",
    "real_estate",
    "music",
    "clothing",
    "personal",
    "research",
    "admin",
    "infrastructure",
]


# ── Trend Detection ──────────────────────────────────────────────────


@dataclass
class TrendRecord:
    """A detected trend in a domain or metric."""
    trend_id: str = field(default_factory=lambda: f"trend-{uuid4().hex[:8]}")
    domain: str = ""
    metric: str = ""
    direction: TrendDirection = TrendDirection.STAGNANT
    magnitude: float = 0.0
    data_points: int = 0
    period_days: float = 0.0
    description: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trend_id": self.trend_id,
            "domain": self.domain,
            "metric": self.metric,
            "direction": self.direction.value,
            "magnitude": round(self.magnitude, 4),
            "data_points": self.data_points,
            "period_days": round(self.period_days, 1),
            "description": self.description,
            "created_at": self.created_at,
        }


class TrendDetector:
    """Detects trends from outcome history and goal progress."""

    def detect_trends(
        self,
        outcomes: list[dict[str, Any]],
        goals: list[Any],
        window_days: float = 30.0,
    ) -> list[TrendRecord]:
        trends: list[TrendRecord] = []
        now = time.time()
        cutoff = now - (window_days * 86400)

        domain_outcomes = self._bucket_by_domain(outcomes, cutoff)
        for domain, domain_items in domain_outcomes.items():
            trend = self._analyze_domain_velocity(domain, domain_items, window_days)
            if trend:
                trends.append(trend)

        queue_trend = self._detect_queue_trend()
        if queue_trend:
            trends.append(queue_trend)

        for goal in goals:
            if not hasattr(goal, "status"):
                continue
            if goal.status.value != "active":
                continue
            goal_trend = self._detect_goal_progress_trend(goal, outcomes, window_days)
            if goal_trend:
                trends.append(goal_trend)

        trends.sort(key=lambda t: abs(t.magnitude), reverse=True)
        return trends

    def _bucket_by_domain(
        self,
        outcomes: list[dict[str, Any]],
        cutoff: float,
    ) -> dict[str, list[dict[str, Any]]]:
        buckets: dict[str, list[dict[str, Any]]] = {}
        for o in outcomes:
            ts = o.get("completed_at", o.get("created_at", 0))
            if ts < cutoff:
                continue
            domain = o.get("domain", "")
            if domain:
                buckets.setdefault(domain, []).append(o)
        return buckets

    def _analyze_domain_velocity(
        self,
        domain: str,
        items: list[dict[str, Any]],
        window_days: float,
    ) -> TrendRecord | None:
        if len(items) < 2:
            return None

        items_sorted = sorted(
            items, key=lambda x: x.get("completed_at", x.get("created_at", 0))
        )

        ts_key = lambda x: x.get("completed_at", x.get("created_at", 0))
        earliest = ts_key(items_sorted[0])
        latest = ts_key(items_sorted[-1])
        time_midpoint = (earliest + latest) / 2.0

        first_count = sum(1 for x in items_sorted if ts_key(x) < time_midpoint)
        second_count = sum(1 for x in items_sorted if ts_key(x) >= time_midpoint)

        if first_count == 0:
            return None

        ratio = second_count / first_count

        if ratio > 1.25:
            direction = TrendDirection.ACCELERATING
        elif ratio > 1.05:
            direction = TrendDirection.POSITIVE
        elif ratio < 0.75:
            direction = TrendDirection.NEGATIVE
        elif ratio < 0.95:
            direction = TrendDirection.DECELERATING
        else:
            direction = TrendDirection.STAGNANT

        magnitude = ratio - 1.0

        failures = sum(
            1 for o in items
            if "fail" in str(o.get("summary", "")).lower()
            or "error" in str(o.get("summary", "")).lower()
        )
        failure_rate = failures / len(items) if items else 0

        desc_parts = [f"{domain}: {len(items)} outcomes in {window_days:.0f}d"]
        if direction in (TrendDirection.ACCELERATING, TrendDirection.POSITIVE):
            desc_parts.append(f"velocity increasing ({magnitude:+.0%})")
        elif direction in (TrendDirection.NEGATIVE, TrendDirection.DECELERATING):
            desc_parts.append(f"velocity declining ({magnitude:+.0%})")
        else:
            desc_parts.append("stable velocity")
        if failure_rate > 0.1:
            desc_parts.append(f"failure rate {failure_rate:.0%}")

        return TrendRecord(
            domain=domain,
            metric="outcome_velocity",
            direction=direction,
            magnitude=magnitude,
            data_points=len(items),
            period_days=window_days,
            description=". ".join(desc_parts),
        )

    def _detect_queue_trend(self) -> TrendRecord | None:
        try:
            from substrate.organism.strategic_tick_loop import get_tick_loop
            loop = get_tick_loop()
            pending = len(loop.candidate_queue.pending())
            total = len(loop.candidate_queue.all_items())

            if total == 0:
                return None

            backlog_ratio = pending / max(total, 1)
            if backlog_ratio > 0.7:
                direction = TrendDirection.NEGATIVE
                desc = f"candidate queue backlog high: {pending}/{total} pending ({backlog_ratio:.0%})"
            elif backlog_ratio < 0.3:
                direction = TrendDirection.POSITIVE
                desc = f"candidate queue healthy: {pending}/{total} pending ({backlog_ratio:.0%})"
            else:
                direction = TrendDirection.STAGNANT
                desc = f"candidate queue moderate: {pending}/{total} pending ({backlog_ratio:.0%})"

            return TrendRecord(
                domain="operations",
                metric="queue_backlog",
                direction=direction,
                magnitude=backlog_ratio,
                data_points=total,
                period_days=0,
                description=desc,
            )
        except Exception:
            return None

    def _detect_goal_progress_trend(
        self,
        goal: Any,
        outcomes: list[dict[str, Any]],
        window_days: float,
    ) -> TrendRecord | None:
        completion = goal.completion_ratio() if hasattr(goal, "completion_ratio") else 0
        domain = goal.domain if hasattr(goal, "domain") else ""
        title = goal.title if hasattr(goal, "title") else str(goal)

        if completion >= 1.0:
            return None

        now = time.time()
        created = goal.created_at if hasattr(goal, "created_at") else now
        age_days = max((now - created) / 86400, 1)

        expected_daily_progress = 1.0 / max(age_days, 7)
        actual_daily_progress = completion / max(age_days, 1)

        if actual_daily_progress > expected_daily_progress * 1.2:
            direction = TrendDirection.POSITIVE
        elif actual_daily_progress < expected_daily_progress * 0.5:
            direction = TrendDirection.NEGATIVE
        else:
            direction = TrendDirection.STAGNANT

        magnitude = (actual_daily_progress / max(expected_daily_progress, 0.001)) - 1.0

        return TrendRecord(
            domain=domain,
            metric="goal_progress",
            direction=direction,
            magnitude=magnitude,
            data_points=1,
            period_days=age_days,
            description=(
                f"Goal '{title}': {completion:.0%} complete over {age_days:.0f}d. "
                f"Progress {'ahead' if direction == TrendDirection.POSITIVE else 'behind' if direction == TrendDirection.NEGATIVE else 'on track'}."
            ),
        )


# ── Projection Model ────────────────────────────────────────────────


@dataclass
class Projection:
    """A forecast of future state for a domain at a time horizon."""
    projection_id: str = field(default_factory=lambda: f"proj-{uuid4().hex[:8]}")
    domain: str = ""
    horizon: TimeHorizon = TimeHorizon.WEEK
    current_state: str = ""
    predicted_state: str = ""
    confidence: ProjectionConfidence = ProjectionConfidence.MEDIUM
    assumptions: list[str] = field(default_factory=list)
    supporting_evidence: list[str] = field(default_factory=list)
    trends: list[str] = field(default_factory=list)
    completion_forecast: float = 0.0
    velocity_forecast: float = 0.0
    risk_indicators: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_id": self.projection_id,
            "domain": self.domain,
            "horizon": self.horizon.value,
            "current_state": self.current_state,
            "predicted_state": self.predicted_state,
            "confidence": self.confidence.value,
            "assumptions": self.assumptions,
            "supporting_evidence": self.supporting_evidence,
            "trends": self.trends,
            "completion_forecast": round(self.completion_forecast, 3),
            "velocity_forecast": round(self.velocity_forecast, 3),
            "risk_indicators": self.risk_indicators,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Projection:
        return cls(
            projection_id=d.get("projection_id", f"proj-{uuid4().hex[:8]}"),
            domain=d.get("domain", ""),
            horizon=TimeHorizon(d["horizon"]) if "horizon" in d else TimeHorizon.WEEK,
            current_state=d.get("current_state", ""),
            predicted_state=d.get("predicted_state", ""),
            confidence=ProjectionConfidence(d["confidence"]) if "confidence" in d else ProjectionConfidence.MEDIUM,
            assumptions=d.get("assumptions", []),
            supporting_evidence=d.get("supporting_evidence", []),
            trends=d.get("trends", []),
            completion_forecast=d.get("completion_forecast", 0.0),
            velocity_forecast=d.get("velocity_forecast", 0.0),
            risk_indicators=d.get("risk_indicators", []),
            created_at=d.get("created_at", time.time()),
        )


# ── Risk Model ───────────────────────────────────────────────────────


@dataclass
class StrategicRisk:
    """A predicted risk detected from projection analysis."""
    risk_id: str = field(default_factory=lambda: f"risk-{uuid4().hex[:8]}")
    title: str = ""
    domain: str = ""
    risk_type: str = ""
    severity: RiskSeverity = RiskSeverity.MEDIUM
    probability: float = 0.0
    impact: str = ""
    evidence: list[str] = field(default_factory=list)
    mitigation: str = ""
    horizon: TimeHorizon = TimeHorizon.WEEK
    related_goal_id: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_id": self.risk_id,
            "title": self.title,
            "domain": self.domain,
            "risk_type": self.risk_type,
            "severity": self.severity.value,
            "probability": round(self.probability, 2),
            "impact": self.impact,
            "evidence": self.evidence,
            "mitigation": self.mitigation,
            "horizon": self.horizon.value,
            "related_goal_id": self.related_goal_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> StrategicRisk:
        return cls(
            risk_id=d.get("risk_id", f"risk-{uuid4().hex[:8]}"),
            title=d.get("title", ""),
            domain=d.get("domain", ""),
            risk_type=d.get("risk_type", ""),
            severity=RiskSeverity(d["severity"]) if "severity" in d else RiskSeverity.MEDIUM,
            probability=d.get("probability", 0.0),
            impact=d.get("impact", ""),
            evidence=d.get("evidence", []),
            mitigation=d.get("mitigation", ""),
            horizon=TimeHorizon(d["horizon"]) if "horizon" in d else TimeHorizon.WEEK,
            related_goal_id=d.get("related_goal_id", ""),
            created_at=d.get("created_at", time.time()),
        )


# ── Opportunity Model ────────────────────────────────────────────────


@dataclass
class StrategicOpportunity:
    """A detected opportunity from projection analysis."""
    opportunity_id: str = field(default_factory=lambda: f"opp-{uuid4().hex[:8]}")
    title: str = ""
    domain: str = ""
    opportunity_type: str = ""
    potential_impact: str = ""
    evidence: list[str] = field(default_factory=list)
    action_suggestion: str = ""
    horizon: TimeHorizon = TimeHorizon.WEEK
    confidence: ProjectionConfidence = ProjectionConfidence.MEDIUM
    related_goal_id: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "title": self.title,
            "domain": self.domain,
            "opportunity_type": self.opportunity_type,
            "potential_impact": self.potential_impact,
            "evidence": self.evidence,
            "action_suggestion": self.action_suggestion,
            "horizon": self.horizon.value,
            "confidence": self.confidence.value,
            "related_goal_id": self.related_goal_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> StrategicOpportunity:
        return cls(
            opportunity_id=d.get("opportunity_id", f"opp-{uuid4().hex[:8]}"),
            title=d.get("title", ""),
            domain=d.get("domain", ""),
            opportunity_type=d.get("opportunity_type", ""),
            potential_impact=d.get("potential_impact", ""),
            evidence=d.get("evidence", []),
            action_suggestion=d.get("action_suggestion", ""),
            horizon=TimeHorizon(d["horizon"]) if "horizon" in d else TimeHorizon.WEEK,
            confidence=ProjectionConfidence(d["confidence"]) if "confidence" in d else ProjectionConfidence.MEDIUM,
            related_goal_id=d.get("related_goal_id", ""),
            created_at=d.get("created_at", time.time()),
        )


# ── Projection Accuracy Tracking ────────────────────────────────────


@dataclass
class ProjectionOutcome:
    """Tracks whether a projection was accurate."""
    outcome_id: str = field(default_factory=lambda: f"po-{uuid4().hex[:8]}")
    projection_id: str = ""
    domain: str = ""
    horizon: str = ""
    predicted_state: str = ""
    actual_state: str = ""
    was_accurate: bool = False
    accuracy_score: float = 0.0
    evaluated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "projection_id": self.projection_id,
            "domain": self.domain,
            "horizon": self.horizon,
            "predicted_state": self.predicted_state,
            "actual_state": self.actual_state,
            "was_accurate": self.was_accurate,
            "accuracy_score": round(self.accuracy_score, 3),
            "evaluated_at": self.evaluated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProjectionOutcome:
        return cls(
            outcome_id=d.get("outcome_id", f"po-{uuid4().hex[:8]}"),
            projection_id=d.get("projection_id", ""),
            domain=d.get("domain", ""),
            horizon=d.get("horizon", ""),
            predicted_state=d.get("predicted_state", ""),
            actual_state=d.get("actual_state", ""),
            was_accurate=d.get("was_accurate", False),
            accuracy_score=d.get("accuracy_score", 0.0),
            evaluated_at=d.get("evaluated_at", time.time()),
        )


class AccuracyTracker:
    """Tracks projection accuracy over time. JSONL-backed."""

    def __init__(self, store_path: str | None = None) -> None:
        _ensure_dirs()
        self._store_path = store_path or os.path.join(
            _projection_data_dir(), "accuracy", "outcomes.jsonl"
        )
        self._outcomes: list[ProjectionOutcome] = []
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
                    self._outcomes.append(ProjectionOutcome.from_dict(json.loads(line)))
        except (json.JSONDecodeError, OSError) as e:
            logger.error("failed to load projection outcomes: %s", e)

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        with open(self._store_path, "w") as f:
            for o in self._outcomes:
                f.write(json.dumps(o.to_dict()) + "\n")

    def record(self, outcome: ProjectionOutcome) -> None:
        self._outcomes.append(outcome)
        self._save()

    def accuracy_by_domain(self) -> dict[str, dict[str, Any]]:
        """Compute accuracy metrics per domain."""
        domain_stats: dict[str, dict[str, Any]] = {}
        for o in self._outcomes:
            if o.domain not in domain_stats:
                domain_stats[o.domain] = {"total": 0, "accurate": 0, "scores": []}
            domain_stats[o.domain]["total"] += 1
            if o.was_accurate:
                domain_stats[o.domain]["accurate"] += 1
            domain_stats[o.domain]["scores"].append(o.accuracy_score)

        result: dict[str, dict[str, Any]] = {}
        for domain, stats in domain_stats.items():
            total = stats["total"]
            accurate = stats["accurate"]
            scores = stats["scores"]
            result[domain] = {
                "total_projections": total,
                "accurate_count": accurate,
                "accuracy_rate": round(accurate / max(total, 1), 3),
                "avg_score": round(sum(scores) / max(len(scores), 1), 3),
            }
        return result

    def accuracy_by_horizon(self) -> dict[str, dict[str, Any]]:
        """Compute accuracy metrics per time horizon."""
        horizon_stats: dict[str, dict[str, Any]] = {}
        for o in self._outcomes:
            h = o.horizon
            if h not in horizon_stats:
                horizon_stats[h] = {"total": 0, "accurate": 0, "scores": []}
            horizon_stats[h]["total"] += 1
            if o.was_accurate:
                horizon_stats[h]["accurate"] += 1
            horizon_stats[h]["scores"].append(o.accuracy_score)

        result: dict[str, dict[str, Any]] = {}
        for h, stats in horizon_stats.items():
            total = stats["total"]
            accurate = stats["accurate"]
            scores = stats["scores"]
            result[h] = {
                "total_projections": total,
                "accurate_count": accurate,
                "accuracy_rate": round(accurate / max(total, 1), 3),
                "avg_score": round(sum(scores) / max(len(scores), 1), 3),
            }
        return result

    def overall_accuracy(self) -> dict[str, Any]:
        total = len(self._outcomes)
        accurate = sum(1 for o in self._outcomes if o.was_accurate)
        scores = [o.accuracy_score for o in self._outcomes]
        return {
            "total_projections": total,
            "accurate_count": accurate,
            "accuracy_rate": round(accurate / max(total, 1), 3),
            "avg_score": round(sum(scores) / max(len(scores), 1), 3),
            "by_domain": self.accuracy_by_domain(),
            "by_horizon": self.accuracy_by_horizon(),
        }

    def all_outcomes(self) -> list[ProjectionOutcome]:
        return list(self._outcomes)


# ── Risk Detector ────────────────────────────────────────────────────


class RiskDetector:
    """Detects strategic risks from projections and trends."""

    def detect_risks(
        self,
        goals: list[Any],
        trends: list[TrendRecord],
        projections: list[Projection],
        outcomes: list[dict[str, Any]],
    ) -> list[StrategicRisk]:
        risks: list[StrategicRisk] = []

        for goal in goals:
            if not hasattr(goal, "status") or goal.status.value != "active":
                continue
            risk = self._check_milestone_slip(goal, trends, projections)
            if risk:
                risks.append(risk)

        bottleneck = self._check_execution_bottleneck(trends)
        if bottleneck:
            risks.append(bottleneck)

        approval_risk = self._check_approval_bottleneck(outcomes)
        if approval_risk:
            risks.append(approval_risk)

        for trend in trends:
            if trend.direction == TrendDirection.NEGATIVE and abs(trend.magnitude) > 0.3:
                risks.append(StrategicRisk(
                    title=f"Declining velocity: {trend.domain}",
                    domain=trend.domain,
                    risk_type="velocity_decline",
                    severity=RiskSeverity.MEDIUM if abs(trend.magnitude) < 0.5 else RiskSeverity.HIGH,
                    probability=min(0.9, 0.5 + abs(trend.magnitude)),
                    impact=f"Output declining {abs(trend.magnitude):.0%} in {trend.domain}",
                    evidence=[trend.description],
                    mitigation=f"Investigate root causes of declining {trend.domain} velocity",
                    horizon=TimeHorizon.WEEK,
                ))

        risks.sort(
            key=lambda r: (
                {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(r.severity.value, 0),
                r.probability,
            ),
            reverse=True,
        )
        return risks

    def _check_milestone_slip(
        self,
        goal: Any,
        trends: list[TrendRecord],
        projections: list[Projection],
    ) -> StrategicRisk | None:
        target_date = getattr(goal, "target_date", "")
        if not target_date:
            return None

        try:
            import datetime
            target_dt = datetime.datetime.strptime(target_date, "%Y-%m-%d")
            now_dt = datetime.datetime.now()
            days_remaining = (target_dt - now_dt).days
        except (ValueError, TypeError):
            return None

        if days_remaining <= 0:
            return None

        completion = goal.completion_ratio() if hasattr(goal, "completion_ratio") else 0
        remaining_work = 1.0 - completion
        title = goal.title if hasattr(goal, "title") else str(goal)
        domain = goal.domain if hasattr(goal, "domain") else ""
        goal_id = goal.goal_id if hasattr(goal, "goal_id") else ""

        created = goal.created_at if hasattr(goal, "created_at") else time.time()
        elapsed_days = max((time.time() - created) / 86400, 1)

        if completion > 0:
            daily_rate = completion / elapsed_days
            days_needed = remaining_work / max(daily_rate, 0.001)
        else:
            days_needed = days_remaining * 2

        negative_trends = [
            t for t in trends
            if t.domain == domain
            and t.direction in (TrendDirection.NEGATIVE, TrendDirection.DECELERATING)
        ]
        if negative_trends:
            days_needed *= 1.3

        if days_needed > days_remaining:
            slip_ratio = days_needed / max(days_remaining, 1)
            if slip_ratio > 2.0:
                severity = RiskSeverity.CRITICAL
                probability = 0.85
            elif slip_ratio > 1.5:
                severity = RiskSeverity.HIGH
                probability = 0.7
            else:
                severity = RiskSeverity.MEDIUM
                probability = 0.5

            evidence = [
                f"Completion: {completion:.0%}, remaining: {remaining_work:.0%}",
                f"Days remaining: {days_remaining}, estimated days needed: {days_needed:.0f}",
                f"Current daily rate: {(completion / max(elapsed_days, 1)):.3f}",
            ]
            if negative_trends:
                evidence.append(f"Declining velocity in {domain}")

            return StrategicRisk(
                title=f"Milestone slip risk: {title}",
                domain=domain,
                risk_type="milestone_slip",
                severity=severity,
                probability=probability,
                impact=f"Goal '{title}' projected to miss target by {days_needed - days_remaining:.0f} days",
                evidence=evidence,
                mitigation=f"Accelerate {domain} or adjust target date from {target_date}",
                horizon=TimeHorizon.MONTH if days_remaining > 14 else TimeHorizon.WEEK,
                related_goal_id=goal_id,
            )
        return None

    def _check_execution_bottleneck(
        self,
        trends: list[TrendRecord],
    ) -> StrategicRisk | None:
        queue_trends = [t for t in trends if t.metric == "queue_backlog"]
        for t in queue_trends:
            if t.direction == TrendDirection.NEGATIVE and t.magnitude > 0.5:
                return StrategicRisk(
                    title="Execution bottleneck: candidate queue overloaded",
                    domain="operations",
                    risk_type="execution_bottleneck",
                    severity=RiskSeverity.HIGH,
                    probability=0.7,
                    impact="High backlog ratio slowing strategic execution",
                    evidence=[t.description],
                    mitigation="Process pending candidates or adjust scope of incoming work",
                    horizon=TimeHorizon.DAY,
                )
        return None

    def _check_approval_bottleneck(
        self,
        outcomes: list[dict[str, Any]],
    ) -> StrategicRisk | None:
        now = time.time()
        recent_approvals = [
            o for o in outcomes
            if o.get("type") == "approval"
            and (now - o.get("completed_at", o.get("created_at", 0))) < 604800
        ]
        if len(recent_approvals) == 0:
            return None

        slow_approvals = [
            a for a in recent_approvals
            if a.get("duration_hours", 0) > 24
        ]
        if len(slow_approvals) > len(recent_approvals) * 0.5:
            return StrategicRisk(
                title="Approval bottleneck: slow approval cycle",
                domain="governance",
                risk_type="approval_bottleneck",
                severity=RiskSeverity.MEDIUM,
                probability=0.6,
                impact="Over 50% of approvals taking >24 hours",
                evidence=[f"{len(slow_approvals)}/{len(recent_approvals)} approvals slow"],
                mitigation="Review approval queue or delegate authority",
                horizon=TimeHorizon.WEEK,
            )
        return None


# ── Opportunity Detector ─────────────────────────────────────────────


class OpportunityDetector:
    """Detects strategic opportunities from projections and trends."""

    def detect_opportunities(
        self,
        goals: list[Any],
        trends: list[TrendRecord],
        projections: list[Projection],
        reality: dict[str, Any],
    ) -> list[StrategicOpportunity]:
        opportunities: list[StrategicOpportunity] = []

        for trend in trends:
            if trend.direction in (TrendDirection.ACCELERATING, TrendDirection.POSITIVE):
                if trend.magnitude > 0.2:
                    opportunities.append(StrategicOpportunity(
                        title=f"Momentum in {trend.domain}",
                        domain=trend.domain,
                        opportunity_type="domain_acceleration",
                        potential_impact=f"Leverage {trend.magnitude:+.0%} velocity increase",
                        evidence=[trend.description],
                        action_suggestion=f"Double down on {trend.domain} while momentum is strong",
                        horizon=TimeHorizon.WEEK,
                        confidence=ProjectionConfidence.MEDIUM,
                    ))

        for goal in goals:
            if not hasattr(goal, "status") or goal.status.value != "active":
                continue
            fast_track = self._check_fast_track(goal, trends)
            if fast_track:
                opportunities.append(fast_track)

        automation = self._detect_automation_opportunity(reality, trends)
        if automation:
            opportunities.append(automation)

        delegation = self._detect_delegation_opportunity(trends, goals)
        if delegation:
            opportunities.append(delegation)

        opportunities.sort(
            key=lambda o: {"high": 3, "medium": 2, "low": 1, "speculative": 0}.get(
                o.confidence.value, 0
            ),
            reverse=True,
        )
        return opportunities

    def _check_fast_track(
        self,
        goal: Any,
        trends: list[TrendRecord],
    ) -> StrategicOpportunity | None:
        completion = goal.completion_ratio() if hasattr(goal, "completion_ratio") else 0
        if completion < 0.7:
            return None

        domain = goal.domain if hasattr(goal, "domain") else ""
        title = goal.title if hasattr(goal, "title") else str(goal)
        goal_id = goal.goal_id if hasattr(goal, "goal_id") else ""

        positive_trends = [
            t for t in trends
            if t.domain == domain
            and t.direction in (TrendDirection.POSITIVE, TrendDirection.ACCELERATING)
        ]

        if positive_trends or completion >= 0.8:
            return StrategicOpportunity(
                title=f"Fast-track opportunity: {title}",
                domain=domain,
                opportunity_type="fast_track",
                potential_impact=f"Goal at {completion:.0%} with positive momentum — can be completed ahead of schedule",
                evidence=[
                    f"Completion: {completion:.0%}",
                    *(t.description for t in positive_trends),
                ],
                action_suggestion=f"Prioritize remaining work on '{title}' to close early",
                horizon=TimeHorizon.DAY,
                confidence=ProjectionConfidence.HIGH if completion >= 0.8 else ProjectionConfidence.MEDIUM,
                related_goal_id=goal_id,
            )
        return None

    def _detect_automation_opportunity(
        self,
        reality: dict[str, Any],
        trends: list[TrendRecord],
    ) -> StrategicOpportunity | None:
        repetitive_domains = []
        for trend in trends:
            if trend.metric == "outcome_velocity" and trend.data_points > 10:
                if trend.direction in (TrendDirection.STAGNANT, TrendDirection.POSITIVE):
                    repetitive_domains.append(trend.domain)

        if repetitive_domains:
            return StrategicOpportunity(
                title=f"Automation potential in {', '.join(repetitive_domains[:3])}",
                domain=repetitive_domains[0],
                opportunity_type="automation",
                potential_impact=f"High-volume domains ({', '.join(repetitive_domains[:3])}) may benefit from automation",
                evidence=[f"{d}: high outcome volume" for d in repetitive_domains[:3]],
                action_suggestion="Identify repeatable patterns for template-based automation",
                horizon=TimeHorizon.MONTH,
                confidence=ProjectionConfidence.MEDIUM,
            )
        return None

    def _detect_delegation_opportunity(
        self,
        trends: list[TrendRecord],
        goals: list[Any],
    ) -> StrategicOpportunity | None:
        active_domains = set()
        for goal in goals:
            if hasattr(goal, "status") and goal.status.value == "active":
                domain = goal.domain if hasattr(goal, "domain") else ""
                if domain:
                    active_domains.add(domain)

        overloaded = [
            t for t in trends
            if t.domain in active_domains
            and t.direction in (TrendDirection.NEGATIVE, TrendDirection.DECELERATING)
            and t.metric == "outcome_velocity"
        ]

        if len(overloaded) >= 2:
            domains = [t.domain for t in overloaded[:3]]
            return StrategicOpportunity(
                title=f"Delegation opportunity: {', '.join(domains)} declining",
                domain=domains[0],
                opportunity_type="delegation",
                potential_impact=f"Multiple domains declining — delegation or re-prioritization needed",
                evidence=[t.description for t in overloaded[:3]],
                action_suggestion="Consider delegating lower-priority domains to preserve bandwidth",
                horizon=TimeHorizon.WEEK,
                confidence=ProjectionConfidence.MEDIUM,
            )
        return None


# ── Projection Generator ────────────────────────────────────────────


class ProjectionGenerator:
    """Generates domain projections from reality + trends + goals."""

    def generate(
        self,
        domain: str,
        horizon: TimeHorizon,
        reality: dict[str, Any],
        goals: list[Any],
        trends: list[TrendRecord],
        outcomes: list[dict[str, Any]],
    ) -> Projection:
        domain_goals = [
            g for g in goals
            if hasattr(g, "domain") and g.domain == domain
            and hasattr(g, "status") and g.status.value == "active"
        ]

        domain_trends = [t for t in trends if t.domain == domain]
        domain_outcomes = [
            o for o in outcomes if o.get("domain", "") == domain
        ]

        current_completion = self._avg_completion(domain_goals)
        velocity = self._compute_velocity(domain_outcomes, horizon.days)
        projected_completion = self._extrapolate_completion(
            current_completion, velocity, horizon.days,
        )

        current_state = self._describe_current(domain, current_completion, domain_outcomes)
        predicted_state = self._describe_predicted(
            domain, projected_completion, velocity, domain_trends, horizon,
        )

        confidence = self._compute_confidence(domain_outcomes, domain_trends, horizon)

        assumptions = self._build_assumptions(velocity, domain_trends, horizon)
        evidence = self._build_evidence(domain_outcomes, domain_goals, domain_trends)

        risk_indicators = []
        for trend in domain_trends:
            if trend.direction in (TrendDirection.NEGATIVE, TrendDirection.DECELERATING):
                risk_indicators.append(trend.description)

        return Projection(
            domain=domain,
            horizon=horizon,
            current_state=current_state,
            predicted_state=predicted_state,
            confidence=confidence,
            assumptions=assumptions,
            supporting_evidence=evidence,
            trends=[t.trend_id for t in domain_trends],
            completion_forecast=projected_completion,
            velocity_forecast=velocity,
            risk_indicators=risk_indicators,
        )

    def _avg_completion(self, goals: list[Any]) -> float:
        if not goals:
            return 0.0
        completions = [
            g.completion_ratio() if hasattr(g, "completion_ratio") else 0.0
            for g in goals
        ]
        return sum(completions) / len(completions)

    def _compute_velocity(
        self, outcomes: list[dict[str, Any]], horizon_days: float,
    ) -> float:
        if not outcomes:
            return 0.0
        now = time.time()
        lookback = now - (horizon_days * 86400)
        recent = [
            o for o in outcomes
            if o.get("completed_at", o.get("created_at", 0)) > lookback
        ]
        if not recent:
            return 0.0
        return len(recent) / max(horizon_days, 1)

    def _extrapolate_completion(
        self, current: float, velocity: float, horizon_days: float,
    ) -> float:
        projected_outcomes = velocity * horizon_days
        progress_per_outcome = 0.05
        projected_progress = projected_outcomes * progress_per_outcome
        return min(1.0, current + projected_progress)

    def _compute_confidence(
        self,
        outcomes: list[dict[str, Any]],
        trends: list[TrendRecord],
        horizon: TimeHorizon,
    ) -> ProjectionConfidence:
        data_points = len(outcomes)
        trend_agreement = all(
            t.direction != TrendDirection.NEGATIVE for t in trends
        ) if trends else True

        if horizon == TimeHorizon.DAY and data_points >= 5:
            return ProjectionConfidence.HIGH
        if horizon == TimeHorizon.WEEK and data_points >= 10 and trend_agreement:
            return ProjectionConfidence.HIGH
        if data_points >= 5:
            return ProjectionConfidence.MEDIUM
        if data_points >= 2:
            return ProjectionConfidence.LOW
        return ProjectionConfidence.SPECULATIVE

    def _describe_current(
        self, domain: str, completion: float, outcomes: list[dict[str, Any]],
    ) -> str:
        parts = [f"{domain}: {completion:.0%} avg goal completion"]
        if outcomes:
            parts.append(f"{len(outcomes)} total outcomes")
        return ". ".join(parts)

    def _describe_predicted(
        self,
        domain: str,
        projected_completion: float,
        velocity: float,
        trends: list[TrendRecord],
        horizon: TimeHorizon,
    ) -> str:
        parts = [f"{domain} in {horizon.value}: projected {projected_completion:.0%} completion"]
        parts.append(f"velocity {velocity:.2f} outcomes/day")

        for trend in trends:
            if trend.direction in (TrendDirection.NEGATIVE, TrendDirection.DECELERATING):
                parts.append(f"risk: {trend.description}")
            elif trend.direction in (TrendDirection.POSITIVE, TrendDirection.ACCELERATING):
                parts.append(f"momentum: {trend.description}")

        return ". ".join(parts)

    def _build_assumptions(
        self,
        velocity: float,
        trends: list[TrendRecord],
        horizon: TimeHorizon,
    ) -> list[str]:
        assumptions = [f"Velocity maintains at ~{velocity:.2f}/day over {horizon.value}"]
        if trends:
            negative = [t for t in trends if t.direction == TrendDirection.NEGATIVE]
            if negative:
                assumptions.append("Declining trends continue without intervention")
            else:
                assumptions.append("Current positive/stable trends persist")
        assumptions.append("No major disruptions or priority shifts")
        return assumptions

    def _build_evidence(
        self,
        outcomes: list[dict[str, Any]],
        goals: list[Any],
        trends: list[TrendRecord],
    ) -> list[str]:
        evidence = []
        if outcomes:
            evidence.append(f"{len(outcomes)} historical outcomes analyzed")
        if goals:
            evidence.append(f"{len(goals)} active goals in domain")
        for trend in trends[:3]:
            evidence.append(trend.description)
        return evidence


# ── Projection Engine (Orchestrator) ─────────────────────────────────


class ProjectionEngine:
    """Top-level orchestrator for the predictive world-model layer.

    Composes TrendDetector, ProjectionGenerator, RiskDetector,
    OpportunityDetector, and AccuracyTracker into a single analysis
    cycle that produces a complete forward-looking strategic picture.
    """

    def __init__(
        self,
        accuracy_tracker: AccuracyTracker | None = None,
        store_path: str | None = None,
    ) -> None:
        _ensure_dirs()
        self._trend_detector = TrendDetector()
        self._projection_generator = ProjectionGenerator()
        self._risk_detector = RiskDetector()
        self._opportunity_detector = OpportunityDetector()
        self._accuracy_tracker = accuracy_tracker or AccuracyTracker()
        self._store = store_path or _projection_data_dir()

        self._last_projections: list[Projection] = []
        self._last_trends: list[TrendRecord] = []
        self._last_risks: list[StrategicRisk] = []
        self._last_opportunities: list[StrategicOpportunity] = []
        self._last_run_at: float = 0.0
        self._run_count: int = 0

    @property
    def last_projections(self) -> list[Projection]:
        return list(self._last_projections)

    @property
    def last_trends(self) -> list[TrendRecord]:
        return list(self._last_trends)

    @property
    def last_risks(self) -> list[StrategicRisk]:
        return list(self._last_risks)

    @property
    def last_opportunities(self) -> list[StrategicOpportunity]:
        return list(self._last_opportunities)

    @property
    def accuracy_tracker(self) -> AccuracyTracker:
        return self._accuracy_tracker

    def run_projections(
        self,
        horizons: list[TimeHorizon] | None = None,
        domains: list[str] | None = None,
    ) -> dict[str, Any]:
        """Full projection cycle: trends → projections → risks → opportunities."""
        self._run_count += 1
        start = time.monotonic_ns()

        if horizons is None:
            horizons = [TimeHorizon.DAY, TimeHorizon.WEEK, TimeHorizon.MONTH, TimeHorizon.QUARTER]

        active_domains = domains or self._get_active_domains()
        reality = self._get_reality()
        goals = self._get_active_goals()
        outcomes = self._get_outcomes()

        trends = self._trend_detector.detect_trends(outcomes, goals)
        self._last_trends = trends
        self._persist_trends(trends)

        projections: list[Projection] = []
        for domain in active_domains:
            for horizon in horizons:
                proj = self._projection_generator.generate(
                    domain, horizon, reality, goals, trends, outcomes,
                )
                projections.append(proj)
        self._last_projections = projections
        self._persist_projections(projections)

        risks = self._risk_detector.detect_risks(goals, trends, projections, outcomes)
        self._last_risks = risks
        self._persist_risks(risks)

        opportunities = self._opportunity_detector.detect_opportunities(
            goals, trends, projections, reality,
        )
        self._last_opportunities = opportunities
        self._persist_opportunities(opportunities)

        elapsed_ms = (time.monotonic_ns() - start) / 1_000_000
        self._last_run_at = time.time()

        return {
            "run_number": self._run_count,
            "domains_analyzed": active_domains,
            "horizons": [h.value for h in horizons],
            "trends": [t.to_dict() for t in trends],
            "trend_count": len(trends),
            "projections": [p.to_dict() for p in projections],
            "projection_count": len(projections),
            "risks": [r.to_dict() for r in risks],
            "risk_count": len(risks),
            "opportunities": [o.to_dict() for o in opportunities],
            "opportunity_count": len(opportunities),
            "accuracy": self._accuracy_tracker.overall_accuracy(),
            "elapsed_ms": round(elapsed_ms, 2),
            "generated_at": self._last_run_at,
        }

    def get_projection_state(self) -> dict[str, Any]:
        """Return complete projection state for cockpit."""
        return {
            "run_count": self._run_count,
            "last_run_at": self._last_run_at,
            "trends": [t.to_dict() for t in self._last_trends],
            "projections": [p.to_dict() for p in self._last_projections],
            "risks": [r.to_dict() for r in self._last_risks],
            "opportunities": [o.to_dict() for o in self._last_opportunities],
            "accuracy": self._accuracy_tracker.overall_accuracy(),
        }

    def get_projections_for_domain(self, domain: str) -> list[Projection]:
        return [p for p in self._last_projections if p.domain == domain]

    def get_projected_reality(self, horizon: TimeHorizon = TimeHorizon.WEEK) -> dict[str, Any]:
        """Return a projected reality snapshot for gap analysis integration."""
        domain_projections: dict[str, Projection] = {}
        for p in self._last_projections:
            if p.horizon == horizon:
                domain_projections[p.domain] = p

        return {
            "horizon": horizon.value,
            "projected_completions": {
                d: p.completion_forecast for d, p in domain_projections.items()
            },
            "projected_velocities": {
                d: p.velocity_forecast for d, p in domain_projections.items()
            },
            "risk_domains": list({
                r.domain for r in self._last_risks
                if r.horizon == horizon or r.severity in (RiskSeverity.CRITICAL, RiskSeverity.HIGH)
            }),
            "opportunity_domains": list({
                o.domain for o in self._last_opportunities
                if o.horizon == horizon
            }),
            "projections": {d: p.to_dict() for d, p in domain_projections.items()},
        }

    def record_outcome(
        self,
        projection_id: str,
        actual_state: str,
        was_accurate: bool,
        accuracy_score: float = 0.0,
    ) -> dict[str, Any]:
        """Record whether a projection was accurate for learning loop."""
        proj = next(
            (p for p in self._last_projections if p.projection_id == projection_id),
            None,
        )
        if not proj:
            return {"success": False, "error": f"projection {projection_id} not found"}

        outcome = ProjectionOutcome(
            projection_id=projection_id,
            domain=proj.domain,
            horizon=proj.horizon.value,
            predicted_state=proj.predicted_state,
            actual_state=actual_state,
            was_accurate=was_accurate,
            accuracy_score=accuracy_score,
        )
        self._accuracy_tracker.record(outcome)

        return {
            "success": True,
            "outcome_id": outcome.outcome_id,
            "projection_id": projection_id,
            "was_accurate": was_accurate,
        }

    def status(self) -> dict[str, Any]:
        """Compact status for health checks."""
        return {
            "run_count": self._run_count,
            "last_run_at": self._last_run_at,
            "trend_count": len(self._last_trends),
            "projection_count": len(self._last_projections),
            "risk_count": len(self._last_risks),
            "opportunity_count": len(self._last_opportunities),
            "accuracy": self._accuracy_tracker.overall_accuracy(),
        }

    # ── Private helpers ────────────────────────────────────────────

    def _get_reality(self) -> dict[str, Any]:
        try:
            from substrate.organism.empire_router import EmpireRouter
            router = EmpireRouter()
            return router.get_reality_snapshot().to_dict()
        except Exception as e:
            logger.error("projection: failed to get reality: %s", e)
            return {
                "active_domains": [],
                "active_loops": [],
                "blocked_items": [],
                "open_approvals": 0,
                "recent_outcomes": [],
                "current_phase": "",
                "next_best_actions": [],
            }

    def _get_active_goals(self) -> list[Any]:
        try:
            from substrate.organism.strategic_gap_engine import GoalRegistry
            registry = GoalRegistry()
            return registry.active_goals()
        except Exception as e:
            logger.error("projection: failed to get goals: %s", e)
            return []

    def _get_outcomes(self) -> list[dict[str, Any]]:
        reality = self._get_reality()
        return reality.get("recent_outcomes", [])

    def _get_active_domains(self) -> list[str]:
        try:
            from substrate.organism.domain_registry import DomainRegistry
            registry = DomainRegistry()
            return [d.domain_id for d in registry.all_domains()]
        except Exception:
            reality = self._get_reality()
            domains = set(reality.get("active_domains", []))
            return sorted(domains) if domains else PROJECTION_DOMAINS[:5]

    def _persist_projections(self, projections: list[Projection]) -> None:
        proj_dir = os.path.join(self._store, "forecasts")
        os.makedirs(proj_dir, exist_ok=True)
        for p in projections:
            path = os.path.join(proj_dir, f"{p.projection_id}.json")
            try:
                with open(path, "w") as f:
                    json.dump(p.to_dict(), f, indent=2)
            except OSError as e:
                logger.error("projection: failed to persist: %s", e)

    def _persist_trends(self, trends: list[TrendRecord]) -> None:
        trend_dir = os.path.join(self._store, "trends")
        os.makedirs(trend_dir, exist_ok=True)
        for t in trends:
            path = os.path.join(trend_dir, f"{t.trend_id}.json")
            try:
                with open(path, "w") as f:
                    json.dump(t.to_dict(), f, indent=2)
            except OSError as e:
                logger.error("projection: failed to persist trend: %s", e)

    def _persist_risks(self, risks: list[StrategicRisk]) -> None:
        risk_dir = os.path.join(self._store, "risks")
        os.makedirs(risk_dir, exist_ok=True)
        for r in risks:
            path = os.path.join(risk_dir, f"{r.risk_id}.json")
            try:
                with open(path, "w") as f:
                    json.dump(r.to_dict(), f, indent=2)
            except OSError as e:
                logger.error("projection: failed to persist risk: %s", e)

    def _persist_opportunities(self, opportunities: list[StrategicOpportunity]) -> None:
        opp_dir = os.path.join(self._store, "opportunities")
        os.makedirs(opp_dir, exist_ok=True)
        for o in opportunities:
            path = os.path.join(opp_dir, f"{o.opportunity_id}.json")
            try:
                with open(path, "w") as f:
                    json.dump(o.to_dict(), f, indent=2)
            except OSError as e:
                logger.error("projection: failed to persist opportunity: %s", e)


# ── Singleton ──────────────────────────────────────────────────────


_engine_instance: ProjectionEngine | None = None


def get_projection_engine() -> ProjectionEngine:
    """Module-level singleton for the projection engine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ProjectionEngine()
    return _engine_instance


def reset_projection_engine() -> None:
    """Reset singleton (testing only)."""
    global _engine_instance
    _engine_instance = None
