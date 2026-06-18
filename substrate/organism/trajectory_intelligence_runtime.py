"""
Trajectory Intelligence Runtime — Campaign 13.0

Computes probable future trajectories for goals, capabilities, work
portfolios, and learning portfolios by enriching ProjectionEngine output
with cross-subsystem context.

Operator questions answered:
  - Where is this goal heading?
  - Which capabilities are accelerating?
  - Is work velocity improving or degrading?
  - Is learning converting to capability at a sustainable rate?

Composes:
  - ProjectionEngine (Phase 6) — trend/projection authority
  - OutcomeTrackingRuntime (C8.2) — goal completion progress
  - GoalDriftEngine (C8) — goal drift signals
  - DecisionValidityEngine (C9) — decision health
  - CapabilityEvolutionEngine (C12.2) — capability maturity trends
  - LearningPortfolioRuntime (C12.3) — learning velocity + health
  - WorkPortfolioRuntime (C11.2) — work execution velocity

Forecast artifacts only. No mutation authority. Does not modify goals,
work, decisions, capabilities, or delegation state.
Deterministic. Zero LLM calls.
"""
from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TrajectoryStatus(str, Enum):
    """Deterministic trajectory classification."""
    ACCELERATING = "accelerating"
    STABLE = "stable"
    SLOWING = "slowing"
    STALLED = "stalled"
    DECLINING = "declining"


_STATUS_SEVERITY = {
    "accelerating": 0,
    "stable": 1,
    "slowing": 2,
    "stalled": 3,
    "declining": 4,
}


@dataclass
class TrajectoryForecast:
    """A single trajectory forecast for an entity.

    Explainability contract: every forecast carries source_signals,
    confidence, confidence_reason, contributing_factors, and
    forecast_horizon_days so the operator can inspect why a prediction
    was made and why confidence is at a given level.
    """
    entity_id: str = ""
    entity_type: str = ""
    current_state: dict[str, Any] = field(default_factory=dict)
    projected_state: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    confidence_reason: str = ""
    status: str = TrajectoryStatus.STABLE.value
    source_signals: list[str] = field(default_factory=list)
    contributing_factors: list[str] = field(default_factory=list)
    forecast_horizon_days: int = 30
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["confidence"] = round(self.confidence, 4)
        return d


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Thresholds
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_HIGH_CONFIDENCE = 0.7
_MODERATE_CONFIDENCE = 0.4
_LOW_VELOCITY_THRESHOLD = 0.1
_DRIFT_SEVERITY_PENALTY = 0.15
_INVALID_DECISION_PENALTY = 0.2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TrajectoryIntelligenceRuntime:
    """Cross-subsystem trajectory forecasting.

    Enriches ProjectionEngine output with decision validity, capability
    evolution, learning velocity, and work execution signals to produce
    trajectory forecasts with full explainability.
    """

    def __init__(
        self,
        projection_engine: Any | None = None,
        outcome_tracking: Any | None = None,
        goal_drift: Any | None = None,
        decision_validity: Any | None = None,
        capability_evolution: Any | None = None,
        learning_portfolio: Any | None = None,
        work_portfolio: Any | None = None,
    ) -> None:
        self._projection_engine = projection_engine
        self._outcome_tracking = outcome_tracking
        self._goal_drift = goal_drift
        self._decision_validity = decision_validity
        self._capability_evolution = capability_evolution
        self._learning_portfolio = learning_portfolio
        self._work_portfolio = work_portfolio

    # ── Lazy subsystem access ────────────────────────────────────────────

    @property
    def projection_engine(self) -> Any | None:
        if self._projection_engine is None:
            try:
                from substrate.organism.projection_engine import ProjectionEngine
                self._projection_engine = ProjectionEngine()
            except Exception:
                logger.debug("ProjectionEngine unavailable")
        return self._projection_engine

    @property
    def outcome_tracking(self) -> Any | None:
        if self._outcome_tracking is None:
            try:
                from substrate.organism.outcome_tracking_runtime import OutcomeTrackingRuntime
                self._outcome_tracking = OutcomeTrackingRuntime()
            except Exception:
                logger.debug("OutcomeTrackingRuntime unavailable")
        return self._outcome_tracking

    @property
    def goal_drift(self) -> Any | None:
        if self._goal_drift is None:
            try:
                from substrate.organism.goal_drift_engine import GoalDriftEngine
                self._goal_drift = GoalDriftEngine()
            except Exception:
                logger.debug("GoalDriftEngine unavailable")
        return self._goal_drift

    @property
    def decision_validity(self) -> Any | None:
        if self._decision_validity is None:
            try:
                from substrate.organism.decision_validity_engine import DecisionValidityEngine
                self._decision_validity = DecisionValidityEngine()
            except Exception:
                logger.debug("DecisionValidityEngine unavailable")
        return self._decision_validity

    @property
    def capability_evolution(self) -> Any | None:
        if self._capability_evolution is None:
            try:
                from substrate.organism.capability_evolution_engine import CapabilityEvolutionEngine
                self._capability_evolution = CapabilityEvolutionEngine()
            except Exception:
                logger.debug("CapabilityEvolutionEngine unavailable")
        return self._capability_evolution

    @property
    def learning_portfolio(self) -> Any | None:
        if self._learning_portfolio is None:
            try:
                from substrate.organism.learning_portfolio_runtime import LearningPortfolioRuntime
                self._learning_portfolio = LearningPortfolioRuntime()
            except Exception:
                logger.debug("LearningPortfolioRuntime unavailable")
        return self._learning_portfolio

    @property
    def work_portfolio(self) -> Any | None:
        if self._work_portfolio is None:
            try:
                from substrate.organism.work_portfolio_runtime import WorkPortfolioRuntime
                self._work_portfolio = WorkPortfolioRuntime()
            except Exception:
                logger.debug("WorkPortfolioRuntime unavailable")
        return self._work_portfolio

    # ── Signal collection helpers ────────────────────────────────────────

    def _get_projection_signals(self) -> dict[str, Any]:
        """Collect projection trend data."""
        signals: dict[str, Any] = {"trend": "neutral", "confidence": 0.5}
        pe = self.projection_engine
        if pe is None:
            return signals
        try:
            state = pe.get_projection_state()
            if isinstance(state, dict):
                trends = state.get("trends", [])
                if trends:
                    pos = sum(1 for t in trends if _get_attr(t, "direction", "") == "positive")
                    neg = sum(1 for t in trends if _get_attr(t, "direction", "") == "negative")
                    if pos > neg:
                        signals["trend"] = "positive"
                    elif neg > pos:
                        signals["trend"] = "negative"
                projections = state.get("projections", [])
                if projections:
                    confs = [_get_attr(p, "confidence_score", 0.5) for p in projections]
                    signals["confidence"] = sum(confs) / len(confs) if confs else 0.5
        except Exception:
            logger.debug("Failed to collect projection signals", exc_info=True)
        return signals

    def _get_goal_signals(self, goal_id: str) -> dict[str, Any]:
        """Collect goal-specific signals."""
        signals: dict[str, Any] = {
            "completion": 0.0,
            "health": "unknown",
            "drift_count": 0,
            "drift_types": [],
        }
        ot = self.outcome_tracking
        if ot is not None:
            try:
                signals["completion"] = ot.completion(goal_id)
                signals["health"] = str(ot.health(goal_id))
            except Exception:
                logger.debug("Failed to get outcome tracking for %s", goal_id)
        gd = self.goal_drift
        if gd is not None:
            try:
                drifts = gd.drift_for_goal(goal_id)
                signals["drift_count"] = len(drifts) if drifts else 0
                signals["drift_types"] = [
                    _get_attr(d, "drift_type", "unknown") for d in (drifts or [])
                ]
            except Exception:
                logger.debug("Failed to get drift for %s", goal_id)
        return signals

    def _get_decision_signals(self) -> dict[str, Any]:
        """Collect decision validity signals."""
        signals: dict[str, Any] = {
            "at_risk_count": 0,
            "invalid_count": 0,
            "total_evaluated": 0,
        }
        dv = self.decision_validity
        if dv is None:
            return signals
        try:
            at_risk = dv.at_risk()
            invalid = dv.invalid()
            signals["at_risk_count"] = len(at_risk) if at_risk else 0
            signals["invalid_count"] = len(invalid) if invalid else 0
            all_evals = dv.evaluate_all()
            signals["total_evaluated"] = len(all_evals) if all_evals else 0
        except Exception:
            logger.debug("Failed to collect decision signals", exc_info=True)
        return signals

    def _get_capability_signals(self, cap_id: str | None = None) -> dict[str, Any]:
        """Collect capability evolution signals."""
        signals: dict[str, Any] = {
            "advancing_count": 0,
            "declining_count": 0,
            "stalled_count": 0,
            "maturity_trend": 0.0,
        }
        ce = self.capability_evolution
        if ce is None:
            return signals
        try:
            if cap_id is not None:
                traj = ce.trajectory(cap_id)
                if traj is not None:
                    signals["maturity_trend"] = getattr(traj, "maturity_trend", 0.0)
            adv = ce.advancing()
            dec = ce.declining()
            stalled = ce.stalled()
            signals["advancing_count"] = len(adv) if adv else 0
            signals["declining_count"] = len(dec) if dec else 0
            signals["stalled_count"] = len(stalled) if stalled else 0
        except Exception:
            logger.debug("Failed to collect capability signals", exc_info=True)
        return signals

    def _get_learning_signals(self) -> dict[str, Any]:
        """Collect learning portfolio signals."""
        signals: dict[str, Any] = {
            "velocity": 0.0,
            "health": "unknown",
            "compounding_score": 0.0,
        }
        lp = self.learning_portfolio
        if lp is None:
            return signals
        try:
            signals["velocity"] = lp.lesson_velocity()
            h = lp.health()
            signals["health"] = h.value if hasattr(h, "value") else str(h)
            signals["compounding_score"] = lp.compounding_score()
        except Exception:
            logger.debug("Failed to collect learning signals", exc_info=True)
        return signals

    def _get_work_signals(self) -> dict[str, Any]:
        """Collect work portfolio signals."""
        signals: dict[str, Any] = {
            "velocity": 0.0,
            "health": "unknown",
            "at_risk_count": 0,
        }
        wp = self.work_portfolio
        if wp is None:
            return signals
        try:
            signals["velocity"] = wp.completions_per_day()
            h = wp.health()
            signals["health"] = h.value if hasattr(h, "value") else str(h)
            at_risk = wp.at_risk_work()
            signals["at_risk_count"] = len(at_risk) if at_risk else 0
        except Exception:
            logger.debug("Failed to collect work signals", exc_info=True)
        return signals

    # ── Status classification ────────────────────────────────────────────

    def _classify_status(
        self,
        trend: str,
        confidence: float,
        drift_count: int,
        velocity: float,
        declining_signals: int,
    ) -> tuple[str, str]:
        """Classify trajectory status and produce a confidence reason.

        Returns (status_value, confidence_reason).
        """
        if declining_signals >= 2 or trend == "negative":
            status = TrajectoryStatus.DECLINING.value
            reason = (
                f"Negative trend with {declining_signals} declining signals"
                if declining_signals >= 2
                else "Negative projection trend detected"
            )
            conf = max(0.1, confidence - _INVALID_DECISION_PENALTY * declining_signals)
            return status, reason

        if drift_count >= 2 and velocity < _LOW_VELOCITY_THRESHOLD:
            status = TrajectoryStatus.STALLED.value
            reason = f"High drift ({drift_count} warnings) with low velocity ({velocity:.2f})"
            return status, reason

        if trend == "positive" and velocity < _LOW_VELOCITY_THRESHOLD:
            status = TrajectoryStatus.SLOWING.value
            reason = f"Positive trend but velocity below threshold ({velocity:.2f} < {_LOW_VELOCITY_THRESHOLD})"
            return status, reason

        if drift_count >= 1 and trend != "positive":
            status = TrajectoryStatus.SLOWING.value
            reason = f"Drift warnings present ({drift_count}) with non-positive trend"
            return status, reason

        if trend == "positive" and confidence >= _HIGH_CONFIDENCE and drift_count == 0:
            status = TrajectoryStatus.ACCELERATING.value
            reason = f"Positive trend, high confidence ({confidence:.2f}), no drift"
            return status, reason

        status = TrajectoryStatus.STABLE.value
        reason = f"Moderate signals: trend={trend}, confidence={confidence:.2f}, drift={drift_count}"
        return status, reason

    def _compute_confidence(
        self,
        base_confidence: float,
        drift_count: int,
        invalid_decisions: int,
        signal_count: int,
    ) -> tuple[float, str]:
        """Compute forecast confidence with reason.

        Returns (confidence, confidence_reason).
        """
        conf = base_confidence
        reasons: list[str] = []

        if signal_count < 3:
            conf *= 0.6
            reasons.append(f"low signal count ({signal_count}/7 subsystems)")

        penalty = drift_count * _DRIFT_SEVERITY_PENALTY
        if penalty > 0:
            conf -= penalty
            reasons.append(f"drift penalty ({drift_count} warnings)")

        decision_penalty = invalid_decisions * _INVALID_DECISION_PENALTY
        if decision_penalty > 0:
            conf -= decision_penalty
            reasons.append(f"invalid decision penalty ({invalid_decisions})")

        conf = max(0.0, min(1.0, conf))

        if not reasons:
            reason = f"Base confidence {base_confidence:.2f} from {signal_count} signal sources"
        else:
            reason = f"Adjusted from {base_confidence:.2f}: {', '.join(reasons)}"

        return round(conf, 4), reason

    # ── Forecast methods ─────────────────────────────────────────────────

    def forecast_goal(self, goal_id: str) -> TrajectoryForecast:
        """Forecast trajectory for a specific goal."""
        now = time.time()
        proj = self._get_projection_signals()
        goal_sig = self._get_goal_signals(goal_id)
        dec_sig = self._get_decision_signals()
        learn_sig = self._get_learning_signals()

        source_signals = []
        signal_count = 0
        if self.projection_engine is not None:
            source_signals.append("projection_engine")
            signal_count += 1
        if self.outcome_tracking is not None:
            source_signals.append("outcome_tracking")
            signal_count += 1
        if self.goal_drift is not None:
            source_signals.append("goal_drift")
            signal_count += 1
        if self.decision_validity is not None:
            source_signals.append("decision_validity")
            signal_count += 1
        if self.learning_portfolio is not None:
            source_signals.append("learning_portfolio")
            signal_count += 1

        declining = dec_sig["invalid_count"] + (
            1 if goal_sig["health"] in ("at_risk", "critical") else 0
        )

        confidence, conf_reason = self._compute_confidence(
            base_confidence=proj["confidence"],
            drift_count=goal_sig["drift_count"],
            invalid_decisions=dec_sig["invalid_count"],
            signal_count=signal_count,
        )

        status, status_reason = self._classify_status(
            trend=proj["trend"],
            confidence=confidence,
            drift_count=goal_sig["drift_count"],
            velocity=goal_sig["completion"],
            declining_signals=declining,
        )

        factors = []
        if goal_sig["completion"] > 0:
            factors.append(f"goal completion: {goal_sig['completion']:.1%}")
        if goal_sig["drift_count"] > 0:
            factors.append(f"goal drift: {goal_sig['drift_count']} warnings")
        if dec_sig["invalid_count"] > 0:
            factors.append(f"invalid decisions: {dec_sig['invalid_count']}")
        if dec_sig["at_risk_count"] > 0:
            factors.append(f"at-risk decisions: {dec_sig['at_risk_count']}")
        if learn_sig["velocity"] > 0:
            factors.append(f"learning velocity: {learn_sig['velocity']:.2f}")

        return TrajectoryForecast(
            entity_id=goal_id,
            entity_type="goal",
            current_state={
                "completion": goal_sig["completion"],
                "health": goal_sig["health"],
                "drift_count": goal_sig["drift_count"],
            },
            projected_state={
                "trend": proj["trend"],
                "trajectory": status,
                "expected_completion_delta": _estimate_delta(
                    goal_sig["completion"], proj["trend"], confidence
                ),
            },
            confidence=confidence,
            confidence_reason=conf_reason,
            status=status,
            source_signals=source_signals,
            contributing_factors=factors,
            forecast_horizon_days=30,
            generated_at=now,
        )

    def forecast_capability(self, cap_id: str) -> TrajectoryForecast:
        """Forecast trajectory for a specific capability."""
        now = time.time()
        proj = self._get_projection_signals()
        cap_sig = self._get_capability_signals(cap_id)
        learn_sig = self._get_learning_signals()

        source_signals = []
        signal_count = 0
        if self.projection_engine is not None:
            source_signals.append("projection_engine")
            signal_count += 1
        if self.capability_evolution is not None:
            source_signals.append("capability_evolution")
            signal_count += 1
        if self.learning_portfolio is not None:
            source_signals.append("learning_portfolio")
            signal_count += 1

        trend = "positive" if cap_sig["maturity_trend"] > 0.1 else (
            "negative" if cap_sig["maturity_trend"] < -0.1 else "neutral"
        )

        declining = cap_sig["declining_count"]
        drift_proxy = cap_sig["stalled_count"]

        confidence, conf_reason = self._compute_confidence(
            base_confidence=proj["confidence"],
            drift_count=drift_proxy,
            invalid_decisions=0,
            signal_count=signal_count,
        )

        status, _ = self._classify_status(
            trend=trend,
            confidence=confidence,
            drift_count=drift_proxy,
            velocity=abs(cap_sig["maturity_trend"]),
            declining_signals=declining,
        )

        factors = []
        factors.append(f"maturity trend: {cap_sig['maturity_trend']:.2f}")
        if cap_sig["advancing_count"] > 0:
            factors.append(f"advancing capabilities: {cap_sig['advancing_count']}")
        if cap_sig["declining_count"] > 0:
            factors.append(f"declining capabilities: {cap_sig['declining_count']}")
        if learn_sig["compounding_score"] > 0:
            factors.append(f"learning compounding: {learn_sig['compounding_score']:.2f}")

        return TrajectoryForecast(
            entity_id=cap_id,
            entity_type="capability",
            current_state={
                "maturity_trend": cap_sig["maturity_trend"],
                "advancing": cap_sig["advancing_count"],
                "declining": cap_sig["declining_count"],
                "stalled": cap_sig["stalled_count"],
            },
            projected_state={
                "trend": trend,
                "trajectory": status,
            },
            confidence=confidence,
            confidence_reason=conf_reason,
            status=status,
            source_signals=source_signals,
            contributing_factors=factors,
            forecast_horizon_days=30,
            generated_at=now,
        )

    def forecast_work(self) -> TrajectoryForecast:
        """Forecast trajectory for the work portfolio."""
        now = time.time()
        proj = self._get_projection_signals()
        work_sig = self._get_work_signals()
        dec_sig = self._get_decision_signals()

        source_signals = []
        signal_count = 0
        if self.projection_engine is not None:
            source_signals.append("projection_engine")
            signal_count += 1
        if self.work_portfolio is not None:
            source_signals.append("work_portfolio")
            signal_count += 1
        if self.decision_validity is not None:
            source_signals.append("decision_validity")
            signal_count += 1

        declining = dec_sig["invalid_count"] + (
            1 if work_sig["health"] in ("degraded", "critical") else 0
        )

        confidence, conf_reason = self._compute_confidence(
            base_confidence=proj["confidence"],
            drift_count=work_sig["at_risk_count"],
            invalid_decisions=dec_sig["invalid_count"],
            signal_count=signal_count,
        )

        status, _ = self._classify_status(
            trend=proj["trend"],
            confidence=confidence,
            drift_count=work_sig["at_risk_count"],
            velocity=work_sig["velocity"],
            declining_signals=declining,
        )

        factors = []
        factors.append(f"work velocity: {work_sig['velocity']:.2f}/day")
        if work_sig["at_risk_count"] > 0:
            factors.append(f"at-risk work items: {work_sig['at_risk_count']}")
        factors.append(f"work health: {work_sig['health']}")

        return TrajectoryForecast(
            entity_id="work_portfolio",
            entity_type="work",
            current_state={
                "velocity": work_sig["velocity"],
                "health": work_sig["health"],
                "at_risk_count": work_sig["at_risk_count"],
            },
            projected_state={
                "trend": proj["trend"],
                "trajectory": status,
            },
            confidence=confidence,
            confidence_reason=conf_reason,
            status=status,
            source_signals=source_signals,
            contributing_factors=factors,
            forecast_horizon_days=30,
            generated_at=now,
        )

    def forecast_learning(self) -> TrajectoryForecast:
        """Forecast trajectory for the learning portfolio."""
        now = time.time()
        proj = self._get_projection_signals()
        learn_sig = self._get_learning_signals()
        cap_sig = self._get_capability_signals()

        source_signals = []
        signal_count = 0
        if self.projection_engine is not None:
            source_signals.append("projection_engine")
            signal_count += 1
        if self.learning_portfolio is not None:
            source_signals.append("learning_portfolio")
            signal_count += 1
        if self.capability_evolution is not None:
            source_signals.append("capability_evolution")
            signal_count += 1

        learn_health = learn_sig["health"]
        declining = 0
        if learn_health in ("declining", "critical"):
            declining += 1
        if cap_sig["stalled_count"] > cap_sig["advancing_count"]:
            declining += 1

        trend = "positive" if learn_sig["velocity"] > _LOW_VELOCITY_THRESHOLD else (
            "negative" if learn_health in ("declining", "critical") else "neutral"
        )

        confidence, conf_reason = self._compute_confidence(
            base_confidence=proj["confidence"],
            drift_count=0,
            invalid_decisions=0,
            signal_count=signal_count,
        )

        status, _ = self._classify_status(
            trend=trend,
            confidence=confidence,
            drift_count=0,
            velocity=learn_sig["velocity"],
            declining_signals=declining,
        )

        factors = []
        factors.append(f"learning velocity: {learn_sig['velocity']:.2f}")
        factors.append(f"learning health: {learn_health}")
        factors.append(f"compounding score: {learn_sig['compounding_score']:.2f}")
        if cap_sig["advancing_count"] > 0:
            factors.append(f"advancing capabilities: {cap_sig['advancing_count']}")

        return TrajectoryForecast(
            entity_id="learning_portfolio",
            entity_type="learning",
            current_state={
                "velocity": learn_sig["velocity"],
                "health": learn_health,
                "compounding_score": learn_sig["compounding_score"],
            },
            projected_state={
                "trend": trend,
                "trajectory": status,
            },
            confidence=confidence,
            confidence_reason=conf_reason,
            status=status,
            source_signals=source_signals,
            contributing_factors=factors,
            forecast_horizon_days=30,
            generated_at=now,
        )

    def forecast_all(self) -> list[TrajectoryForecast]:
        """All entity forecasts: goals + capabilities + work + learning."""
        forecasts: list[TrajectoryForecast] = []

        # Goal forecasts
        goal_ids = self._collect_goal_ids()
        for gid in goal_ids:
            try:
                forecasts.append(self.forecast_goal(gid))
            except Exception:
                logger.debug("Failed to forecast goal %s", gid)

        # Capability forecasts
        cap_ids = self._collect_capability_ids()
        for cid in cap_ids:
            try:
                forecasts.append(self.forecast_capability(cid))
            except Exception:
                logger.debug("Failed to forecast capability %s", cid)

        # Work portfolio forecast
        try:
            forecasts.append(self.forecast_work())
        except Exception:
            logger.debug("Failed to forecast work portfolio")

        # Learning portfolio forecast
        try:
            forecasts.append(self.forecast_learning())
        except Exception:
            logger.debug("Failed to forecast learning portfolio")

        return forecasts

    def at_risk_trajectories(self) -> list[TrajectoryForecast]:
        """Forecasts with SLOWING, STALLED, or DECLINING status."""
        risk_statuses = {
            TrajectoryStatus.SLOWING.value,
            TrajectoryStatus.STALLED.value,
            TrajectoryStatus.DECLINING.value,
        }
        return [
            f for f in self.forecast_all()
            if f.status in risk_statuses
        ]

    def trajectory_summary(self) -> dict[str, Any]:
        """Aggregate trajectory data."""
        forecasts = self.forecast_all()
        if not forecasts:
            return {
                "total": 0,
                "by_status": {},
                "average_confidence": 0.0,
                "at_risk_count": 0,
                "generated_at": time.time(),
            }

        by_status: dict[str, int] = {}
        for f in forecasts:
            by_status[f.status] = by_status.get(f.status, 0) + 1

        confs = [f.confidence for f in forecasts]
        avg_conf = sum(confs) / len(confs) if confs else 0.0

        risk_statuses = {"slowing", "stalled", "declining"}
        at_risk = sum(1 for f in forecasts if f.status in risk_statuses)

        return {
            "total": len(forecasts),
            "by_status": by_status,
            "average_confidence": round(avg_conf, 4),
            "at_risk_count": at_risk,
            "generated_at": time.time(),
        }

    def health(self) -> str:
        """Deterministic health classification."""
        forecasts = self.forecast_all()
        if not forecasts:
            return "unknown"

        total = len(forecasts)
        good = sum(
            1 for f in forecasts
            if f.status in (TrajectoryStatus.ACCELERATING.value, TrajectoryStatus.STABLE.value)
        )
        bad = sum(
            1 for f in forecasts
            if f.status in (TrajectoryStatus.STALLED.value, TrajectoryStatus.DECLINING.value)
        )

        good_ratio = good / total
        bad_ratio = bad / total

        if good_ratio >= 0.5:
            return "healthy"
        if bad_ratio >= 0.3:
            return "critical"
        return "degraded"

    def summary(self) -> dict[str, Any]:
        """Compact summary for API."""
        ts = self.trajectory_summary()
        ts["health"] = self.health()
        return ts

    # ── Internal helpers ─────────────────────────────────────────────────

    def _collect_goal_ids(self) -> list[str]:
        """Collect active goal IDs from outcome tracking."""
        ot = self.outcome_tracking
        if ot is None:
            return []
        try:
            at_risk = ot.goals_at_risk()
            if at_risk:
                return [_get_attr(g, "goal_id", "") for g in at_risk if _get_attr(g, "goal_id", "")]
        except Exception:
            logger.debug("Failed to collect goal IDs")
        return []

    def _collect_capability_ids(self) -> list[str]:
        """Collect capability IDs from evolution engine."""
        ce = self.capability_evolution
        if ce is None:
            return []
        try:
            trajectories = ce.all_trajectories()
            if trajectories:
                return [
                    _get_attr(t, "capability_id", "")
                    for t in trajectories
                    if _get_attr(t, "capability_id", "")
                ]
        except Exception:
            logger.debug("Failed to collect capability IDs")
        return []


# ── Module helpers ───────────────────────────────────────────────────────


def _get_attr(obj: Any, name: str, default: Any = None) -> Any:
    """Safely get attribute from object or dict."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _estimate_delta(current: float, trend: str, confidence: float) -> float:
    """Estimate completion delta over forecast horizon."""
    base = 0.1 if trend == "positive" else (-0.05 if trend == "negative" else 0.0)
    return round(base * confidence, 4)
