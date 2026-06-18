"""
Prediction Portfolio Runtime — Campaign 13.2

Composition façade aggregating trajectory intelligence and scenario
intelligence into a single prediction health model with drift detection.

Operator questions answered:
  - How confident should we be about the future?
  - Where are predictions weakest?
  - Are forecasts improving or degrading?
  - What is the uncertainty index across the portfolio?
  - Where is the prediction pipeline blind?

Composes:
  - TrajectoryIntelligenceRuntime (C13.0) — trajectory forecasts
  - ScenarioIntelligenceEngine (C13.1) — future-state scenarios
  - LearningPortfolioRuntime (C12.3) — signal strength indicator
  - CapabilityPortfolioRuntime (C10.2) — signal strength indicator
  - WorkPortfolioRuntime (C11.2) — signal strength indicator
  - StrategicMemoryEngine (C9.4) — pattern quality indicator

Forecast artifacts only. No mutation authority. Does not modify goals,
work, decisions, capabilities, or delegation state.
No persistence — predictions are ephemeral, recomputed on demand.
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


class PredictionHealth(str, Enum):
    """Portfolio-level prediction confidence classification."""
    HIGH_CONFIDENCE = "high_confidence"
    STABLE = "stable"
    UNCERTAIN = "uncertain"
    VOLATILE = "volatile"
    BLIND = "blind"


class PredictionDriftType(str, Enum):
    """Types of prediction drift that indicate forecast degradation."""
    FORECAST_DECAY = "forecast_decay"
    SIGNAL_WEAKNESS = "signal_weakness"
    SCENARIO_DIVERGENCE = "scenario_divergence"
    CONFIDENCE_COLLAPSE = "confidence_collapse"
    TRAJECTORY_BREAK = "trajectory_break"


@dataclass
class PredictionDriftWarning:
    """A specific prediction drift warning with severity and recommendation."""
    drift_type: str = PredictionDriftType.SIGNAL_WEAKNESS.value
    severity: str = "low"
    description: str = ""
    affected_ids: list[str] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PredictionPortfolioSnapshot:
    """Full prediction portfolio snapshot."""
    forecast_count: int = 0
    scenario_count: int = 0
    prediction_health: str = PredictionHealth.BLIND.value
    average_confidence: float = 0.0
    uncertainty_index: float = 1.0
    drift_warnings: list[dict[str, Any]] = field(default_factory=list)
    top_forecasts: list[dict[str, Any]] = field(default_factory=list)
    critical_risks: list[dict[str, Any]] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["average_confidence"] = round(self.average_confidence, 4)
        d["uncertainty_index"] = round(self.uncertainty_index, 4)
        return d


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Thresholds
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_HIGH_CONF_THRESHOLD = 0.7
_STABLE_CONF_THRESHOLD = 0.5
_UNCERTAIN_CONF_THRESHOLD = 0.3
_COLLAPSE_THRESHOLD = 0.15
_MIN_SIGNAL_SOURCES = 3
_SCENARIO_DIVERGENCE_THRESHOLD = 0.7
_TRAJECTORY_BREAK_LEVELS = 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


_STATUS_SEVERITY = {
    "accelerating": 0,
    "stable": 1,
    "slowing": 2,
    "stalled": 3,
    "declining": 4,
}


class PredictionPortfolioRuntime:
    """Composition façade for all prediction subsystems."""

    def __init__(
        self,
        trajectory_runtime: Any | None = None,
        scenario_engine: Any | None = None,
        learning_portfolio: Any | None = None,
        capability_portfolio: Any | None = None,
        work_portfolio: Any | None = None,
        strategic_memory: Any | None = None,
    ) -> None:
        self._trajectory_runtime = trajectory_runtime
        self._scenario_engine = scenario_engine
        self._learning_portfolio = learning_portfolio
        self._capability_portfolio = capability_portfolio
        self._work_portfolio = work_portfolio
        self._strategic_memory = strategic_memory

    # ── Lazy subsystem access ────────────────────────────────────────────

    @property
    def trajectory_runtime(self) -> Any | None:
        if self._trajectory_runtime is None:
            try:
                from substrate.organism.trajectory_intelligence_runtime import TrajectoryIntelligenceRuntime
                self._trajectory_runtime = TrajectoryIntelligenceRuntime()
            except Exception:
                logger.debug("TrajectoryIntelligenceRuntime unavailable")
        return self._trajectory_runtime

    @property
    def scenario_engine(self) -> Any | None:
        if self._scenario_engine is None:
            try:
                from substrate.organism.scenario_intelligence_engine import ScenarioIntelligenceEngine
                self._scenario_engine = ScenarioIntelligenceEngine()
            except Exception:
                logger.debug("ScenarioIntelligenceEngine unavailable")
        return self._scenario_engine

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
    def capability_portfolio(self) -> Any | None:
        if self._capability_portfolio is None:
            try:
                from substrate.organism.capability_portfolio_runtime import CapabilityPortfolioRuntime
                self._capability_portfolio = CapabilityPortfolioRuntime()
            except Exception:
                logger.debug("CapabilityPortfolioRuntime unavailable")
        return self._capability_portfolio

    @property
    def work_portfolio(self) -> Any | None:
        if self._work_portfolio is None:
            try:
                from substrate.organism.work_portfolio_runtime import WorkPortfolioRuntime
                self._work_portfolio = WorkPortfolioRuntime()
            except Exception:
                logger.debug("WorkPortfolioRuntime unavailable")
        return self._work_portfolio

    @property
    def strategic_memory(self) -> Any | None:
        if self._strategic_memory is None:
            try:
                from substrate.organism.strategic_memory_engine import StrategicMemoryEngine
                self._strategic_memory = StrategicMemoryEngine()
            except Exception:
                logger.debug("StrategicMemoryEngine unavailable")
        return self._strategic_memory

    # ── Signal strength assessment ───────────────────────────────────────

    def _count_signal_sources(self) -> int:
        """Count how many signal-providing subsystems are available."""
        count = 0
        if self.learning_portfolio is not None:
            count += 1
        if self.capability_portfolio is not None:
            count += 1
        if self.work_portfolio is not None:
            count += 1
        if self.strategic_memory is not None:
            count += 1
        if self.trajectory_runtime is not None:
            count += 1
        if self.scenario_engine is not None:
            count += 1
        return count

    # ── Drift detection ──────────────────────────────────────────────────

    def _check_forecast_decay(
        self, avg_confidence: float
    ) -> PredictionDriftWarning | None:
        """Detect: average confidence below threshold."""
        if avg_confidence < _UNCERTAIN_CONF_THRESHOLD and avg_confidence >= _COLLAPSE_THRESHOLD:
            return PredictionDriftWarning(
                drift_type=PredictionDriftType.FORECAST_DECAY.value,
                severity="high",
                description=f"Average forecast confidence at {avg_confidence:.2f} (threshold: {_UNCERTAIN_CONF_THRESHOLD})",
                recommendation="Review data freshness and signal source availability",
            )
        return None

    def _check_signal_weakness(self, signal_count: int) -> PredictionDriftWarning | None:
        """Detect: insufficient signal sources for reliable prediction."""
        if signal_count < _MIN_SIGNAL_SOURCES:
            return PredictionDriftWarning(
                drift_type=PredictionDriftType.SIGNAL_WEAKNESS.value,
                severity="high",
                description=f"Only {signal_count}/{_MIN_SIGNAL_SOURCES} minimum signal sources available",
                recommendation="Ensure learning, capability, and work portfolios are operational",
            )
        return None

    def _check_scenario_divergence(
        self, scenarios: list[Any]
    ) -> PredictionDriftWarning | None:
        """Detect: extreme spread between best and worst case probability."""
        if len(scenarios) < 2:
            return None
        probs = [_get_attr(s, "probability", 0.0) for s in scenarios]
        non_disruption = [
            _get_attr(s, "probability", 0.0)
            for s in scenarios
            if _get_attr(s, "scenario_type", "") != "disruption"
        ]
        if not non_disruption:
            non_disruption = probs
        spread = max(non_disruption) - min(non_disruption)
        if spread > _SCENARIO_DIVERGENCE_THRESHOLD:
            return PredictionDriftWarning(
                drift_type=PredictionDriftType.SCENARIO_DIVERGENCE.value,
                severity="medium",
                description=f"Scenario probability spread is {spread:.2f} (threshold: {_SCENARIO_DIVERGENCE_THRESHOLD})",
                affected_ids=[_get_attr(s, "scenario_id", "") for s in scenarios],
                recommendation="High uncertainty — review assumptions in best and worst case scenarios",
            )
        return None

    def _check_confidence_collapse(
        self, avg_confidence: float
    ) -> PredictionDriftWarning | None:
        """Detect: average confidence critically low."""
        if avg_confidence < _COLLAPSE_THRESHOLD:
            return PredictionDriftWarning(
                drift_type=PredictionDriftType.CONFIDENCE_COLLAPSE.value,
                severity="critical",
                description=f"Average confidence at {avg_confidence:.2f} — prediction system effectively blind",
                recommendation="Manual review needed — automated forecasts unreliable",
            )
        return None

    def _check_trajectory_break(
        self, forecasts: list[Any]
    ) -> PredictionDriftWarning | None:
        """Detect: any trajectory changed status sharply."""
        # We detect this by looking for entities that are DECLINING
        # but have high confidence (suggesting a sharp shift, not gradual)
        sharp_shifts: list[str] = []
        for f in forecasts:
            status = _get_attr(f, "status", "")
            confidence = _get_attr(f, "confidence", 0.0)
            if status == "declining" and confidence > 0.5:
                eid = _get_attr(f, "entity_id", "unknown")
                sharp_shifts.append(eid)
        if sharp_shifts:
            return PredictionDriftWarning(
                drift_type=PredictionDriftType.TRAJECTORY_BREAK.value,
                severity="high",
                description=f"Sharp trajectory break detected for {len(sharp_shifts)} entities",
                affected_ids=sharp_shifts,
                recommendation="Rapid trajectory shift — forecasts may be stale, review contributing factors",
            )
        return None

    def drift_warnings(self) -> list[PredictionDriftWarning]:
        """All active prediction drift warnings."""
        warnings: list[PredictionDriftWarning] = []

        # Collect data
        forecasts: list[Any] = []
        scenarios: list[Any] = []
        avg_confidence = 0.0

        tr = self.trajectory_runtime
        if tr is not None:
            try:
                forecasts = tr.forecast_all()
                if forecasts:
                    confs = [_get_attr(f, "confidence", 0.0) for f in forecasts]
                    avg_confidence = sum(confs) / len(confs) if confs else 0.0
            except Exception:
                logger.debug("Failed to get forecasts for drift detection")

        se = self.scenario_engine
        if se is not None:
            try:
                scenarios = se.generate()
            except Exception:
                logger.debug("Failed to get scenarios for drift detection")

        signal_count = self._count_signal_sources()

        # Run detectors
        for detector in [
            lambda: self._check_forecast_decay(avg_confidence),
            lambda: self._check_signal_weakness(signal_count),
            lambda: self._check_scenario_divergence(scenarios),
            lambda: self._check_confidence_collapse(avg_confidence),
            lambda: self._check_trajectory_break(forecasts),
        ]:
            try:
                warning = detector()
                if warning is not None:
                    warnings.append(warning)
            except Exception:
                logger.debug("Drift detector failed", exc_info=True)

        return warnings

    # ── Health classification ────────────────────────────────────────────

    def health(self) -> PredictionHealth:
        """Deterministic prediction health classification."""
        signal_count = self._count_signal_sources()
        if signal_count < _MIN_SIGNAL_SOURCES:
            return PredictionHealth.BLIND

        # Get average confidence
        avg_conf = 0.0
        tr = self.trajectory_runtime
        if tr is not None:
            try:
                forecasts = tr.forecast_all()
                if forecasts:
                    confs = [_get_attr(f, "confidence", 0.0) for f in forecasts]
                    avg_conf = sum(confs) / len(confs)
            except Exception:
                logger.debug("Failed to compute average confidence")

        if avg_conf <= _COLLAPSE_THRESHOLD:
            return PredictionHealth.BLIND

        warnings = self.drift_warnings()
        drift_count = len(warnings)

        if avg_conf > _HIGH_CONF_THRESHOLD and drift_count == 0:
            return PredictionHealth.HIGH_CONFIDENCE
        if avg_conf > _STABLE_CONF_THRESHOLD and drift_count <= 1:
            return PredictionHealth.STABLE
        if avg_conf > _UNCERTAIN_CONF_THRESHOLD and drift_count <= 3:
            return PredictionHealth.UNCERTAIN
        return PredictionHealth.VOLATILE

    # ── Uncertainty index ────────────────────────────────────────────────

    def uncertainty_index(self) -> float:
        """Compute uncertainty index (0.0 = certain, 1.0 = blind).

        Formula: (1.0 - avg_confidence) scaled by drift warning count.
        """
        avg_conf = 0.0
        tr = self.trajectory_runtime
        if tr is not None:
            try:
                forecasts = tr.forecast_all()
                if forecasts:
                    confs = [_get_attr(f, "confidence", 0.0) for f in forecasts]
                    avg_conf = sum(confs) / len(confs)
            except Exception:
                logger.debug("Failed to compute uncertainty index")

        base_uncertainty = 1.0 - avg_conf
        warnings = self.drift_warnings()
        drift_penalty = len(warnings) * 0.05
        return round(max(0.0, min(1.0, base_uncertainty + drift_penalty)), 4)

    # ── Risk forecasts ───────────────────────────────────────────────────

    def highest_risk_forecasts(self, limit: int = 5) -> list[Any]:
        """Top N forecasts with worst trajectory status."""
        tr = self.trajectory_runtime
        if tr is None:
            return []
        try:
            forecasts = tr.forecast_all()
            sorted_forecasts = sorted(
                forecasts,
                key=lambda f: _STATUS_SEVERITY.get(_get_attr(f, "status", "stable"), 1),
                reverse=True,
            )
            return sorted_forecasts[:limit]
        except Exception:
            logger.debug("Failed to get highest risk forecasts")
            return []

    # ── Snapshot ─────────────────────────────────────────────────────────

    def snapshot(self) -> PredictionPortfolioSnapshot:
        """Full prediction portfolio snapshot."""
        now = time.time()

        forecasts: list[Any] = []
        tr = self.trajectory_runtime
        if tr is not None:
            try:
                forecasts = tr.forecast_all()
            except Exception:
                logger.debug("Failed to get forecasts for snapshot")

        scenarios: list[Any] = []
        se = self.scenario_engine
        if se is not None:
            try:
                scenarios = se.generate()
            except Exception:
                logger.debug("Failed to get scenarios for snapshot")

        avg_conf = 0.0
        if forecasts:
            confs = [_get_attr(f, "confidence", 0.0) for f in forecasts]
            avg_conf = sum(confs) / len(confs)

        health = self.health()
        warnings = self.drift_warnings()
        uidx = self.uncertainty_index()

        # Top at-risk forecasts
        risk_forecasts = sorted(
            forecasts,
            key=lambda f: _STATUS_SEVERITY.get(_get_attr(f, "status", "stable"), 1),
            reverse=True,
        )[:5]

        # Critical risks from worst-case scenario
        critical_risks: list[dict[str, Any]] = []
        for s in scenarios:
            if _get_attr(s, "scenario_type", "") == "worst_case":
                for r in (_get_attr(s, "risks", []) or []):
                    critical_risks.append({"risk": r, "source": "worst_case_scenario"})
                break

        return PredictionPortfolioSnapshot(
            forecast_count=len(forecasts),
            scenario_count=len(scenarios),
            prediction_health=health.value if hasattr(health, "value") else str(health),
            average_confidence=avg_conf,
            uncertainty_index=uidx,
            drift_warnings=[w.to_dict() for w in warnings],
            top_forecasts=[
                _to_dict(f) for f in risk_forecasts
            ],
            critical_risks=critical_risks,
            generated_at=now,
        )

    # ── Summary ──────────────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        """Compact summary for API."""
        snap = self.snapshot()
        return {
            "forecast_count": snap.forecast_count,
            "scenario_count": snap.scenario_count,
            "prediction_health": snap.prediction_health,
            "average_confidence": round(snap.average_confidence, 4),
            "uncertainty_index": round(snap.uncertainty_index, 4),
            "drift_count": len(snap.drift_warnings),
            "generated_at": snap.generated_at,
        }


# ── Module helpers ───────────────────────────────────────────────────────


def _get_attr(obj: Any, name: str, default: Any = None) -> Any:
    """Safely get attribute from object or dict."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _to_dict(obj: Any) -> dict[str, Any]:
    """Convert object to dict, handling both dataclass and dict."""
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return {}
